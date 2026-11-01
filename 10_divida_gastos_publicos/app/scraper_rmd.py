from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import pdfplumber
import requests
from bs4 import BeautifulSoup


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PAGE_URL = "https://www.tesourotransparente.gov.br/publicacoes/relatorio-mensal-da-divida-rmd/2000/11"
DEFAULT_JSON_PATH = BASE_DIR / "data" / "input" / "rmd_divida_publica_2000_11.json"
USER_AGENT = "rmd-data-collector/1.0 (educational data collection)"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extrai indicadores do PDF do RMD e atualiza um JSON local.")
    parser.add_argument("--pagina", default=DEFAULT_PAGE_URL, help="URL da página da publicação no Tesouro Transparente.")
    parser.add_argument("--json", dest="json_path", type=Path, default=DEFAULT_JSON_PATH, help="JSON a atualizar.")
    parser.add_argument("--saida", type=Path, help="Novo caminho para o JSON. O padrão sobrescreve --json com backup.")
    parser.add_argument("--pdf", type=Path, help="Usa um PDF local em vez de baixá-lo.")
    parser.add_argument("--salvar-pdf", type=Path, help="Copia o PDF usado para este caminho.")
    parser.add_argument("--sem-backup", action="store_true", help="Não cria um arquivo .bak antes de sobrescrever o JSON.")
    return parser.parse_args()


def _is_supported_document(content: bytes, content_type: str) -> bool:
    return (
        content.startswith(b"%PDF")
        or content.startswith(b"\xd0\xcf\x11\xe0")  # Microsoft Compound Document (.doc)
        or "application/pdf" in content_type
        or "application/msword" in content_type
        or "application/vnd.openxmlformats-officedocument.wordprocessingml" in content_type
    )


def get_document_url(page_url: str, session: requests.Session) -> str:
    """Segue o Download, que pode levar a PDF, DOC ou a uma página com iframe."""
    response = session.get(page_url, timeout=30)
    response.raise_for_status()
    page = BeautifulSoup(response.text, "html.parser")
    link = next(
        (
            anchor.get("href")
            for anchor in page.find_all("a", href=True)
            if "download" in anchor.get_text(" ", strip=True).casefold()
        ),
        None,
    )
    if not link:
        raise ValueError("Link de download do PDF não encontrado na página da publicação.")

    download_url = urljoin(page_url, link)
    response = session.get(download_url, timeout=30)
    response.raise_for_status()
    if _is_supported_document(response.content, response.headers.get("Content-Type", "").casefold()):
        return response.url

    wrapper = BeautifulSoup(response.text, "html.parser")
    iframe = wrapper.find("iframe", src=True)
    if not iframe:
        raise ValueError("O download não é PDF/DOC e não contém um iframe com documento.")
    return urljoin(response.url, iframe["src"])


def download_document(document_url: str, session: requests.Session) -> bytes:
    response = session.get(document_url, timeout=60)
    response.raise_for_status()
    if not _is_supported_document(response.content, response.headers.get("Content-Type", "").casefold()):
        raise ValueError("O endereço encontrado não retornou um PDF ou DOC suportado.")
    return response.content


