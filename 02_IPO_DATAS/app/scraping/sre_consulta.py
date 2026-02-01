#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Consulta a página da CVM (SRE), seleciona:
 - TipoEmis = "ACOES"
 - Ano (ex.: 2005)
 - Clica em "Procura"
 - Varre todos os resultados (com paginação)
 - Abre cada registro e extrai os detalhes do BODY
 - Mantém SOMENTE IPO = "SIM"
 - Extrai também as linhas da tabela "ESPÉCIES" (uma linha por espécie)
 - Salva tudo em JSON, atualizando/mesclando o arquivo (merge por chave única)
 - (Opcional) exporta CSV

Uso típico:
    # JSON default em data/output/sre_consulta.json
    python -m app.scraping.sre_consulta --ano 2005 --tipo ACOES --headed

    # JSON custom e também CSV
    python -m app.scraping.sre_consulta --ano 2005 --json-out data/output/ipos_2005.json --csv-out data/output/ipos_2005.csv
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

from playwright.sync_api import (
    Frame,
    Page,
    TimeoutError as PWTimeoutError,
    sync_playwright,
)

BASE = "https://sistemas.cvm.gov.br"
URL = f"{BASE}/port/redir.asp?subpage=consulta"

PAGE_TIMEOUT_MS = 60_000
NETWORK_IDLE_TIMEOUT_MS = 30_000
CLICK_WAIT_MS = 1200
POST_OPEN_WAIT_MS = 1000
NEXT_PAGE_WAIT_MS = 800

LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())

LocatorContainer = Frame | Page

# --------------------------------------------------------
# Utilitários de localização e extração (Playwright / DOM)
# --------------------------------------------------------
def _find_frame_with_selector(page: Page, css_selector: str) -> Optional[LocatorContainer]:
    """Procura o primeiro frame (ou a própria page) contendo o seletor CSS."""
    for container in [page, *page.frames]:
        try:
            if container.locator(css_selector).count() > 0:
                return container
        except Exception:
            continue
    return None


def _find_results_links(page: Page) -> tuple[Optional[LocatorContainer], Optional[str]]:
    """
    Localiza o frame com a tabela de resultados e retorna um seletor para links de REGISTRO.

    Preferência:
      1) 'a.MenuItemP' (classe usual)
      2) 'a[href*="RedirEmisCons.asp"]' (padrão de URL)
      3) 'table a' (fallback)
    """
    candidate_selectors = [
        "a.MenuItemP",
        'a[href*="RedirEmisCons.asp"]',
        "table a",
    ]
    frames_to_search: list[LocatorContainer] = [page, *page.frames]

    for fr in frames_to_search:
        for sel in candidate_selectors:
            try:
                loc = fr.locator(sel)
                if loc.count() > 0:
                    return fr, sel
            except Exception:
                continue

    return None, None


def _try_inner_text(node) -> str:
    try:
        return (node.inner_text() or "").strip()
    except Exception:
        return ""


def _text_by_xpath(container: LocatorContainer, xpath: str) -> str:
    loc = container.locator(f"xpath={xpath}")
    if loc.count() == 0:
        return ""
    return _try_inner_text(loc.first)


def _exists(container: LocatorContainer, selector: str) -> bool:
    try:
        return container.locator(selector).count() > 0
    except Exception:
        return False


def _abs_url(href: str) -> str:
    return urljoin(BASE, href)

# --------------------------------------------------------
# Extração de detalhes da página do REGISTRO
# --------------------------------------------------------
@dataclass
class RegistroDetalhe:
    ano: int
    registro_link: str
    registro_texto: str
    emissora: str
    numero_processo: str
    data_protocolo: str
    analista: str
    ipo: str
    lider: str
    enc_distribuicao: str
    especie_tipo: str
    especie_classe: str
    especie_quantidade: str
    especie_preco: str
    especie_volume: str
    especie_garantidos: str
    especie_sobras: str
    registro_data: str
    registro_numero: str


LABELS = {
    "numero_processo": ["Nº do Processo", "No do Processo", "Nº do Processo ", "Nº Processo"],
    "data_protocolo": ["Data Protocolo", "Dt Protocolo", "Data de Protocolo"],
    "analista": ["Analista"],
    "emissora": ["Emissora", "Companhia", "Emissora "],
    "ipo": ["IPO"],
    "lider": ["Líder", "Lider"],
    "enc_distribuicao": [
        "Encer. Distribuição",
        "Encerramento Distribuição",
        "Encerr. Distribuição",
        "Encer. Distribuicao",
    ],
}


