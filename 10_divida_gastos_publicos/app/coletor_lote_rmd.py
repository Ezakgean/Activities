from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterator

import requests

from .scraper_rmd import (
    DEFAULT_PAGE_URL,
    USER_AGENT,
    download_document,
    extract_document_text,
    extract_indicators,
    get_document_url,
    merge_indicators,
)


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = BASE_DIR / "data" / "input"
MONTH_NAMES = (
    "Janeiro",
    "Fevereiro",
    "Marco",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
)


def parse_period(value: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d{4})-(0[1-9]|1[0-2])", value)
    if not match:
        raise argparse.ArgumentTypeError("Use o formato AAAA-MM, por exemplo 2000-11.")
    return int(match.group(1)), int(match.group(2))


def month_range(start: tuple[int, int], end: tuple[int, int]) -> Iterator[tuple[int, int]]:
    year, month = start
    while (year, month) <= end:
        yield year, month
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)


def create_payload(year: int, month: int, page_url: str, pdf_url: str) -> dict:
    month_name = MONTH_NAMES[month - 1]
    key = f"resumo_{month_name.casefold()}_{year}".replace("ç", "c")
    return {
        "schema_version": "1.0",
        "dataset": f"Relatorio Mensal da Divida - {month_name} de {year}",
        "sigla": "RMD",
        "periodo_referencia": {
            "ano": year,
            "mes": month,
            "mes_nome": month_name,
            "inicio": f"{year:04d}-{month:02d}-01",
            "fim": f"{year:04d}-{month:02d}-{calendar.monthrange(year, month)[1]}",
        },
        "publicacao": {
            "orgao": "Tesouro Nacional",
            "portal": "Tesouro Transparente",
            "fonte_pagina": page_url,
            "fonte_pdf": pdf_url,
        },
        "convencoes": {
            "moeda": "BRL",
            "valores_financeiros": "Valores numéricos convertidos para ponto decimal no JSON.",
            "percentuais": "Percentuais armazenados como valores de 0 a 100.",
            "nulos": "null indica ausência de valor/título na publicação.",
        },
        key: {},
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Coleta vários RMDs mensais e gera um JSON por competência.")
    parser.add_argument("--inicio", type=parse_period, default=parse_period("2000-11"), help="Competência inicial (AAAA-MM).")
    parser.add_argument("--fim", type=parse_period, default=parse_period("2001-12"), help="Competência final (AAAA-MM).")
    parser.add_argument("--saida", type=Path, default=DEFAULT_INPUT_DIR, help="Pasta dos JSONs gerados.")
    parser.add_argument("--sobrescrever", action="store_true", help="Atualiza também JSONs que já existem.")
    parser.add_argument(
        "--dados-completos",
        action="store_true",
        help="Compatibilidade: a coleta completa já é o padrão.",
    )
    parser.add_argument("--somente-estoque", action="store_true", help="Coleta apenas o estoque.")
    parser.add_argument("--pausa", type=float, default=0.5, help="Pausa entre requisições, em segundos.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.inicio > args.fim:
        raise ValueError("--inicio não pode ser posterior a --fim.")
    if args.pausa < 0:
        raise ValueError("--pausa não pode ser negativa.")

    args.saida.mkdir(parents=True, exist_ok=True)
    report: list[dict[str, str]] = []
    with TemporaryDirectory(prefix="rmd_lote_") as temp_dir, requests.Session() as session:
        session.headers.update({"User-Agent": USER_AGENT})
        for year, month in month_range(args.inicio, args.fim):
            period = f"{year:04d}-{month:02d}"
            output_path = args.saida / f"rmd_divida_publica_{year:04d}_{month:02d}.json"
            if output_path.exists() and not args.sobrescrever:
                print(f"{period}: ignorado (arquivo já existe)")
                report.append({"periodo": period, "status": "ignorado", "arquivo": output_path.name})
                continue

            # O portal usa mês sem zero à esquerda: /2026/7, não /2026/07.
            page_url = DEFAULT_PAGE_URL.replace("/2000/11", f"/{year:04d}/{month}")
            try:
                existing = json.loads(output_path.read_text(encoding="utf-8")) if output_path.exists() else None
                document_url = (existing or {}).get("publicacao", {}).get("fonte_pdf") or get_document_url(page_url, session)
                document_bytes = download_document(document_url, session)
                document_path = Path(temp_dir) / f"rmd_{year:04d}_{month:02d}.bin"
                document_path.write_bytes(document_bytes)
                payload = existing or create_payload(year, month, page_url, document_url)
                payload["publicacao"]["fonte_pdf"] = document_url
                indicators = extract_indicators(extract_document_text(document_path), MONTH_NAMES[month - 1], year)
                if args.somente_estoque:
                    indicators = {"dpfi_estoque_poder_publico_brl_bilhoes": indicators["dpfi_estoque_poder_publico_brl_bilhoes"]}
                updated = merge_indicators(payload, indicators)
                payload["scraping"] = {
                    "extraido_em": datetime.now(UTC).isoformat(),
                    "metodo": "requests + BeautifulSoup + pdftotext/pdfplumber/catdoc",
                    "campos_atualizados": updated,
                    "sha256_documento": hashlib.sha256(document_bytes).hexdigest(),
                }
                output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                print(f"{period}: salvo ({len(updated)} campos)")
                report.append({"periodo": period, "status": "salvo", "arquivo": output_path.name})
            except Exception as exc:
                print(f"{period}: falhou - {exc}")
                report.append({"periodo": period, "status": "falhou", "erro": str(exc)})
            time.sleep(args.pausa)

    report_path = args.saida / "relatorio_coleta_rmd.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    successful = sum(item["status"] == "salvo" for item in report)
    failed = sum(item["status"] == "falhou" for item in report)
    print(f"Concluído: {successful} salvos, {failed} falhos. Relatório: {report_path}")


if __name__ == "__main__":
    main()
