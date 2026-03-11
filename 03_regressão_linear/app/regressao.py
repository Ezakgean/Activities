"""
Requisitos de bibliotecas:
    pip install pandas matplotlib statsmodels
"""

from __future__ import annotations

from pathlib import Path
import textwrap

import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure
import statsmodels.api as sm

COL_OBS = "observações"
COL_Y = "y - despesas com alimentação"
COL_X = "x - renda"

OUTPUT_CSV = "resultado_exe1_regressao.csv"
OUTPUT_PNG = "grafico_exe1_regressao.png"
OUTPUT_PDF = "relatorio_exe1_regressao.pdf"


def parse_decimal_series(series: pd.Series) -> pd.Series:
    """Converte strings com vírgula decimal (ex.: 1.234,56) para float."""
    cleaned = (
        series.astype(str)
        .str.strip()
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    return pd.to_numeric(cleaned, errors="coerce")


def validate_columns(df: pd.DataFrame) -> None:
    required = {COL_OBS, COL_X, COL_Y}
    missing = required - set(df.columns)
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ValueError(f"Colunas ausentes no CSV: {missing_list}")


def load_and_prepare(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {csv_path}")

    df = pd.read_csv(csv_path, sep=None, engine="python")
    validate_columns(df)

    df = df.copy()
    df[COL_X] = parse_decimal_series(df[COL_X])
    df[COL_Y] = parse_decimal_series(df[COL_Y])

    invalid = df[COL_X].isna() | df[COL_Y].isna()
    if invalid.any():
        dropped = int(invalid.sum())
        print(f"Aviso: {dropped} linhas com valores invalidos foram removidas.")
        df = df.loc[~invalid].copy()

    if df.empty:
        raise ValueError("Nao ha dados validos para regressao apos a limpeza.")

    return df


def fit_regression(df: pd.DataFrame) -> sm.regression.linear_model.RegressionResultsWrapper:
    x = sm.add_constant(df[COL_X])
    y = df[COL_Y]
    return sm.OLS(y, x).fit()


def format_results(model: sm.regression.linear_model.RegressionResultsWrapper) -> str:
    n_obs = int(model.nobs)
    beta0 = float(model.params.get("const", float("nan")))
    beta1 = float(model.params.get(COL_X, float("nan")))
    r2 = float(model.rsquared)
    r2_adj = float(model.rsquared_adj)
    std_err = float(model.mse_resid ** 0.5)
    f_stat = float(model.fvalue) if model.fvalue is not None else float("nan")
    f_pvalue = float(model.f_pvalue) if model.f_pvalue is not None else float("nan")

    lines = [
        "Resumo da Regressao Linear",
        "-" * 32,
        f"Numero de observacoes: {n_obs}",
        f"Intercepto (beta0): {beta0:.6f}",
        f"Coeficiente angular (beta1): {beta1:.6f}",
        f"R2: {r2:.6f}",
        f"R2 ajustado: {r2_adj:.6f}",
        f"Erro padrao da regressao: {std_err:.6f}",
        f"Estatistica F: {f_stat:.6f}",
        f"P-valor (F): {f_pvalue:.6g}",
        "",
        "Tabela de coeficientes",
        "-" * 24,
    ]

    conf_int = model.conf_int()
    table = pd.DataFrame(
        {
            "coef": model.params,
            "std_err": model.bse,
            "t": model.tvalues,
            "p_valor": model.pvalues,
            "ci_inf": conf_int[0],
            "ci_sup": conf_int[1],
        }
    )
    lines.append(table.to_string(float_format=lambda v: f"{v:.6f}"))
    return "\n".join(lines)


def build_output_df(
    df: pd.DataFrame, model: sm.regression.linear_model.RegressionResultsWrapper
) -> pd.DataFrame:
    fitted = model.fittedvalues
    resid = model.resid

    return pd.DataFrame(
        {
            COL_OBS: df[COL_OBS].values,
            "x": df[COL_X].values,
            "y": df[COL_Y].values,
            "y_estimado": fitted.values,
            "residuo": resid.values,
        }
    )


def build_figure(df_out: pd.DataFrame) -> Figure:
    x = df_out["x"]
    y = df_out["y"]
    y_hat = df_out["y_estimado"]
    order = x.argsort()

    fig = Figure(figsize=(7, 4))
    ax = fig.add_subplot(111)
    ax.scatter(x, y, label="Observacoes reais", alpha=0.8)
    ax.plot(x.iloc[order], y_hat.iloc[order], color="red", label="Linha de regressao")
    ax.set_title("Regressao Linear: Despesas x Renda")
    ax.set_xlabel("Renda (x)")
    ax.set_ylabel("Despesas com alimentacao (y)")
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend()
    fig.tight_layout()
    return fig


def save_outputs(df_out: pd.DataFrame, fig: Figure, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / OUTPUT_CSV
    png_path = output_dir / OUTPUT_PNG

    df_out.to_csv(csv_path, index=False)
    fig.savefig(png_path, dpi=150)

    return csv_path, png_path


def _format_report_text(stats_text: str) -> str:
    formulas = [
        "Formulas usadas:",
        "1) y = beta0 + beta1 * x + erro",
        "2) beta1 = soma((x - x_bar) * (y - y_bar)) / soma((x - x_bar)^2)",
        "3) beta0 = y_bar - beta1 * x_bar",
        "4) R2 = 1 - (SSE / SST)",
    ]
    parts = ["\n".join(formulas), "", stats_text]
    raw_text = "\n".join(parts)

    wrapped_lines: list[str] = []
    for line in raw_text.splitlines():
        if not line.strip():
            wrapped_lines.append("")
            continue
        wrapped_lines.extend(textwrap.fill(line, width=95).splitlines())
    return "\n".join(wrapped_lines)


def _build_report_figure(stats_text: str) -> Figure:
    fig = Figure(figsize=(8.27, 11.69))  # A4 portrait
    ax = fig.add_subplot(111)
    ax.axis("off")
    report_text = _format_report_text(stats_text)
    ax.text(
        0.02,
        0.98,
        report_text,
        ha="left",
        va="top",
        fontsize=10,
        family="monospace",
    )
    fig.tight_layout()
    return fig


def save_pdf_report(stats_text: str, fig: Figure, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / OUTPUT_PDF
    report_fig = _build_report_figure(stats_text)
    with PdfPages(pdf_path) as pdf:
        pdf.savefig(report_fig, dpi=150)
        pdf.savefig(fig, dpi=150)
    return pdf_path


def run_pipeline(csv_path: Path) -> tuple[str, pd.DataFrame, Figure, Path, Path]:
    df = load_and_prepare(csv_path)
    model = fit_regression(df)
    stats_text = format_results(model)

    df_out = build_output_df(df, model)
    fig = build_figure(df_out)
    output_dir = csv_path.parent
    csv_path, png_path = save_outputs(df_out, fig, output_dir)

    return stats_text, df_out, fig, csv_path, png_path