def _value_by_label(container: LocatorContainer, labels: list[str]) -> str:
    """
    Busca um <td> com <b>LABEL</b> e retorna o texto do 3º <td> (pula o ':').
    Estrutura típica:
        <td><font><b>LABEL</b></font></td><td><b>:</b></td><td><font>VALOR</font></td>
    """
    for label in labels:
        xpath = f"//td[.//b[normalize-space()='{label}']]/following-sibling::td[2]"
        val = _text_by_xpath(container, xpath)
        if val:
            return val
    return ""


def _table_xpath_by_title(title: str) -> str:
    # encontra <table> que contenha <b>title</b>
    return f"//table[.//b[normalize-space()='{title}']]"


# ---------------------------
# Normalizações e filtros
# ---------------------------
_ALLOWED_TIPOS = {
    # comuns em ofertas de ações
    "AO", "AP", "ON", "PN", "PNA", "PNB", "PNC", "PND", "PNE", "UNIT", "UNT",
    # casos que já vi em históricos
    "OR", "OS", "AR", "BP", "BR", "CS",
}

def _looks_like_tipo_valido(tipo: str) -> bool:
    """
    Considera válido se:
      - está em _ALLOWED_TIPOS, ou
      - é 1-5 letras maiúsculas (sem sinais), p.ex. AO, AP, ON, PN, UNIT.
    """
    t = (tipo or "").strip().upper()
    if not t:
        return False
    if t in _ALLOWED_TIPOS:
        return True
    return re.fullmatch(r"[A-Z]{1,5}", t) is not None


def _is_footer_or_note(texto: str) -> bool:
    """Detecta rodapés/notas: 'Volume Total:', '** Dispensa', 'Obs:' etc."""
    t = (texto or "").strip().upper()
    banned_prefixes = ("VOLUME TOTAL", "**", "OBS", "DISPENSA", "DISPOSITIVO", "NOTA", "OBSERVA")
    return any(t.startswith(p) for p in banned_prefixes)


def _normalize_registro_numero(s: str) -> str:
    """
    Normaliza registro como 'CVM/SRE/REM/2005/005' removendo espaços supérfluos.
    """
    s = (s or "").strip()
    if not s:
        return s
    # remove espaços ao redor de barras
    s = re.sub(r"\s*/\s*", "/", s)
    # colapsa múltiplos espaços
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _has_some_digit(*vals: str) -> bool:
    for v in vals:
        if any(ch.isdigit() for ch in (v or "")):
            return True
    return False


def _extract_registros_table(container: LocatorContainer) -> tuple[str, str]:
    """Extrai a primeira linha da tabela REGISTROS: (Data, Número)"""
    table_xpath = _table_xpath_by_title("REGISTROS")
    data_xpath = f"{table_xpath}//tr[position()>2]/td[1]"
    numero_xpath = f"{table_xpath}//tr[position()>2]/td[2]"
    data_val = _text_by_xpath(container, data_xpath)
    numero_val = _text_by_xpath(container, numero_xpath)
    return data_val, _normalize_registro_numero(numero_val)


def _extract_especies_rows(container: LocatorContainer) -> list[dict[str, str]]:
    """
    Extrai as linhas da tabela ESPÉCIES, **filtrando** rodapés/observações.
    Mantém somente linhas que aparentam ser espécies (Tipo válido + algum número em quantidade/preço/volume).
    """
    rows: list[dict[str, str]] = []
    table_xpath = _table_xpath_by_title("ESPÉCIES")
    data_rows = container.locator(f"xpath={table_xpath}//tr[position()>2]")
    n = data_rows.count()

    for i in range(n):
        base = f"{table_xpath}//tr[position()>2][{i+1}]"
        tipo = _text_by_xpath(container, f"{base}/td[1]")
        classe = _text_by_xpath(container, f"{base}/td[2]")
        quantidade = _text_by_xpath(container, f"{base}/td[3]")
        preco = _text_by_xpath(container, f"{base}/td[4]")
        volume = _text_by_xpath(container, f"{base}/td[5]")
        garantidos = _text_by_xpath(container, f"{base}/td[6]")
        sobras = _text_by_xpath(container, f"{base}/td[7]")

        # ignora linhas vazias
        if not any([tipo, classe, quantidade, preco, volume, garantidos, sobras]):
            continue

        # ignora rodapés/observações
        if _is_footer_or_note(tipo):
            continue

        # exige "tipo" com cara de espécie + algum número nas colunas numéricas
        if not _looks_like_tipo_valido(tipo):
            continue
        if not _has_some_digit(quantidade, preco, volume):
            continue

        rows.append(
            {
                "especie_tipo": tipo,
                "especie_classe": classe,
                "especie_quantidade": quantidade,
                "especie_preco": preco,
                "especie_volume": volume,
                "especie_garantidos": garantidos,
                "especie_sobras": sobras,
            }
        )

    # se nada sobrou, retornamos vazio mesmo (não vamos injetar linha fake)
    return rows


