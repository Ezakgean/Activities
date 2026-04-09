from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import textwrap

from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter
from matplotlib.transforms import ScaledTranslation
import pandas as pd
import statsmodels.api as sm


SUPPORTED_EXTENSIONS = {".json"}

DEFAULT_INPUT = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "input"
    / "profissoes_15_estados_salarios_estimados.json"
)
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "output"

OUTPUT_SUMMARY = "resumo_regressao_salario_escolaridade.txt"
OUTPUT_FLAT_DATA = "base_profissoes_estado.csv"
OUTPUT_STATE_MEANS = "medias_salariais_estado_escolaridade.csv"
OUTPUT_REGRESSIONS = "regressoes_por_estado.csv"
OUTPUT_PNG = "dashboard_salario_escolaridade.png"
OUTPUT_PDF = "relatorio_salario_escolaridade.pdf"

FIG_BG = "#0f0f10"
PANEL_BG = "#141516"
CARD_BG = "#191b1f"
GRID_COLOR = "#35373b"
TEXT_PRIMARY = "#f7f7f7"
TEXT_MUTED = "#9aa0a6"
ACCENT = "#f5821f"
ACCENT_SOFT = "#ffb066"
SECONDARY = "#2a6f97"
LINE_COLOR = "#636873"
BORDER_COLOR = "#2a2c30"


@dataclass
class PipelineResult:
    stats_text: str
    figure: Figure
    analysis_frame: pd.DataFrame
    state_means_df: pd.DataFrame
    regressions_df: pd.DataFrame
    output_dir: Path
    summary_path: Path
    flat_data_path: Path
    state_means_path: Path
    regressions_path: Path
    dashboard_path: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Executa as regressoes salario ~ ensino_superior por estado."
    )
    parser.add_argument(
        "--arquivo",
        type=Path,
        default=DEFAULT_INPUT,
        help="Arquivo JSON com profissoes e salarios estimados por estado.",
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
        help="Gera tambem um PDF com o resumo e o dashboard.",
    )
    return parser.parse_args()


def format_brl(value: float) -> str:
    formatted = f"{float(value):,.2f}"
    return "R$ " + formatted.replace(",", "_").replace(".", ",").replace("_", ".")


def format_brl_compact(value: float) -> str:
    if abs(value) >= 1000:
        formatted = f"{value / 1000:.1f} mil"
    else:
        formatted = f"{value:.0f}"
    return "R$ " + formatted.replace(".", ",")


def format_percent(value: float) -> str:
    return f"{value * 100:.1f}%".replace(".", ",")


def format_p_value(value: float) -> str:
    if value < 0.0001:
        return "< 0,0001"
    return f"{value:.4f}".replace(".", ",")