def extract_text(pdf_path: Path) -> str:
    if shutil.which("pdftotext"):
        result = subprocess.run(
            ["pdftotext", "-layout", str(pdf_path), "-"],
            capture_output=True, timeout=60, check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return normalize_document_text(result.stdout.decode("utf-8", errors="replace"))
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def normalize_document_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    return "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines())


def extract_document_text(document_path: Path) -> str:
    content = document_path.read_bytes()
    if content.startswith(b"%PDF"):
        return extract_text(document_path)
    if content.startswith(b"\xd0\xcf\x11\xe0"):
        try:
            result = subprocess.run(
                ["catdoc", str(document_path)],
                capture_output=True,
                check=True,
                timeout=60,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("Arquivos .doc exigem o programa 'catdoc' instalado no sistema.") from exc
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"Não foi possível extrair o documento .doc: {exc.stderr.decode(errors='replace')}") from exc
        return result.stdout.decode("utf-8", errors="replace")
    raise ValueError("Formato de documento não suportado.")


def br_number(value: str) -> float:
    return float(value.replace(".", "").replace(",", "."))


def find_number(text: str, patterns: list[str]) -> float | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return br_number(match.group(1))
    return None


def normalize_table_numbers(text: str) -> str:
    """Repara a separação visual de milhares produzida por PDFs antigos: '1 .228,42'."""
    return re.sub(r"(?<=\d)\s+(?=[.,]\d)", "", text)


def find_stock_from_dpf_table(text: str) -> float | None:
    """Extrai a última coluna mensal da linha DPF em tabelas de estoque/composição.

    Os RMDs de 2007 em diante repetem a linha DPF em mais de uma tabela. A coluna
    de referência é sempre o número imediatamente anterior ao percentual final de 100%.
    """
    normalized = normalize_table_numbers(text)
    candidates: list[float] = []
    for line in normalized.splitlines():
        if not re.search(r"\bDPF\s+", line, flags=re.IGNORECASE) or "100,00%" not in line:
            continue
        values = re.findall(r"-?[\d.]+,[\d]+", line[line.upper().find("DPF") :])
        if len(values) >= 2:
            candidates.append(br_number(values[-2]))
    plausible = [value for value in candidates if 400 <= value <= 20_000]
    return max(plausible) if plausible else None


def find_stock_from_legacy_narrative(text: str) -> float | None:
    """Extrai o estoque de DPFi/DPMFi dos RMDs de 2000 a 2006."""
    patterns = [
        r"estoque(?:\s+total)?\s+da\s+(?:DPMFi|DPFi).*?atingiu\s+R\$\s*([\d.,]+)\s*bilh",
        r"estoque(?:\s+total)?\s+da\s+(?:DPMFi|DPFi).*?alcançou\s+R\$\s*([\d.,]+)\s*bilh",
        r"estoque(?:\s+total)?\s+da\s+(?:DPMFi|DPFi).*?chegando\s+a\s+R\$\s*([\d.,]+)\s*bilh",
        r"estoque(?:\s+total)?\s+da\s+(?:DPMFi|DPFi).*?passando\s+de.*?para\s+R\$\s*([\d.,]+)\s*bilh",
        r"estoque\s+da\s+DPFi.*?registrando\s+o\s+valor\s+de\s+R\$\s*([\d.,]+)\s*bilh",
    ]
    return find_number(text, patterns)


def valid_stock(value: float | None) -> float | None:
    # A DPF em poder do público permaneceu acima de R$ 400 bi em todo o acervo do RMD.
    return value if value is not None and 400 <= value <= 20_000 else None


def find_table_month_values(text: str, table_number: int, month_name: str) -> list[float]:
    """Obtém os números da linha mensal dentro de uma tabela específica."""
    table = re.search(
        rf"TABELA\s+{table_number}\b(.*?)(?=\nTABELA\s+{table_number + 1}\b|\n\d+\.\d|\Z)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not table:
        return []
    row = re.search(rf"^{re.escape(month_name)}\s+(.+)$", table.group(1), flags=re.IGNORECASE | re.MULTILINE)
    if not row:
        return []
    return [br_number(value) for value in re.findall(r"-?[\d.]+(?:,[\d]+)?", row.group(1))]


def extract_indicators(text: str, month_name: str = "Novembro", year: int | None = None) -> dict[str, Any]:
    """Extrai números das narrativas e dos totais das tabelas do RMD.

    Os relatórios antigos variam levemente na diagramação. Campos não encontrados
    retornam None e, por isso, não substituem valores existentes no JSON.
    """
    text = normalize_document_text(text)
    maturities = find_table_month_values(text, 9, month_name)
    secondary_market = find_table_month_values(text, 10, month_name)
    stock = find_stock_from_dpf_table(text) or find_stock_from_legacy_narrative(text)
    indicators = {
        "dpfi_estoque_poder_publico_brl_bilhoes": valid_stock(stock),
        "prazo_medio_estoque_meses": find_number(text, [r"prazo m[ée]dio.*?([\d.,]+)\s*meses"]),
        "titulos_vencendo_em_12_meses_brl_bilhoes": find_number(
            text,
            [r"vencendo.*?(?:12|doze) meses.*?R\$\s*([\d.,]+)\s*bilh"],
        ) or (maturities[-2] if len(maturities) >= 2 else None),
        "titulos_vencendo_em_12_meses_percentual_total": find_number(
            text,
            [
                r"12 meses reduziu-se(?:\s+de\s+[\d.,]+%)?\s+para\s+([\d.,]+)%",
                r"t[ií]tulos?\s+a\s+vencer\s+em\s+(?:12|doze)\s+meses.*?(?:foi|atingiu).*?([\d.,]+)%",
            ],
        ) or (maturities[-1] if maturities else None),
        "emissoes_diretas_brl_milhoes": find_number(
            text,
            [r"Emiss[õo]es Diretas.*?\bTOTAL\s+([\d.,]+)"],
        ),
        # A tabela 10 traz a média exata; a narrativa costuma arredondar o valor.
        "mercado_secundario_volume_diario_medio_brl_bilhoes": (
            secondary_market[-3]
            if len(secondary_market) >= 3
            else find_number(
                text,
                [r"mercado secund[aá]rio.*?volume di[aá]rio m[ée]dio.*?R\$\s*([\d.,]+)\s*bilh"],
            )
        ),
        "ofertas_publicas": {
            "resgates_brl_milhoes": find_number(text, [r"\bRESGATE\s+(?:[\d.]+\s+){5}([\d.]+)\b"]),
            "emissoes_brl_milhoes": find_number(
                text, [r"\bEMISS(?:ÃO|AO)(?:\s+\*+)?\s+(?:[\d.]+\s+){5}([\d.]+)\b"]
            ),
            "impacto_liquidez_brl_milhoes": find_number(
                text, [r"\bIMPACTO\s+LIQUIDEZ(?:\s+\*+)?\s+(?:-?[\d.]+\s+){5}(-?[\d.]+)\b"]
            ),
        },
    }
    indicators["composicao_percentual"] = extract_composition(text, month_name, year)
    # Tabelas modernas têm outras numerações e unidades; os padrões antigos
    # não podem ser usados nelas (por exemplo, prazo em anos versus meses).
    if re.search(r"EMISS[ÕO]ES\s+DPF\b", text, re.I):
        indicators = {
            "dpfi_estoque_poder_publico_brl_bilhoes": valid_stock(stock),
            "composicao_percentual": indicators["composicao_percentual"],
            "fluxos_dpf": extract_dpf_flows(text),
        }
    return indicators


def extract_composition(text: str, month_name: str, year: int | None = None) -> dict[str, float]:
    """Lê a composição do estoque, sem confundir emissões ou vencimentos."""
    text = normalize_table_numbers(text)
    labels = {
        "prefixada": r"Prefixad[oa]s?",
        "indice_precos": r"[ÍI]ndice de Pre[çc]os",
        "taxa_flutuante": r"Taxa Flutuante",
        "cambio": r"C[âa]mbio",
        "selic": r"(?:Taxa )?Selic",
        "tr": r"TR",
        "outros": r"Outros",
    }
    for match in re.finditer(r"Composi[çc][ãa]o da DPF\b", text, re.I):
        block = text[match.end():].splitlines()[:35]
        result = {}
        in_dpf = False
        for line in block:
            if re.search(r"\bDPF\s+[\d.,]+\s+100(?:,00)?%", line, re.I):
                in_dpf = True
                continue
            if not in_dpf:
                continue
            if re.search(r"\b(?:DPMFi|DPFe)\s+[\d.,]+", line, re.I):
                break
            for key, label in labels.items():
                row = re.search(rf"\b{label}\s+(?=[\d.,])(.+)", line, re.I)
                if row:
                    pairs = re.findall(r"([\d.]+,\d+)\s+([\d.]+,\d+)%", row[1])
                    if len(pairs) >= 2:
                        result[key] = br_number(pairs[-1][1])
        if {"prefixada", "indice_precos", "cambio"} <= result.keys() and ("selic" in result or "taxa_flutuante" in result) and all(0 <= v <= 100 for v in result.values()) and abs(sum(result.values()) - 100) <= 0.1:
            return result

    # Layout histórico: uma linha por mês, com volume/percentual por indexador.
    for table in re.split(r"\bTABELA\s+\d+\b", text, flags=re.I):
        if not re.search(r"Composi[çc][ãa]o da D[Pp](?:MFi|Fi).*?por Tipo de Rentabilidade", table[:250], re.I | re.S):
            continue
        suffix = rf"(?:/(?:{year}|{year % 100:02d}))?" if year is not None else r"(?:/\d{2,4})?"
        rows = list(re.finditer(rf"^{re.escape(month_name).replace('Marco', 'Mar[çc]o')}{suffix}\s+(.+)$", table, re.I | re.M))
        if rows:
            row = rows[-1]
            values = [br_number(v) for v in re.findall(r"([\d.,]+)%", row[1])]
            if len(values) == 7 and abs(values[-1] - 100) < 0.1 and all(0 <= v <= 100 for v in values) and abs(sum(values[:-1]) - 100) <= 0.1:
                return dict(zip(("prefixada", "selic", "indice_precos", "cambio", "tr", "outros"), values[:-1]))
    return {}


def extract_dpf_flows(text: str) -> dict[str, float]:
    result = {}
    for key, label in (("emissoes_brl_milhoes", r"EMISS[ÕO]ES"), ("resgates_brl_milhoes", "RESGATES")):
        row = re.search(rf"\b{label}\s+DPF\s+([^\n]+)", normalize_table_numbers(text), re.I)
        if row:
            values = re.findall(r"-?[\d.]+,\d+", row[1])
            numbers = [br_number(value) for value in values]
            if len(numbers) in (5, 6) and all(v >= 0 for v in numbers) and abs(sum(numbers[:-1]) - numbers[-1]) <= 0.1:
                result[key] = numbers[-1]
    return result


def merge_indicators(payload: dict[str, Any], indicators: dict[str, Any]) -> list[str]:
    summary_key = next((key for key in payload if key.startswith("resumo_")), None)
    if not summary_key:
        raise ValueError("O JSON não contém uma seção resumo_ para atualizar.")
    summary = payload[summary_key]
    updated: list[str] = []
    for key, value in indicators.items():
        if key in {"ofertas_publicas", "fluxos_dpf", "composicao_percentual"}:
            target = summary.setdefault(key, {})
            for sub_key, sub_value in value.items():
                if sub_value is not None:
                    target[sub_key] = sub_value
                    updated.append(f"{key}.{sub_key}")
        elif value is not None:
            summary[key] = value
            updated.append(key)
    return updated


def main() -> None:
    args = parse_args()
    output_path = args.saida or args.json_path
    if not args.json_path.exists():
        raise FileNotFoundError(f"JSON não encontrado: {args.json_path}")

    with requests.Session() as session:
        session.headers.update({"User-Agent": USER_AGENT})
        if args.pdf:
            pdf_path = args.pdf
            pdf_url = None
        else:
            pdf_url = get_document_url(args.pagina, session)
            pdf_bytes = download_document(pdf_url, session)
            pdf_path = Path("/tmp/rmd_download.pdf")
            pdf_path.write_bytes(pdf_bytes)

    if args.salvar_pdf:
        args.salvar_pdf.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(pdf_path, args.salvar_pdf)

    payload = json.loads(args.json_path.read_text(encoding="utf-8"))
    month_name = payload.get("periodo_referencia", {}).get("mes_nome", "Novembro")
    indicators = extract_indicators(extract_document_text(pdf_path), month_name, payload.get("periodo_referencia", {}).get("ano"))
    updated = merge_indicators(payload, indicators)
    publication = payload.setdefault("publicacao", {})
    publication["fonte_pagina"] = args.pagina
    if pdf_url:
        publication["fonte_pdf"] = pdf_url
    payload["scraping"] = {
        "extraido_em": datetime.now(UTC).isoformat(),
        "metodo": "requests + BeautifulSoup + pdftotext/pdfplumber/catdoc",
        "campos_atualizados": updated,
        "sha256_pdf": hashlib.sha256(pdf_path.read_bytes()).hexdigest(),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path == args.json_path and output_path.exists() and not args.sem_backup:
        shutil.copyfile(output_path, output_path.with_suffix(output_path.suffix + ".bak"))
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"JSON atualizado: {output_path}")
    print("Campos extraídos: " + (", ".join(updated) if updated else "nenhum"))


if __name__ == "__main__":
    main()