def extrair_detalhes_registro(page: Page, registro_url: str, ano: int) -> list[RegistroDetalhe]:
    """
    Abre a URL do registro em nova aba, extrai cabeçalho + REGISTROS + ESPÉCIES.
    Retorna POSSIVELMENTE N linhas (uma por espécie).
    """
    detalhes: list[RegistroDetalhe] = []
    context = page.context
    newp = context.new_page()
    try:
        newp.goto(registro_url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)

        container: LocatorContainer = newp
        if not _exists(container, "text=REGISTROS"):
            for fr in newp.frames:
                if _exists(fr, "text=REGISTROS") or fr.locator(
                    "xpath=//b[normalize-space()='REGISTROS']"
                ).count() > 0:
                    container = fr
                    break

        numero_processo = _value_by_label(container, LABELS["numero_processo"]).strip()
        data_protocolo = _value_by_label(container, LABELS["data_protocolo"]).strip()
        analista = _value_by_label(container, LABELS["analista"]).strip()
        emissora = _value_by_label(container, LABELS["emissora"]).strip()
        ipo = _value_by_label(container, LABELS["ipo"]).strip().upper()
        lider = _value_by_label(container, LABELS["lider"]).strip()
        enc_distrib = _value_by_label(container, LABELS["enc_distribuicao"]).strip()

        # mantém somente IPO=SIM (se o campo não existir, aceita)
        if ipo and ipo != "SIM":
            return []

        reg_data, reg_numero = _extract_registros_table(container)
        especies = _extract_especies_rows(container)

        # texto do topo (h2)
        registro_texto = ""
        try:
            registro_texto = newp.locator("xpath=//h2").first.inner_text().strip()
        except Exception:
            pass

        for esp in especies:
            detalhes.append(
                RegistroDetalhe(
                    ano=ano,
                    registro_link=registro_url,
                    registro_texto=registro_texto,
                    emissora=emissora,
                    numero_processo=numero_processo,
                    data_protocolo=data_protocolo,
                    analista=analista,
                    ipo=ipo,
                    lider=lider,
                    enc_distribuicao=enc_distrib,
                    especie_tipo=esp["especie_tipo"],
                    especie_classe=esp["especie_classe"],
                    especie_quantidade=esp["especie_quantidade"],
                    especie_preco=esp["especie_preco"],
                    especie_volume=esp["especie_volume"],
                    especie_garantidos=esp["especie_garantidos"],
                    especie_sobras=esp["especie_sobras"],
                    registro_data=reg_data,
                    registro_numero=reg_numero,
                )
            )
    finally:
        try:
            newp.close()
        except Exception:
            pass
    return detalhes

