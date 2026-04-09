from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import textwrap

from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure
import pandas as pd


SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}

DEFAULT_INPUT = (
    Path(__file__).resolve().parents[1] / "data" / "input" / "exemplo_salario_escolaridade.csv"
)
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "output"

OUTPUT_SUMMARY = "resumo_salario_escolaridade.txt"
OUTPUT_COLUMNS = "colunas_detectadas.csv"
OUTPUT_PREVIEW = "amostra_dados.csv"
OUTPUT_NUMERIC_STATS = "estatisticas_numericas.csv"
OUTPUT_PDF = "relatorio_salario_escolaridade.pdf"


@dataclass
class PipelineResult:
    stats_text: str
    output_dir: Path
    summary_path: Path
    columns_path: Path
    preview_path: Path
    numeric_stats_path: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Executa a base do modulo 05 para inspecao inicial de dados."
    )
    parser.add_argument(
        "--arquivo",
        type=Path,
        default=DEFAULT_INPUT,
        help="Arquivo tabular de entrada (.csv, .xlsx ou .xls).",
    )
    parser.add_argument(
        "--saida",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Pasta onde os arquivos de saida serao salvos.",
    )
    parser.add_argument(
        "--pdf",
        action="store_true",
        help="Gera tambem um PDF com o resumo da execucao.",
    )
    return parser.parse_args()


