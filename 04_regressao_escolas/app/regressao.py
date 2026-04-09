from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import textwrap
import zipfile
from xml.etree import ElementTree as ET

import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure
from scipy import stats
import statsmodels.formula.api as smf


NS = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

REQUIRED_COLUMNS = {"nota", "tratado", "mulher", "cor", "estudo_mae"}

DEFAULT_INPUT = Path(__file__).resolve().parents[1] / "data" / "input" / "EXE 2.xlsx"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "output"

OUTPUT_SUMMARY = "resumo_regressao_escolas.txt"
OUTPUT_DESCRIPTIVES = "estatisticas_descritivas.csv"
OUTPUT_TTESTS = "testes_t.csv"
OUTPUT_COEFFICIENTS = "coeficientes_regressoes.csv"
OUTPUT_PNG = "grafico_estudo_mae.png"
OUTPUT_PDF = "relatorio_regressao_escolas.pdf"


@dataclass
class PipelineResult:
    stats_text: str
    figure: Figure
    output_dir: Path
    summary_path: Path
    descriptives_path: Path
    ttests_path: Path
    coefficients_path: Path
    plot_path: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Executa a analise de regressao escolar em linha de comando."
    )
    parser.add_argument(
        "--arquivo",
        type=Path,
        default=DEFAULT_INPUT,
        help="Arquivo Excel com os dados de entrada.",
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
        help="Gera tambem um PDF com o resumo e o grafico.",
    )
    return parser.parse_args()