# --------------------------------------------------------
# Fluxo principal (consulta, coleta de links, paginação)
# --------------------------------------------------------
def coletar_hrefs_resultados(page: Page) -> list[str]:
    """
    Coleta TODOS os hrefs dos registros, paginando enquanto existir "Próxima" (ou similar).
    Retorna a lista completa de hrefs absolutos.
    """
    hrefs: list[str] = []
    while True:
        res_frame, link_selector = _find_results_links(page)
        if not res_frame or not link_selector:
            break

        links = res_frame.locator(link_selector)
        total = links.count()
        for i in range(total):
            a = links.nth(i)
            try:
                href = a.get_attribute("href") or ""
            except Exception:
                href = ""
            if href:
                hrefs.append(_abs_url(href))

        # paginação
        next_locators = [
            res_frame.get_by_role("link", name="Próxima"),
            res_frame.get_by_role("link", name="Proxima"),
            res_frame.locator("a", has_text="Próxima"),
            res_frame.locator("a", has_text="Proxima"),
            res_frame.locator("a", has_text=">>"),
        ]
        found_next = None
        for cand in next_locators:
            try:
                if cand.count() > 0:
                    found_next = cand.first
                    break
            except Exception:
                continue

        if found_next is None:
            break

        try:
            found_next.click()
            page.wait_for_load_state("networkidle", timeout=20_000)
            page.wait_for_timeout(NEXT_PAGE_WAIT_MS)
        except Exception:
            break

    # de-dup preservando ordem
    seen: set[str] = set()
    uniq: list[str] = []
    for u in hrefs:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq

# --------------------------------------------------------
# Persistência JSON (merge/atualização)
# --------------------------------------------------------
def _make_key(row: dict[str, str]) -> tuple:
    """
    Chave única para merge:
      (ano, registro_link, registro_numero, especie_tipo, especie_classe)
    """
    return (
        str(row.get("ano", "")),
        str(row.get("registro_link", "")).strip().lower(),
        str(row.get("registro_numero", "")).strip().lower(),
        str(row.get("especie_tipo", "")).strip().lower(),
        str(row.get("especie_classe", "")).strip().lower(),
    )


def _load_json_list(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list):
                    return v
        return []
    except Exception:
        return []