def load_payload(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {path}")

    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(f"Formato nao suportado: {suffix}. Use um destes: {supported}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("O JSON precisa conter um objeto na raiz.")
    if "metadata" not in payload or "professions" not in payload:
        raise ValueError("O JSON precisa conter as chaves 'metadata' e 'professions'.")
    if not isinstance(payload["professions"], list) or not payload["professions"]:
        raise ValueError("A chave 'professions' precisa conter uma lista nao vazia.")
    return payload


def build_analysis_frame(payload: dict) -> pd.DataFrame:
    metadata = payload.get("metadata", {})
    states_selected = metadata.get("states_selected", {})

    rows: list[dict[str, object]] = []
    for profession in payload["professions"]:
        salary_by_state = profession.get("estimated_average_salary_by_state_brl")
        if not isinstance(salary_by_state, dict) or not salary_by_state:
            raise ValueError("Cada profissao precisa conter salarios estimados por estado.")

        superior = int(bool(profession.get("requires_higher_education")))
        for estado, salario in salary_by_state.items():
            state_metadata = states_selected.get(estado, {})
            rows.append(
                {
                    "estado": estado,
                    "estado_nome": state_metadata.get("name", estado),
                    "profissao": profession.get("profession", ""),
                    "grupo_ocupacional": profession.get("occupational_group", ""),
                    "escolaridade_dummy": superior,
                    "escolaridade_label": "Superior" if superior else "Nao superior",
                    "salario_brl": float(salario),
                    "media_nacional_grupo_brl_2024": float(
                        profession.get("national_group_average_brl_2024", 0.0)
                    ),
                    "rendimento_uf_2025_brl": float(
                        state_metadata.get("uf_income_2025_brl", 0.0)
                    ),
                }
            )

    data = pd.DataFrame(rows)
    if data.empty:
        raise ValueError("Nao foi possivel construir a base de analise a partir do JSON.")

    return data.sort_values(
        ["estado", "escolaridade_dummy", "grupo_ocupacional", "profissao"]
    ).reset_index(drop=True)


def build_state_means(data: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        data.groupby(
            ["estado", "estado_nome", "escolaridade_dummy", "escolaridade_label"],
            as_index=False,
        )
        .agg(
            n_profissoes=("profissao", "count"),
            salario_medio_brl=("salario_brl", "mean"),
            salario_mediano_brl=("salario_brl", "median"),
            salario_dp_brl=("salario_brl", "std"),
        )
        .sort_values(["estado", "escolaridade_dummy"])
        .reset_index(drop=True)
    )
    return grouped


def build_state_regressions(data: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for (estado, estado_nome), group in data.groupby(["estado", "estado_nome"], sort=True):
        x = sm.add_constant(group["escolaridade_dummy"])
        y = group["salario_brl"]
        model = sm.OLS(y, x).fit()

        salario_sem_superior = float(model.params["const"])
        premio_superior = float(model.params["escolaridade_dummy"])
        salario_com_superior = salario_sem_superior + premio_superior

        rows.append(
            {
                "estado": estado,
                "estado_nome": estado_nome,
                "n_obs": int(model.nobs),
                "n_sem_superior": int((group["escolaridade_dummy"] == 0).sum()),
                "n_superior": int((group["escolaridade_dummy"] == 1).sum()),
                "salario_sem_superior_brl": salario_sem_superior,
                "premio_superior_brl": premio_superior,
                "salario_com_superior_brl": salario_com_superior,
                "premio_superior_percentual": (
                    premio_superior / salario_sem_superior if salario_sem_superior else 0.0
                ),
                "salario_medio_geral_brl": float(group["salario_brl"].mean()),
                "r2": float(model.rsquared),
                "r2_ajustado": float(model.rsquared_adj),
                "estatistica_t_beta1": float(model.tvalues["escolaridade_dummy"]),
                "p_valor_beta1": float(model.pvalues["escolaridade_dummy"]),
                "erro_padrao_residual": float(model.mse_resid ** 0.5),
            }
        )

    return pd.DataFrame(rows).sort_values(
        ["premio_superior_brl", "estado"], ascending=[False, True]
    ).reset_index(drop=True)


def build_stats_text(
    source_path: Path,
    payload: dict,
    data: pd.DataFrame,
    state_means: pd.DataFrame,
    regressions: pd.DataFrame,
) -> str:
    metadata = payload.get("metadata", {})
    coverage = metadata.get("coverage", {})

    top_state = regressions.iloc[0]
    bottom_state = regressions.iloc[-1]
    pooled_means = (
        data.groupby(["escolaridade_dummy", "escolaridade_label"], as_index=False)
        .agg(salario_medio_brl=("salario_brl", "mean"))
        .sort_values("escolaridade_dummy")
    )
    pooled_sem = float(
        pooled_means.loc[pooled_means["escolaridade_dummy"] == 0, "salario_medio_brl"].iloc[0]
    )
    pooled_com = float(
        pooled_means.loc[pooled_means["escolaridade_dummy"] == 1, "salario_medio_brl"].iloc[0]
    )
    pooled_premium = pooled_com - pooled_sem
    avg_premium = float(regressions["premio_superior_brl"].mean())
    avg_r2 = float(regressions["r2"].mean())

    display_table = regressions[
        [
            "estado",
            "estado_nome",
            "salario_sem_superior_brl",
            "premio_superior_brl",
            "salario_com_superior_brl",
            "r2",
            "p_valor_beta1",
        ]
    ].copy()
    display_table["salario_sem_superior_brl"] = display_table["salario_sem_superior_brl"].map(
        format_brl
    )
    display_table["premio_superior_brl"] = display_table["premio_superior_brl"].map(format_brl)
    display_table["salario_com_superior_brl"] = display_table["salario_com_superior_brl"].map(
        format_brl
    )
    display_table["r2"] = display_table["r2"].map(lambda value: f"{value:.4f}")
    display_table["p_valor_beta1"] = display_table["p_valor_beta1"].map(format_p_value)
    display_table = display_table.rename(
        columns={
            "estado": "UF",
            "estado_nome": "Estado",
            "salario_sem_superior_brl": "Base sem superior",
            "premio_superior_brl": "Premio superior",
            "salario_com_superior_brl": "Previsto com superior",
            "r2": "R2",
            "p_valor_beta1": "p-valor",
        }
    )

    mean_table = state_means[
        ["estado", "estado_nome", "escolaridade_label", "n_profissoes", "salario_medio_brl"]
    ].copy()
    mean_table["salario_medio_brl"] = mean_table["salario_medio_brl"].map(format_brl)
    mean_table = mean_table.rename(
        columns={
            "estado": "UF",
            "estado_nome": "Estado",
            "escolaridade_label": "Grupo",
            "n_profissoes": "N",
            "salario_medio_brl": "Salario medio",
        }
    )

    sections = [
        "Resumo da regressao salario ~ ensino_superior por estado",
        "========================================================",
        f"Arquivo analisado: {source_path}",
        f"Observacoes consolidadas: {len(data)}",
        f"Profissoes na base: {coverage.get('professions_count', data['profissao'].nunique())}",
        f"Estados na base: {coverage.get('states_count', data['estado'].nunique())}",
        f"Data de geracao informada no metadata: {metadata.get('generated_on', 'n/d')}",
        "",
        "Nota metodologica",
        "-----------------",
        (
            "A base nao traz anos de estudo por profissao. A escolaridade foi modelada como "
            "uma proxy binaria: 1 para profissao com exigencia de ensino superior e 0 caso "
            "contrario."
        ),
        (
            "Com isso, a regressao por UF assume a forma salario = beta0 + beta1 * "
            "ensino_superior. O intercepto beta0 representa o salario medio estimado para "
            "profissoes sem exigencia de ensino superior e beta1 representa o premio salarial "
            "associado a ocupacoes com exigencia de ensino superior."
        ),
        "",
        "Principais achados",
        "------------------",
        f"Media pooled sem superior: {format_brl(pooled_sem)}",
        f"Media pooled com superior: {format_brl(pooled_com)}",
        f"Premio pooled associado a ensino superior: {format_brl(pooled_premium)}",
        f"Premio medio entre os estados: {format_brl(avg_premium)}",
        f"Premio relativo medio: {format_percent(regressions['premio_superior_percentual'].mean())}",
        f"R2 medio dos modelos estaduais: {avg_r2:.4f}",
        (
            f"Maior premio estimado: {top_state['estado_nome']} ({top_state['estado']}) "
            f"= {format_brl(top_state['premio_superior_brl'])}"
        ),
        (
            f"Menor premio estimado: {bottom_state['estado_nome']} ({bottom_state['estado']}) "
            f"= {format_brl(bottom_state['premio_superior_brl'])}"
        ),
        "",
        "Medias salariais por estado e grupo",
        "-----------------------------------",
        mean_table.to_string(index=False),
        "",
        "Coeficientes das regressoes por estado",
        "--------------------------------------",
        display_table.to_string(index=False),
        "",
        "Conclusoes",
        "----------",
        (
            "As regressoes por estado apontam uma associacao positiva e sistematica entre a "
            "exigencia de ensino superior e salarios estimados mais altos em todas as UFs da base."
        ),
        (
            f"No agregado, a media estimada passa de {format_brl(pooled_sem)} para "
            f"{format_brl(pooled_com)}, um diferencial de {format_brl(pooled_premium)}."
        ),
        (
            "Esse premio aparece em todos os estados, mas cresce em termos absolutos nas UFs "
            "com maior nivel geral de renda, como Sao Paulo, Rio Grande do Sul, Santa Catarina, "
            "Rio de Janeiro e Parana."
        ),
        (
            "Como a base foi estimada a partir de medias nacionais ajustadas por um indice "
            "estadual, a leitura mais segura nao e causal: o modelo descreve uma associacao "
            "entre grupos ocupacionais com e sem exigencia de ensino superior, e nao o efeito "
            "de anos adicionais de estudo sobre salario."
        ),
        (
            "Por isso, a principal utilidade economica da analise esta em comparar o tamanho do "
            "premio salarial e a faixa prevista de rendimentos entre estados, e nao em inferir "
            "impacto causal de escolaridade individual."
        ),
        "",
        "Leitura economica",
        "-----------------",
        (
            "Como os salarios do JSON foram estimados a partir de medias nacionais por grupo "
            "ocupacional ajustadas por um indice estadual, os modelos produzem um R2 alto e "
            "bastante homogeneo entre os estados. A comparacao mais util aqui e o tamanho "
            "absoluto do premio salarial e a faixa prevista de salarios por UF."
        ),
    ]
    return "\n".join(sections).strip()


def _style_axis(ax) -> None:
    ax.set_facecolor(PANEL_BG)
    for spine in ax.spines.values():
        spine.set_color(BORDER_COLOR)
        spine.set_linewidth(1.0)
    ax.tick_params(colors=TEXT_MUTED, labelsize=9)
    ax.grid(axis="x", color=GRID_COLOR, linestyle="--", linewidth=0.8, alpha=0.55)
    ax.set_axisbelow(True)


def _currency_axis_formatter(value: float, _pos: float) -> str:
    return format_brl_compact(value)


def build_dashboard_figure(payload: dict, data: pd.DataFrame, regressions: pd.DataFrame) -> Figure:
    metadata = payload.get("metadata", {})
    ranking_premium = regressions.sort_values("premio_superior_brl", ascending=True)
    state_profile = regressions.sort_values("salario_medio_geral_brl").reset_index(drop=True)

    fig = Figure(figsize=(14.2, 9.6), facecolor=FIG_BG)
    gs = fig.add_gridspec(
        nrows=2,
        ncols=1,
        height_ratios=[1.0, 1.12],
        hspace=0.32,
    )

    ax_premium = fig.add_subplot(gs[0, 0])
    ax_profile = fig.add_subplot(gs[1, 0])

    header_x = 0.06
    header_y = 0.985
    fig.text(
        header_x,
        header_y,
        "Salario x Escolaridade por Estado",
        color=TEXT_PRIMARY,
        fontsize=17,
        fontweight="bold",
        ha="left",
        va="top",
    )
    fig.text(
        header_x,
        header_y,
        (
            f"{metadata.get('title', 'Base salarial por estado')} | "
            f"Gerado em {metadata.get('generated_on', 'n/d')}"
        ),
        color=TEXT_MUTED,
        fontsize=9.4,
        ha="left",
        va="top",
        transform=fig.transFigure
        + ScaledTranslation(0, -26 / 72, fig.dpi_scale_trans),
    )
    fig.text(
        header_x,
        header_y,
        (
            "Visao sintetica por UF: premio salarial associado ao ensino superior "
            "e faixa prevista entre ocupacoes com e sem essa exigencia."
        ),
        color=TEXT_MUTED,
        fontsize=9.0,
        ha="left",
        va="top",
        transform=fig.transFigure
        + ScaledTranslation(0, -42 / 72, fig.dpi_scale_trans),
    )

    _style_axis(ax_premium)
    premium_labels = [row.estado for row in ranking_premium.itertuples(index=False)]
    premium_values = ranking_premium["premio_superior_brl"]
    premium_positions = list(range(len(premium_labels)))
    ax_premium.barh(
        premium_positions,
        premium_values,
        color=ACCENT,
        alpha=0.88,
        tick_label=premium_labels,
    )
    ax_premium.set_title(
        "Premio salarial por UF",
        color=TEXT_PRIMARY,
        fontsize=12.5,
        fontweight="bold",
        pad=12,
    )
    ax_premium.set_xlabel(
        "Diferenca salarial associada a ocupacoes com exigencia de ensino superior",
        color=TEXT_MUTED,
        fontsize=9.5,
        labelpad=2,
    )
    ax_premium.xaxis.set_major_formatter(FuncFormatter(_currency_axis_formatter))
    ax_premium.set_ylabel("")
    ax_premium.tick_params(axis="y", labelsize=9.5, colors=TEXT_PRIMARY)
    ax_premium.margins(x=0.18)
    label_offset = float(premium_values.max()) * 0.014
    for position, row in zip(premium_positions, ranking_premium.itertuples(index=False)):
        ax_premium.text(
            row.premio_superior_brl + label_offset,
            position,
            f"{format_brl_compact(row.premio_superior_brl)} | {format_percent(row.premio_superior_percentual)}",
            color=TEXT_PRIMARY,
            fontsize=8.5,
            va="center",
        )

    _style_axis(ax_profile)
    ax_profile.grid(axis="y", color=GRID_COLOR, linestyle="-", linewidth=0.7, alpha=0.25)
    y_positions = list(range(len(state_profile)))
    labels = [row.estado for row in state_profile.itertuples(index=False)]
    salary_without = state_profile["salario_sem_superior_brl"]
    salary_with = state_profile["salario_com_superior_brl"]

    ax_profile.hlines(
        y_positions,
        salary_without,
        salary_with,
        color=LINE_COLOR,
        linewidth=2.2,
        alpha=0.7,
    )
    ax_profile.scatter(
        salary_without,
        y_positions,
        color=SECONDARY,
        s=34,
        zorder=3,
        label="Sem superior",
    )
    ax_profile.scatter(
        salary_with,
        y_positions,
        color=ACCENT,
        s=38,
        zorder=4,
        label="Com superior",
    )
    max_salary = float(salary_with.max())
    for position, row in enumerate(state_profile.itertuples(index=False)):
        ax_profile.text(
            row.salario_com_superior_brl + max_salary * 0.02,
            position,
            (
                f"{format_brl_compact(row.salario_com_superior_brl)} | "
                f"{format_percent(row.premio_superior_percentual)}"
            ),
            color=TEXT_PRIMARY,
            fontsize=8.5,
            ha="left",
            va="center",
        )

    ax_profile.set_title(
        "Faixa salarial prevista por UF",
        color=TEXT_PRIMARY,
        fontsize=13,
        fontweight="bold",
        pad=10,
    )
    ax_profile.set_xlabel(
        "Salario estimado",
        color=TEXT_MUTED,
        fontsize=9.5,
    )
    ax_profile.set_ylabel("")
    ax_profile.set_yticks(y_positions)
    ax_profile.set_yticklabels(labels, fontsize=9.5, color=TEXT_PRIMARY)
    ax_profile.xaxis.set_major_formatter(FuncFormatter(_currency_axis_formatter))
    ax_profile.set_xlim(0, max_salary * 1.34)
    ax_profile.tick_params(axis="y", labelsize=9.5, colors=TEXT_PRIMARY)
    legend = ax_profile.legend(
        loc="upper left",
        frameon=True,
        facecolor=PANEL_BG,
        edgecolor=BORDER_COLOR,
        labelcolor=TEXT_PRIMARY,
        fontsize=9,
        ncol=2,
    )
    for text in legend.get_texts():
        text.set_color(TEXT_PRIMARY)

    fig.text(
        0.015,
        0.014,
        (
            "Leitura: os charts priorizam comparacao por UF, com menos texto dentro do painel "
            "e rotulos curtos para preservar legibilidade quando o dashboard for exibido em telas menores."
        ),
        color=TEXT_MUTED,
        fontsize=9.2,
    )
    fig.subplots_adjust(left=0.12, right=0.96, top=0.79, bottom=0.08)
    return fig


def _format_report_text(stats_text: str) -> str:
    intro = [
        "Relatorio do modulo 05 - regressao salario x escolaridade",
        "",
        "Arquivos gerados automaticamente:",
        f"- {OUTPUT_SUMMARY}",
        f"- {OUTPUT_FLAT_DATA}",
        f"- {OUTPUT_STATE_MEANS}",
        f"- {OUTPUT_REGRESSIONS}",
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
    fig = Figure(figsize=(8.27, 11.69), facecolor="white")
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


def save_pdf_report(stats_text: str, dashboard_figure: Figure, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / OUTPUT_PDF
    report_figure = _build_report_figure(stats_text)
    with PdfPages(pdf_path) as pdf:
        pdf.savefig(report_figure, dpi=150)
        pdf.savefig(dashboard_figure, dpi=150)
    return pdf_path


def save_outputs(
    stats_text: str,
    analysis_frame: pd.DataFrame,
    state_means: pd.DataFrame,
    regressions: pd.DataFrame,
    dashboard_figure: Figure,
    output_dir: Path,
) -> tuple[Path, Path, Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_path = output_dir / OUTPUT_SUMMARY
    flat_data_path = output_dir / OUTPUT_FLAT_DATA
    state_means_path = output_dir / OUTPUT_STATE_MEANS
    regressions_path = output_dir / OUTPUT_REGRESSIONS
    dashboard_path = output_dir / OUTPUT_PNG

    summary_path.write_text(stats_text + "\n", encoding="utf-8")
    analysis_frame.to_csv(flat_data_path, index=False)
    state_means.to_csv(state_means_path, index=False)
    regressions.to_csv(regressions_path, index=False)
    dashboard_figure.savefig(dashboard_path, dpi=180, facecolor=dashboard_figure.get_facecolor())

    return summary_path, flat_data_path, state_means_path, regressions_path, dashboard_path


def run_pipeline(input_path: Path, output_dir: Path | None = None) -> PipelineResult:
    payload = load_payload(input_path)
    final_output_dir = output_dir or DEFAULT_OUTPUT_DIR

    analysis_frame = build_analysis_frame(payload)
    state_means = build_state_means(analysis_frame)
    regressions = build_state_regressions(analysis_frame)
    stats_text = build_stats_text(input_path, payload, analysis_frame, state_means, regressions)
    dashboard_figure = build_dashboard_figure(payload, analysis_frame, regressions)

    (
        summary_path,
        flat_data_path,
        state_means_path,
        regressions_path,
        dashboard_path,
    ) = save_outputs(
        stats_text=stats_text,
        analysis_frame=analysis_frame,
        state_means=state_means,
        regressions=regressions,
        dashboard_figure=dashboard_figure,
        output_dir=final_output_dir,
    )

    return PipelineResult(
        stats_text=stats_text,
        figure=dashboard_figure,
        analysis_frame=analysis_frame,
        state_means_df=state_means,
        regressions_df=regressions,
        output_dir=final_output_dir,
        summary_path=summary_path,
        flat_data_path=flat_data_path,
        state_means_path=state_means_path,
        regressions_path=regressions_path,
        dashboard_path=dashboard_path,
    )


def main() -> None:
    args = parse_args()
    result = run_pipeline(args.arquivo, args.saida)

    print(result.stats_text)
    print("\nArquivos gerados:")
    print(f"- {result.summary_path}")
    print(f"- {result.flat_data_path}")
    print(f"- {result.state_means_path}")
    print(f"- {result.regressions_path}")
    print(f"- {result.dashboard_path}")

    if args.pdf:
        pdf_path = save_pdf_report(result.stats_text, result.figure, result.output_dir)
        print(f"- {pdf_path}")