def load_data(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {path}")

    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(f"Formato nao suportado: {suffix}. Use um destes: {supported}")

    if suffix == ".csv":
        return pd.read_csv(path, sep=None, engine="python")

    return pd.read_excel(path)


def build_columns_inventory(data: pd.DataFrame) -> pd.DataFrame:
    rows = []
    total_rows = len(data.index)
    for column in data.columns:
        series = data[column]
        missing = int(series.isna().sum())
        rows.append(
            {
                "coluna": column,
                "tipo": str(series.dtype),
                "linhas_total": total_rows,
                "nao_nulos": int(series.notna().sum()),
                "nulos": missing,
                "percentual_nulos": (missing / total_rows * 100) if total_rows else 0.0,
                "valores_unicos": int(series.nunique(dropna=True)),
            }
        )
    return pd.DataFrame(rows)


def build_numeric_summary(data: pd.DataFrame) -> pd.DataFrame:
    numeric = data.select_dtypes(include="number")
    if numeric.empty:
        return pd.DataFrame(
            columns=[
                "coluna",
                "contagem",
                "media",
                "desvio_padrao",
                "minimo",
                "q1",
                "mediana",
                "q3",
                "maximo",
            ]
        )

    summary = numeric.describe().T.reset_index().rename(columns={"index": "coluna"})
    rename_map = {
        "count": "contagem",
        "mean": "media",
        "std": "desvio_padrao",
        "min": "minimo",
        "25%": "q1",
        "50%": "mediana",
        "75%": "q3",
        "max": "maximo",
    }
    return summary.rename(columns=rename_map)


def build_stats_text(source_path: Path, data: pd.DataFrame, numeric_summary: pd.DataFrame) -> str:
    column_list = ", ".join(str(column) for column in data.columns) or "(nenhuma coluna)"
    numeric_columns = ", ".join(str(column) for column in data.select_dtypes(include="number").columns)
    preview = data.head(5).to_string(index=False) if not data.empty else "(arquivo sem linhas)"

    sections = [
        "Resumo inicial do modulo 05 - salario x escolaridade",
        "=====================================================",
        f"Arquivo analisado: {source_path}",
        f"Linhas: {len(data.index)}",
        f"Colunas: {len(data.columns)}",
        f"Colunas detectadas: {column_list}",
        "",
        "Amostra inicial (5 primeiras linhas)",
        "------------------------------------",
        preview,
        "",
    ]

    if numeric_columns:
        sections.extend(
            [
                f"Colunas numericas detectadas: {numeric_columns}",
                "",
                "Este modulo ja esta pronto para evoluir a logica especifica do novo programa",
                "mantendo a mesma organizacao de pastas usada nos demais projetos.",
            ]
        )
    else:
        sections.extend(
            [
                "Nenhuma coluna numerica foi detectada no arquivo de entrada.",
                "",
                "A base do modulo continua pronta para evoluir a logica especifica",
                "do novo programa na mesma estrutura dos demais projetos.",
            ]
        )

    if not numeric_summary.empty:
        sections.extend(
            [
                "",
                "Resumo numerico",
                "---------------",
                numeric_summary.to_string(index=False, float_format=lambda value: f"{value:.4f}"),
            ]
        )

    return "\n".join(sections).strip()


def _format_report_text(stats_text: str) -> str:
    intro = [
        "Relatorio do modulo 05 - salario x escolaridade",
        "",
        "Arquivos gerados automaticamente:",
        f"- {OUTPUT_SUMMARY}",
        f"- {OUTPUT_COLUMNS}",
        f"- {OUTPUT_PREVIEW}",
        f"- {OUTPUT_NUMERIC_STATS}",
        "",
    ]
    raw_text = "\n".join(intro) + stats_text

    wrapped_lines: list[str] = []
    for line in raw_text.splitlines():
        if not line.strip():
            wrapped_lines.append("")
            continue
        wrapped_lines.extend(textwrap.fill(line, width=96).splitlines())
    return "\n".join(wrapped_lines)


def _build_report_figure(stats_text: str) -> Figure:
    fig = Figure(figsize=(8.27, 11.69))
    ax = fig.add_subplot(111)
    ax.axis("off")
    ax.text(
        0.02,
        0.98,
        _format_report_text(stats_text),
        ha="left",
        va="top",
        fontsize=9.5,
        family="monospace",
    )
    fig.subplots_adjust(left=0.03, right=0.97, top=0.98, bottom=0.02)
    return fig


def save_pdf_report(stats_text: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / OUTPUT_PDF
    report_fig = _build_report_figure(stats_text)
    with PdfPages(pdf_path) as pdf:
        pdf.savefig(report_fig, dpi=150)
    return pdf_path


def save_outputs(
    stats_text: str,
    columns_df: pd.DataFrame,
    preview_df: pd.DataFrame,
    numeric_stats_df: pd.DataFrame,
    output_dir: Path,
) -> tuple[Path, Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_path = output_dir / OUTPUT_SUMMARY
    columns_path = output_dir / OUTPUT_COLUMNS
    preview_path = output_dir / OUTPUT_PREVIEW
    numeric_stats_path = output_dir / OUTPUT_NUMERIC_STATS

    summary_path.write_text(stats_text + "\n", encoding="utf-8")
    columns_df.to_csv(columns_path, index=False)
    preview_df.to_csv(preview_path, index=False)
    numeric_stats_df.to_csv(numeric_stats_path, index=False)

    return summary_path, columns_path, preview_path, numeric_stats_path


def run_pipeline(input_path: Path, output_dir: Path | None = None) -> PipelineResult:
    data = load_data(input_path)
    final_output_dir = output_dir or DEFAULT_OUTPUT_DIR

    columns_df = build_columns_inventory(data)
    preview_df = data.head(20).copy()
    numeric_stats_df = build_numeric_summary(data)
    stats_text = build_stats_text(input_path, data, numeric_stats_df)

    summary_path, columns_path, preview_path, numeric_stats_path = save_outputs(
        stats_text=stats_text,
        columns_df=columns_df,
        preview_df=preview_df,
        numeric_stats_df=numeric_stats_df,
        output_dir=final_output_dir,
    )

    return PipelineResult(
        stats_text=stats_text,
        output_dir=final_output_dir,
        summary_path=summary_path,
        columns_path=columns_path,
        preview_path=preview_path,
        numeric_stats_path=numeric_stats_path,
    )


def main() -> None:
    args = parse_args()
    result = run_pipeline(args.arquivo, args.saida)

    print(result.stats_text)
    print("\nArquivos gerados:")
    print(f"- {result.summary_path}")
    print(f"- {result.columns_path}")
    print(f"- {result.preview_path}")
    print(f"- {result.numeric_stats_path}")

    if args.pdf:
        pdf_path = save_pdf_report(result.stats_text, result.output_dir)
        print(f"- {pdf_path}")