def _atomic_write_text(path: Path, content: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def save_or_update_json(json_path: Path, rows: list[dict]) -> int:
    """
    Lê o JSON existente (se houver), mescla com rows usando chave única e salva de volta.
    Retorna o total de linhas no JSON após o merge.
    """
    json_path.parent.mkdir(parents=True, exist_ok=True)
    existing = _load_json_list(json_path)
    merged_map: dict[tuple, dict] = {}

    for r in existing:
        merged_map[_make_key(r)] = r

    for r in rows:
        merged_map[_make_key(r)] = r

    merged_list = list(merged_map.values())
    try:
        merged_list.sort(
            key=lambda x: (
                int(x.get("ano") or 0),
                str(x.get("registro_numero") or ""),
                str(x.get("emissora") or "")
            )
        )
    except Exception:
        pass

    _atomic_write_text(json_path, json.dumps(merged_list, ensure_ascii=False, indent=2))
    return len(merged_list)

# --------------------------------------------------------
# Orquestração
# --------------------------------------------------------
def selecionar_e_extrair(
    *,
    tipo: str,
    ano: int,
    json_out: Path,
    headless: bool = True,
    csv_out: Optional[Path] = None,
    max_registros: Optional[int] = None,
) -> tuple[int, int, list[dict]]:
    """
    Executa a consulta, coleta todos os registros, extrai os detalhes e salva JSON (merge).
    Se csv_out for fornecido, exporta CSV também.
    Retorna (qtd_linhas_extraidas_no_run, qtd_total_json_pos_merge, rows_do_run).
    """
    registros_total: list[RegistroDetalhe] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()
        try:
            # 1) Abre a consulta
            page.goto(URL, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
            page.wait_for_timeout(POST_OPEN_WAIT_MS)

            # 2) Seleciona TipoEmis e Ano
            frame = _find_frame_with_selector(page, 'select[name="TipoEmis"]')
            if frame is None:
                page.wait_for_timeout(2000)
                frame = _find_frame_with_selector(page, 'select[name="TipoEmis"]')
            if frame is None:
                raise RuntimeError("Não encontrei <select name='TipoEmis'> (layout pode ter mudado).")

            sel_tipo = frame.locator('select[name="TipoEmis"]')
            try:
                sel_tipo.wait_for(state="visible", timeout=10_000)
            except PWTimeoutError:
                pass
            sel_tipo.select_option(str(tipo).strip())

            frame_ano = (
                frame
                if frame.locator('select[name="Ano"]').count() > 0
                else _find_frame_with_selector(page, 'select[name="Ano"]')
            )
            if frame_ano is None:
                raise RuntimeError("Não encontrei <select name='Ano'> (layout pode ter mudado).")
            sel_ano = frame_ano.locator('select[name="Ano"]')
            try:
                sel_ano.wait_for(state="visible", timeout=10_000)
            except PWTimeoutError:
                pass
            sel_ano.select_option(str(ano))

            # 3) Clica em "Procura"
            btn = None
            if frame.locator('input[name="dd"][value^="Procura"]').count() > 0:
                btn = frame.locator('input[name="dd"][value^="Procura"]').first
            elif frame.get_by_role("button", name="Procura").count() > 0:
                btn = frame.get_by_role("button", name="Procura").first
            else:
                cand = frame.locator('input[type="button"]')
                if cand.count() > 0:
                    btn = cand.first
            if btn is None:
                raise RuntimeError("Não encontrei o botão 'Procura'.")
            btn.click()
            page.wait_for_load_state("networkidle", timeout=NETWORK_IDLE_TIMEOUT_MS)
            page.wait_for_timeout(CLICK_WAIT_MS)

            # 4) Coleta todos os hrefs (com paginação)
            hrefs = coletar_hrefs_resultados(page)
            if not hrefs:
                raise RuntimeError("Nenhum registro encontrado na consulta.")

            if max_registros is not None:
                hrefs = hrefs[:max_registros]

            # 5) Visita cada registro e extrai
            for idx, href in enumerate(hrefs, 1):
                try:
                    detalhes = extrair_detalhes_registro(page, href, ano=ano)
                    registros_total.extend(detalhes)
                    LOGGER.info(
                        "[%s/%s] %s espécie(s) válidas\t%s",
                        idx,
                        len(hrefs),
                        len(detalhes),
                        href,
                    )
                except Exception as exc:
                    LOGGER.warning("[%s/%s] ERRO em %s: %s", idx, len(hrefs), href, exc)
        finally:
            try:
                context.close()
            except Exception:
                pass
            try:
                browser.close()
            except Exception:
                pass

    rows = [asdict(r) for r in registros_total]

    # CSV (opcional)
    if csv_out is not None:
        try:
            import pandas as pd
        except ImportError as exc:
            raise RuntimeError(
                "Pandas não está instalado. Instale com 'pip install pandas' para gerar CSV."
            ) from exc
        csv_out.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_csv(csv_out, index=False, encoding="utf-8")
        LOGGER.info("[OK] CSV salvo: %s", csv_out)

    # JSON (merge/atualiza)
    total_json = save_or_update_json(json_out, rows)
    LOGGER.info("[OK] JSON atualizado: %s (agora com %s linha(s))", json_out, total_json)

    return len(rows), total_json, rows

# --------------------------------------------------------
# CLI
# --------------------------------------------------------
def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    ap = argparse.ArgumentParser(
        description=(
            "Consulta CVM (TipoEmis='ACOES', Ano=N), clica em 'Procura', varre todos os registros "
            "(paginando), abre cada um, extrai detalhes do BODY e salva/ATUALIZA JSON (merge). "
            "Mantém apenas IPO=SIM. CSV é opcional."
        )
    )
    ap.add_argument("--tipo", default="ACOES", help="Valor a selecionar em TipoEmis (default: ACOES)")
    ap.add_argument("--ano", type=int, default=2005, help="Ano a selecionar no <select name='Ano'> (default: 2005)")

    ap.add_argument(
        "--json-out",
        default="data/output/sre_consulta.json",
        help="Caminho do JSON de saída (será criado/atualizado com merge). "
             "Default: data/output/sre_consulta.json",
    )
    ap.add_argument(
        "--csv-out",
        default=None,
        help="(Opcional) Caminho do CSV de saída. Se omitido, não gera CSV.",
    )

    ap.add_argument("--headed", action="store_true", help="Abre o Chromium visível (não headless)")
    ap.add_argument(
        "--max-registros",
        type=int,
        default=None,
        help="Limite de registros (debug). Se omitido, varre todos.",
    )
    args = ap.parse_args()

    try:
        _, total_json, _ = selecionar_e_extrair(
            tipo=args.tipo,
            ano=args.ano,
            json_out=Path(args.json_out),
            headless=not args.headed,
            csv_out=Path(args.csv_out) if args.csv_out else None,
            max_registros=args.max_registros,
        )
        LOGGER.info("[RESUMO] Total de linhas no JSON após merge: %s", total_json)
    except Exception as exc:
        LOGGER.error("[ERRO] %s", exc)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