def load_data(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {path}")

    try:
        df = pd.read_excel(path)
    except ImportError:
        if path.suffix.lower() != ".xlsx":
            raise
        df = load_xlsx_without_openpyxl(path)

    validate_columns(df)
    return df


def validate_columns(df: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ValueError(f"Colunas ausentes no arquivo Excel: {missing_list}")


def load_xlsx_without_openpyxl(path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(path) as workbook:
        shared_strings = read_shared_strings(workbook)
        rows = read_sheet_rows(workbook, shared_strings)

    if not rows:
        raise ValueError(f"Nenhuma linha foi encontrada em {path}.")

    header = rows[0]
    data = rows[1:]
    frame = pd.DataFrame(data, columns=header)
    return coerce_numeric_columns(frame)


def read_shared_strings(workbook: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in workbook.namelist():
        return []

    root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
    strings: list[str] = []
    for string_item in root.findall("main:si", NS):
        text = "".join(node.text or "" for node in string_item.findall(".//main:t", NS))
        strings.append(text)
    return strings


def read_sheet_rows(workbook: zipfile.ZipFile, shared_strings: list[str]) -> list[list[object]]:
    sheet_root = ET.fromstring(workbook.read("xl/worksheets/sheet1.xml"))
    row_maps: list[dict[int, object]] = []
    max_width = 0

    for row in sheet_root.findall(".//main:sheetData/main:row", NS):
        values_by_column: dict[int, object] = {}
        for cell in row.findall("main:c", NS):
            column_index = excel_column_index(cell.attrib["r"])
            max_width = max(max_width, column_index + 1)
            values_by_column[column_index] = parse_cell_value(cell, shared_strings)
        row_maps.append(values_by_column)

    return [
        [values_by_column.get(index) for index in range(max_width)]
        for values_by_column in row_maps
    ]


def excel_column_index(cell_reference: str) -> int:
    column_letters = "".join(char for char in cell_reference if char.isalpha())
    index = 0
    for char in column_letters:
        index = index * 26 + (ord(char.upper()) - ord("A") + 1)
    return index - 1


def parse_cell_value(cell: ET.Element, shared_strings: list[str]) -> object:
    cell_type = cell.attrib.get("t")
    value_node = cell.find("main:v", NS)

    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(".//main:t", NS))

    if value_node is None:
        return None

    value = value_node.text
    if value is None:
        return None

    if cell_type == "s":
        return shared_strings[int(value)]

    if cell_type == "b":
        return int(value)

    return value


def coerce_numeric_columns(frame: pd.DataFrame) -> pd.DataFrame:
    for column in frame.columns:
        non_null = frame[column].dropna()
        if non_null.empty:
            continue

        converted = pd.to_numeric(non_null, errors="coerce")
        if converted.notna().all():
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

    return frame


def descriptive_table(data: pd.DataFrame, column: str) -> pd.DataFrame:
    return data.groupby("tratado")[column].agg(media="mean", dp="std", mediana="median")


def welch_t_test(data: pd.DataFrame, column: str):
    tratado = data.loc[data["tratado"] == 1, column].dropna()
    controle = data.loc[data["tratado"] == 0, column].dropna()
    return stats.ttest_ind(tratado, controle, equal_var=False)


def run_regression(data: pd.DataFrame, formula: str):
    return smf.ols(formula, data=data).fit()


def build_plot(data: pd.DataFrame, model) -> Figure:
    x = data["estudo_mae"]
    y = data["nota"]
    x_line = np.linspace(float(x.min()), float(x.max()), 100)
    y_line = model.params["Intercept"] + model.params["estudo_mae"] * x_line

    fig = Figure(figsize=(7, 4.4))
    ax = fig.add_subplot(111)
    ax.scatter(x, y, alpha=0.55, s=24, color="#2a6f97", edgecolors="none")
    ax.plot(x_line, y_line, color="#c1121f", linewidth=2)
    ax.set_title("Regressao entre estudo da mae e nota")
    ax.set_xlabel("Estudo da mae")
    ax.set_ylabel("Nota do aluno")
    ax.grid(True, linestyle="--", alpha=0.25)
    fig.tight_layout()
    return fig


def format_table(title: str, table: pd.DataFrame) -> str:
    body = table.to_string(float_format=lambda value: f"{value:.4f}")
    return f"{title}\n{'-' * len(title)}\n{body}"


def format_t_test(title: str, result) -> str:
    lines = [
        title,
        "-" * len(title),
        f"estatistica t: {result.statistic:.4f}",
        f"p-valor: {result.pvalue:.6f}",
        f"graus de liberdade aproximados: {result.df:.4f}",
    ]
    return "\n".join(lines)


def format_interpretation(model) -> str:
    intercept = model.params["Intercept"]
    slope = model.params["estudo_mae"]
    predicted_grade = model.predict(pd.DataFrame({"estudo_mae": [4]})).iloc[0]
    lines = [
        "Interpretacao do modelo nota ~ estudo_mae",
        "----------------------------------------",
        f"Se a mae tem escolaridade zero, a nota esperada do aluno e {intercept:.2f}.",
        (
            "Para cada ano adicional de escolaridade da mae, a nota esperada "
            f"aumenta em {slope:.2f} pontos."
        ),
        (
            "Com base no modelo, a media esperada para um aluno cuja mae tem 4 anos "
            f"de escolaridade e {predicted_grade:.2f}."
        ),
    ]
    return "\n".join(lines)


def build_descriptive_export(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for variable, table in tables.items():
        export_df = table.reset_index().rename(columns={"tratado": "grupo_tratado"})
        export_df.insert(0, "variavel", variable)
        frames.append(export_df)
    return pd.concat(frames, ignore_index=True)


def build_ttests_export(results: dict[str, object]) -> pd.DataFrame:
    rows = []
    for variable, result in results.items():
        rows.append(
            {
                "variavel": variable,
                "estatistica_t": result.statistic,
                "p_valor": result.pvalue,
                "graus_liberdade": result.df,
            }
        )
    return pd.DataFrame(rows)


def build_coefficients_export(models: dict[str, object]) -> pd.DataFrame:
    rows = []
    for model_name, model in models.items():
        conf_int = model.conf_int()
        for variable in model.params.index:
            rows.append(
                {
                    "modelo": model_name,
                    "variavel": variable,
                    "coef": model.params[variable],
                    "std_err": model.bse[variable],
                    "t": model.tvalues[variable],
                    "p_valor": model.pvalues[variable],
                    "ci_inf": conf_int.loc[variable, 0],
                    "ci_sup": conf_int.loc[variable, 1],
                    "r2": model.rsquared,
                    "r2_ajustado": model.rsquared_adj,
                    "n_obs": model.nobs,
                }
            )
    return pd.DataFrame(rows)


def build_stats_text(
    source_path: Path,
    tables: dict[str, pd.DataFrame],
    ttests: dict[str, object],
    models: dict[str, object],
) -> str:
    sections = [
        "Resumo da regressao escolar",
        "===========================",
        f"Arquivo analisado: {source_path}",
        "",
        format_table("Estatisticas descritivas de nota por grupo tratado", tables["nota"]),
        "",
        format_t_test("Teste t de diferenca de medias para nota", ttests["nota"]),
        "",
        "Regressao simples: nota ~ tratado",
        "---------------------------------",
        models["reg1"].summary().as_text(),
        "",
        format_table(
            "Estatisticas descritivas de estudo_mae por grupo tratado",
            tables["estudo_mae"],
        ),
        "",
        format_t_test("Teste t de diferenca de medias para estudo_mae", ttests["estudo_mae"]),
        "",
        "Regressao simples: nota ~ estudo_mae",
        "------------------------------------",
        models["reg2"].summary().as_text(),
        "",
        format_interpretation(models["reg2"]),
        "",
        format_table("Estatisticas descritivas de mulher por grupo tratado", tables["mulher"]),
        "",
        format_table("Estatisticas descritivas de cor por grupo tratado", tables["cor"]),
        "",
        "Regressao linear multipla: nota ~ tratado + mulher + cor + estudo_mae",
        "---------------------------------------------------------------------",
        models["reg3"].summary().as_text(),
    ]
    return "\n".join(sections).strip()


def _format_report_text(stats_text: str) -> str:
    intro = [
        "Relatorio da atividade 04 - regressao escolar",
        "",
        "Saidas geradas automaticamente:",
        f"- {OUTPUT_SUMMARY}",
        f"- {OUTPUT_DESCRIPTIVES}",
        f"- {OUTPUT_TTESTS}",
        f"- {OUTPUT_COEFFICIENTS}",
        f"- {OUTPUT_PNG}",
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


def save_pdf_report(stats_text: str, fig: Figure, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / OUTPUT_PDF
    report_fig = _build_report_figure(stats_text)
    with PdfPages(pdf_path) as pdf:
        pdf.savefig(report_fig, dpi=150)
        pdf.savefig(fig, dpi=150)
    return pdf_path


def save_outputs(
    stats_text: str,
    descriptives_df: pd.DataFrame,
    ttests_df: pd.DataFrame,
    coefficients_df: pd.DataFrame,
    fig: Figure,
    output_dir: Path,
) -> tuple[Path, Path, Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_path = output_dir / OUTPUT_SUMMARY
    descriptives_path = output_dir / OUTPUT_DESCRIPTIVES
    ttests_path = output_dir / OUTPUT_TTESTS
    coefficients_path = output_dir / OUTPUT_COEFFICIENTS
    plot_path = output_dir / OUTPUT_PNG

    summary_path.write_text(stats_text + "\n", encoding="utf-8")
    descriptives_df.to_csv(descriptives_path, index=False)
    ttests_df.to_csv(ttests_path, index=False)
    coefficients_df.to_csv(coefficients_path, index=False)
    fig.savefig(plot_path, dpi=180)

    return summary_path, descriptives_path, ttests_path, coefficients_path, plot_path


def run_pipeline(excel_path: Path, output_dir: Path | None = None) -> PipelineResult:
    data = load_data(excel_path)
    final_output_dir = output_dir or DEFAULT_OUTPUT_DIR

    tables = {
        "nota": descriptive_table(data, "nota"),
        "estudo_mae": descriptive_table(data, "estudo_mae"),
        "mulher": descriptive_table(data, "mulher"),
        "cor": descriptive_table(data, "cor"),
    }
    ttests = {
        "nota": welch_t_test(data, "nota"),
        "estudo_mae": welch_t_test(data, "estudo_mae"),
    }
    models = {
        "reg1": run_regression(data, "nota ~ tratado"),
        "reg2": run_regression(data, "nota ~ estudo_mae"),
        "reg3": run_regression(data, "nota ~ tratado + mulher + cor + estudo_mae"),
    }

    stats_text = build_stats_text(excel_path, tables, ttests, models)
    descriptives_df = build_descriptive_export(tables)
    ttests_df = build_ttests_export(ttests)
    coefficients_df = build_coefficients_export(models)
    fig = build_plot(data, models["reg2"])

    (
        summary_path,
        descriptives_path,
        ttests_path,
        coefficients_path,
        plot_path,
    ) = save_outputs(
        stats_text,
        descriptives_df,
        ttests_df,
        coefficients_df,
        fig,
        final_output_dir,
    )

    return PipelineResult(
        stats_text=stats_text,
        figure=fig,
        output_dir=final_output_dir,
        summary_path=summary_path,
        descriptives_path=descriptives_path,
        ttests_path=ttests_path,
        coefficients_path=coefficients_path,
        plot_path=plot_path,
    )


def main() -> None:
    args = parse_args()
    result = run_pipeline(args.arquivo, args.saida)

    print(result.stats_text)
    print("\nArquivos gerados:")
    print(f"- {result.summary_path}")
    print(f"- {result.descriptives_path}")
    print(f"- {result.ttests_path}")
    print(f"- {result.coefficients_path}")
    print(f"- {result.plot_path}")

    if args.pdf:
        pdf_path = save_pdf_report(result.stats_text, result.figure, result.output_dir)
        print(f"- {pdf_path}")
