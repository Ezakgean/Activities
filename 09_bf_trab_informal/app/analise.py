from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

from matplotlib import dates as mdates
from matplotlib import pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = BASE_DIR / "data" / "input" / "DadosEconometria.xlsx"
DEFAULT_OUTPUT_DIR = BASE_DIR / "data" / "output"
OUTPUT_FILENAME = "series_extraidas.json"
CHARTS_DIRNAME = "graficos_series"
CORRELATION_CHARTS_DIRNAME = "graficos_correlacoes"
COMOVEMENT_CHARTS_DIRNAME = "graficos_comovimento"
CORRELATION_TARGETS = (
    "taxa_informalidade",
    "pessoas_informais_mil",
)
COMOVEMENT_TARGET = "pessoas_informais_mil"


SERIES_TABELAS = [
    {
        "tema": "Trabalho informal — taxa",
        "aba": "Tabela 29",
        "variavel": "Taxa de informalidade das pessoas ocupadas (%)",
        "chave": "taxa_informalidade",
    },
    {
        "tema": "Trabalho informal — quantidade",
        "aba": "Tabela 31",
        "variavel": "Pessoas ocupadas em situação de informalidade, em mil pessoas",
        "chave": "pessoas_informais_mil",
    },
    {
        "tema": "Pessoas ocupadas",
        "aba": "Tabela 9",
        "variavel": "Pessoas ocupadas, em mil pessoas",
        "chave": "pessoas_ocupadas_mil",
    },
    {
        "tema": "Pessoas desocupadas",
        "aba": "Tabela 13",
        "variavel": "Pessoas desocupadas, em mil pessoas",
        "chave": "pessoas_desocupadas_mil",
    },
    {
        "tema": "Taxa de desocupação",
        "aba": "Tabela 27",
        "variavel": "Taxa de desocupação (%)",
        "chave": "taxa_desocupacao",
    },
    {
        "tema": "Força de trabalho",
        "aba": "Tabela 5",
        "variavel": "Pessoas na força de trabalho, em mil pessoas",
        "chave": "forca_trabalho_mil",
    },
    {
        "tema": "Fora da força de trabalho",
        "aba": "Tabela 17",
        "variavel": "Pessoas fora da força de trabalho, em mil pessoas",
        "chave": "fora_forca_trabalho_mil",
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extrai series especificas da planilha da atividade 09 e salva em JSON."
    )
    parser.add_argument(
        "--arquivo",
        type=Path,
        default=DEFAULT_INPUT,
        help="Arquivo Excel de entrada.",
    )
    parser.add_argument(
        "--saida",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Pasta onde o JSON sera salvo.",
    )
    return parser.parse_args()


def converter_excel_serial_para_data(valor: object) -> pd.Timestamp | pd.NaT:
    if pd.isna(valor):
        return pd.NaT
    if isinstance(valor, (int, float)):
        return pd.to_datetime("1899-12-30") + pd.to_timedelta(int(valor), unit="D")
    return pd.to_datetime(valor, errors="coerce")


def converter_trimestre(texto: object) -> str | None:
    if pd.isna(texto):
        return None

    match = re.search(r"([1-4]).*?trimestre.*?(\d{4})", str(texto).lower())
    if not match:
        return None

    return f"{match.group(2)}T{match.group(1)}"


def limpar_numero(valor: object) -> float | None:
    if pd.isna(valor):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)

    texto = str(valor).strip()
    if texto in {"...", "-", ""}:
        return None

    texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None


def extrair_serie_tabela(arquivo: Path, aba: str, chave: str) -> list[dict[str, object]]:
    df = pd.read_excel(arquivo, sheet_name=aba, header=None)

    periodos = df.iloc[3, 1:58].tolist()
    valores = df.iloc[5, 1:58].tolist()

    registros: list[dict[str, object]] = []
    for periodo, valor in zip(periodos, valores, strict=True):
        trimestre = converter_trimestre(periodo)
        valor_limpo = limpar_numero(valor)
        if trimestre is None:
            continue

        registros.append(
            {
                "trimestre": trimestre,
                chave: valor_limpo,
            }
        )

    return registros


def extrair_bolsa_familia(arquivo: Path) -> list[dict[str, object]]:
    df = pd.read_excel(
        arquivo,
        sheet_name="visdata3-download-01-07-2026 17",
        usecols="A:C",
        nrows=136,
    )

    df.columns = [
        "referencia",
        "pbf_ate_2021",
        "pbf_a_partir_2023",
    ]
    df["data"] = df["referencia"].apply(converter_excel_serial_para_data)
    df["pessoas_beneficiarias_pbf"] = df["pbf_ate_2021"].combine_first(df["pbf_a_partir_2023"])
    df["pessoas_beneficiarias_pbf"] = df["pessoas_beneficiarias_pbf"].apply(limpar_numero)
    df = df.dropna(subset=["data", "pessoas_beneficiarias_pbf"]).copy()

    registros: list[dict[str, object]] = []
    for _, row in df.iterrows():
        data = row["data"]
        if pd.isna(data):
            continue
        registros.append(
            {
                "data": data.strftime("%Y-%m-%d"),
                "pessoas_beneficiarias_pbf": row["pessoas_beneficiarias_pbf"],
            }
        )

    return registros


def sanitizar_json(valor: object) -> object:
    if isinstance(valor, dict):
        return {chave: sanitizar_json(item) for chave, item in valor.items()}
    if isinstance(valor, list):
        return [sanitizar_json(item) for item in valor]
    if isinstance(valor, pd.Timestamp):
        return valor.strftime("%Y-%m-%d")
    if isinstance(valor, np.generic):
        return valor.item()
    return valor


def slugify(texto: str) -> str:
    texto = texto.lower()
    texto = re.sub(r"[^a-z0-9]+", "_", texto)
    return texto.strip("_")


def formatar_valor_eixo(valor: float, _: float) -> str:
    absoluto = abs(valor)
    if absoluto >= 1_000_000:
        return f"{valor / 1_000_000:.1f} mi"
    if absoluto >= 1_000:
        return f"{valor / 1_000:.0f} mil"
    return f"{valor:.1f}".rstrip("0").rstrip(".")


def trimestre_para_timestamp(valor: str) -> pd.Timestamp:
    match = re.fullmatch(r"(\d{4})T([1-4])", str(valor))
    if not match:
        raise ValueError(f"Trimestre invalido: {valor}")

    ano = int(match.group(1))
    trimestre = int(match.group(2))
    mes_final = trimestre * 3
    periodo = pd.Period(year=ano, month=mes_final, freq="M")
    return periodo.to_timestamp(how="end")


def trimestre_para_ordinal(valor: str) -> int:
    match = re.fullmatch(r"(\d{4})T([1-4])", str(valor))
    if not match:
        raise ValueError(f"Trimestre invalido: {valor}")

    ano = int(match.group(1))
    trimestre = int(match.group(2))
    return ano * 4 + (trimestre - 1)


def montar_dataframe_serie(chave: str, serie: dict[str, object]) -> tuple[pd.DataFrame, str, str]:
    dados = pd.DataFrame(serie["dados"])
    coluna_valor = next(coluna for coluna in dados.columns if coluna not in {"data", "trimestre"})
    coluna_periodo = "data" if "data" in dados.columns else "trimestre"

    if coluna_periodo == "data":
        dados["periodo"] = pd.to_datetime(dados["data"], errors="coerce")
    else:
        dados["periodo"] = dados["trimestre"].apply(trimestre_para_timestamp)

    dados["valor"] = pd.to_numeric(dados[coluna_valor], errors="coerce")
    dados = dados.dropna(subset=["periodo", "valor"]).sort_values("periodo").reset_index(drop=True)
    return dados, coluna_periodo, coluna_valor


def agregar_bolsa_familia_trimestral(payload: dict[str, object]) -> pd.DataFrame:
    serie_bf = payload["series"]["bolsa_familia"]
    dados, _, coluna_valor = montar_dataframe_serie("bolsa_familia", serie_bf)
    trimestral = (
        dados.assign(trimestre=dados["periodo"].dt.to_period("Q"))
        .groupby("trimestre", as_index=False)
        .agg(pessoas_beneficiarias_pbf_media_tri=("valor", "mean"))
    )
    trimestral["trimestre"] = trimestral["trimestre"].astype(str).str.replace("Q", "T", regex=False)
    return trimestral


def agregar_serie_por_trimestre_unico(
    chave: str,
    serie: dict[str, object],
) -> pd.DataFrame:
    dados, _, _ = montar_dataframe_serie(chave, serie)
    if dados.empty:
        return pd.DataFrame(columns=["trimestre", chave])

    dados["trimestre"] = dados["periodo"].dt.to_period("Q").astype(str).str.replace("Q", "T", regex=False)
    agregado = (
        dados.groupby("trimestre", as_index=False)
        .agg(valor=("valor", "mean"))
        .rename(columns={"valor": chave})
    )
    return agregado


def construir_base_pareada_trimestre_unico(
    payload: dict[str, object],
    chave_y: str,
) -> pd.DataFrame:
    bolsa_familia_tri = agregar_bolsa_familia_trimestral(payload)
    serie_y = agregar_serie_por_trimestre_unico(chave_y, payload["series"][chave_y])

    base = (
        bolsa_familia_tri.merge(serie_y, on="trimestre", how="inner")
        .dropna(subset=["pessoas_beneficiarias_pbf_media_tri", chave_y])
        .drop_duplicates(subset=["trimestre"])
        .sort_values("trimestre")
        .reset_index(drop=True)
    )
    return base


def calcular_correlacoes(payload: dict[str, object]) -> list[dict[str, object]]:
    resultados: list[dict[str, object]] = []

    for chave in CORRELATION_TARGETS:
        serie = payload["series"][chave]
        base = construir_base_pareada_trimestre_unico(payload, chave)
        if base.empty:
            resultados.append(
                {
                    "metodo": "pareamento por trimestre unico",
                    "variavel_x": "pessoas_beneficiarias_pbf_media_tri",
                    "variavel_y": chave,
                    "tema_y": serie["tema"],
                    "variavel_descricao_y": serie["variavel"],
                    "n_observacoes_nivel": 0,
                    "correlacao_nivel": None,
                    "n_observacoes_variacao": 0,
                    "correlacao_variacao": None,
                    "criterio_variacao": "diferenca apenas entre trimestres consecutivos disponiveis na base",
                    "dados_pareados_trimestre_unico": [],
                }
            )
            continue

        correlacao_nivel = base["pessoas_beneficiarias_pbf_media_tri"].corr(base[chave], method="pearson")

        base_com_periodo = base.copy()
        base_com_periodo["periodo"] = base_com_periodo["trimestre"].apply(trimestre_para_timestamp)
        variacoes = construir_base_variacoes(base_com_periodo, chave).rename(
            columns={"var_bf": "var_bolsa_familia", "var_y": f"var_{chave}"}
        )
        correlacao_variacao = (
            variacoes["var_bolsa_familia"].corr(variacoes[f"var_{chave}"], method="pearson")
            if not variacoes.empty
            else None
        )

        resultados.append(
            {
                "metodo": "pareamento por trimestre unico",
                "variavel_x": "pessoas_beneficiarias_pbf_media_tri",
                "variavel_y": chave,
                "tema_y": serie["tema"],
                "variavel_descricao_y": serie["variavel"],
                "n_observacoes_nivel": int(len(base)),
                "correlacao_nivel": None if pd.isna(correlacao_nivel) else float(correlacao_nivel),
                "n_observacoes_variacao": int(len(variacoes)),
                "correlacao_variacao": None if pd.isna(correlacao_variacao) else float(correlacao_variacao),
                "criterio_variacao": "diferenca apenas entre trimestres consecutivos disponiveis na base",
                "dados_pareados_trimestre_unico": base.to_dict(orient="records"),
            }
        )

    return resultados


def calcular_comovimento(payload: dict[str, object]) -> dict[str, object]:
    serie = payload["series"][COMOVEMENT_TARGET]
    base = construir_base_pareada_trimestre_unico(payload, COMOVEMENT_TARGET)
    if base.empty:
        return {
            "metodo": "pareamento por trimestre unico",
            "variavel_x": "pessoas_beneficiarias_pbf_media_tri",
            "variavel_y": COMOVEMENT_TARGET,
            "tema_y": serie["tema"],
            "variavel_descricao_y": serie["variavel"],
            "n_observacoes": 0,
            "dados_pareados_trimestre_unico": [],
        }

    base = base.copy()
    base["bf_tri_zscore"] = (
        (base["pessoas_beneficiarias_pbf_media_tri"] - base["pessoas_beneficiarias_pbf_media_tri"].mean())
        / base["pessoas_beneficiarias_pbf_media_tri"].std(ddof=0)
    )
    base[f"{COMOVEMENT_TARGET}_zscore"] = (
        (base[COMOVEMENT_TARGET] - base[COMOVEMENT_TARGET].mean())
        / base[COMOVEMENT_TARGET].std(ddof=0)
    )

    base["bf_tri_indice_base_100"] = (
        base["pessoas_beneficiarias_pbf_media_tri"] / base["pessoas_beneficiarias_pbf_media_tri"].iloc[0] * 100
    )
    base[f"{COMOVEMENT_TARGET}_indice_base_100"] = (
        base[COMOVEMENT_TARGET] / base[COMOVEMENT_TARGET].iloc[0] * 100
    )

    return {
        "metodo": "pareamento por trimestre unico",
        "variavel_x": "pessoas_beneficiarias_pbf_media_tri",
        "variavel_y": COMOVEMENT_TARGET,
        "tema_y": serie["tema"],
        "variavel_descricao_y": serie["variavel"],
        "n_observacoes": int(len(base)),
        "dados_pareados_trimestre_unico": base.to_dict(orient="records"),
    }


def salvar_grafico_serie(chave: str, serie: dict[str, object], pasta_graficos: Path) -> Path | None:
    dados, coluna_periodo, _ = montar_dataframe_serie(chave, serie)
    if dados.empty:
        return None

    fig, ax = plt.subplots(figsize=(16, 9), dpi=160)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#fbfbfc")

    ax.plot(
        dados["periodo"],
        dados["valor"],
        color="#0b6e4f",
        linewidth=2.4,
        marker="o",
        markersize=3.4,
        markerfacecolor="#0b6e4f",
        markeredgewidth=0,
    )
    ax.fill_between(dados["periodo"], dados["valor"], color="#0b6e4f", alpha=0.10)

    titulo = str(serie["tema"])
    subtitulo = str(serie["variavel"])
    fig.suptitle(titulo, x=0.06, y=0.965, ha="left", va="top", fontsize=22, fontweight="bold")
    fig.text(0.06, 0.925, subtitulo, ha="left", va="top", fontsize=13, color="#243b53")

    cabecalho = (
        f"Aba: {serie['aba']}\n"
        f"Intervalo: {serie['intervalo']}\n"
        f"Variável: {serie['variavel']}\n"
        f"Observações: {len(dados)}"
    )
    fig.text(
        0.06,
        0.875,
        cabecalho,
        ha="left",
        va="top",
        fontsize=11,
        color="#334e68",
        bbox={"boxstyle": "round,pad=0.5", "facecolor": "#eef4f7", "edgecolor": "#d9e2ec"},
    )

    ax.grid(True, axis="y", linestyle="--", linewidth=0.8, alpha=0.35)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#9fb3c8")
    ax.spines["bottom"].set_color("#9fb3c8")
    ax.tick_params(axis="x", labelsize=10, colors="#243b53")
    ax.tick_params(axis="y", labelsize=10, colors="#243b53")
    ax.yaxis.set_major_formatter(FuncFormatter(formatar_valor_eixo))

    if coluna_periodo == "data":
        ax.xaxis.set_major_locator(mdates.YearLocator(base=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    else:
        ax.xaxis.set_major_locator(mdates.YearLocator(base=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    ax.set_xlabel("Período", fontsize=11, color="#102a43", labelpad=10)
    ax.set_ylabel("Valor", fontsize=11, color="#102a43", labelpad=10)

    ultimo = dados.iloc[-1]
    ax.scatter([ultimo["periodo"]], [ultimo["valor"]], color="#d64550", s=48, zorder=5)
    ax.annotate(
        f"{ultimo['valor']:,.2f}".replace(",", "_").replace(".", ",").replace("_", "."),
        xy=(ultimo["periodo"], ultimo["valor"]),
        xytext=(12, 12),
        textcoords="offset points",
        fontsize=10,
        color="#7a1f2b",
        bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": "#f0b4bb"},
    )

    fig.subplots_adjust(top=0.72, left=0.08, right=0.97, bottom=0.12)

    arquivo_grafico = pasta_graficos / f"{slugify(chave)}.png"
    fig.savefig(arquivo_grafico, bbox_inches="tight")
    plt.close(fig)
    return arquivo_grafico


def adicionar_cabecalho_correlacao(fig: plt.Figure, correlacao: dict[str, object], subtitulo: str) -> None:
    titulo = f"Correlação: Bolsa Família x {correlacao['tema_y']}"
    fig.suptitle(titulo, x=0.05, y=0.97, ha="left", va="top", fontsize=22, fontweight="bold")
    fig.text(0.05, 0.935, subtitulo, ha="left", va="top", fontsize=13, color="#243b53")
    fig.text(
        0.05,
        0.895,
        (
            f"X: pessoas_beneficiarias_pbf_media_tri\n"
            f"Y: {correlacao['variavel_descricao_y']}\n"
            f"Observações em nível: {correlacao['n_observacoes_nivel']}\n"
            f"Observações em variação: {correlacao['n_observacoes_variacao']}\n"
            f"Variação: trimestres consecutivos disponíveis"
        ),
        ha="left",
        va="top",
        fontsize=11,
        color="#334e68",
        bbox={"boxstyle": "round,pad=0.5", "facecolor": "#eef4f7", "edgecolor": "#d9e2ec"},
    )

def estilizar_eixos(ax: plt.Axes, usar_datas: bool = False) -> None:
    ax.set_facecolor("#fbfbfc")
    ax.grid(True, axis="y", linestyle="--", linewidth=0.8, alpha=0.35)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#9fb3c8")
    ax.spines["bottom"].set_color("#9fb3c8")
    ax.tick_params(axis="x", labelsize=10, colors="#243b53")
    ax.tick_params(axis="y", labelsize=10, colors="#243b53")
    ax.yaxis.set_major_formatter(FuncFormatter(formatar_valor_eixo))
    if usar_datas:
        ax.xaxis.set_major_locator(mdates.YearLocator(base=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))


def construir_base_variacoes(dados: pd.DataFrame, y_key: str) -> pd.DataFrame:
    variacoes = dados[["periodo", "pessoas_beneficiarias_pbf_media_tri", y_key]].copy()
    variacoes["trimestre_ordinal"] = dados["trimestre"].apply(trimestre_para_ordinal).to_numpy()
    variacoes["gap_trimestres"] = variacoes["trimestre_ordinal"].diff()
    variacoes["var_bf"] = variacoes["pessoas_beneficiarias_pbf_media_tri"].diff()
    variacoes["var_y"] = variacoes[y_key].diff()
    variacoes.loc[variacoes["gap_trimestres"] != 1, ["var_bf", "var_y"]] = np.nan
    return variacoes.dropna(subset=["var_bf", "var_y"]).reset_index(drop=True)


def adicionar_cabecalho_comovimento(fig: plt.Figure, comovimento: dict[str, object], subtitulo: str) -> None:
    titulo = f"Co-movimento: Bolsa Família x {comovimento['tema_y']}"
    fig.suptitle(titulo, x=0.05, y=0.97, ha="left", va="top", fontsize=22, fontweight="bold")
    fig.text(0.05, 0.935, subtitulo, ha="left", va="top", fontsize=13, color="#243b53")
    fig.text(
        0.05,
        0.895,
        (
            f"X: pessoas_beneficiarias_pbf_media_tri\n"
            f"Y: {comovimento['variavel_descricao_y']}\n"
            f"Método: {comovimento['metodo']}\n"
            f"Observações: {comovimento['n_observacoes']}"
        ),
        ha="left",
        va="top",
        fontsize=11,
        color="#334e68",
        bbox={"boxstyle": "round,pad=0.5", "facecolor": "#eef4f7", "edgecolor": "#d9e2ec"},
    )


def salvar_graficos_correlacao(correlacao: dict[str, object], pasta_graficos: Path) -> list[Path]:
    dados = pd.DataFrame(correlacao["dados_pareados_trimestre_unico"])
    if dados.empty:
        return []

    y_key = str(correlacao["variavel_y"])
    slug = slugify(y_key)
    dados["periodo"] = dados["trimestre"].apply(trimestre_para_timestamp)
    variacoes = construir_base_variacoes(dados, y_key)
    arquivos: list[Path] = []

    fig, ax = plt.subplots(figsize=(18, 10), dpi=180)
    fig.patch.set_facecolor("white")
    adicionar_cabecalho_correlacao(fig, correlacao, "Séries padronizadas em nível")
    base_norm = dados[["pessoas_beneficiarias_pbf_media_tri", y_key]].copy()
    base_norm = (base_norm - base_norm.mean()) / base_norm.std(ddof=0)
    ax.plot(dados["periodo"], base_norm["pessoas_beneficiarias_pbf_media_tri"], color="#0b6e4f", linewidth=2.4, label="BF tri (z-score)")
    ax.plot(dados["periodo"], base_norm[y_key], color="#d64550", linewidth=2.4, label="Y (z-score)")
    ax.set_title("Séries padronizadas em nível", loc="left", fontsize=14, fontweight="bold")
    ax.set_xlabel("Período", fontsize=11, color="#102a43")
    ax.set_ylabel("Z-score", fontsize=11, color="#102a43")
    ax.legend(frameon=False, fontsize=11, loc="upper right")
    estilizar_eixos(ax, usar_datas=True)
    fig.subplots_adjust(top=0.74, left=0.08, right=0.97, bottom=0.12)
    arquivo = pasta_graficos / f"correlacao_{slug}_nivel_series.png"
    fig.savefig(arquivo, bbox_inches="tight")
    plt.close(fig)
    arquivos.append(arquivo)

    fig, ax = plt.subplots(figsize=(14, 10), dpi=180)
    fig.patch.set_facecolor("white")
    adicionar_cabecalho_correlacao(fig, correlacao, "Dispersão em nível")
    ax.scatter(dados["pessoas_beneficiarias_pbf_media_tri"], dados[y_key], color="#1565c0", alpha=0.85, s=46)
    ax.set_title(
        f"Dispersão em nível | Pearson = {correlacao['correlacao_nivel']:.3f}" if correlacao["correlacao_nivel"] is not None else "Dispersão em nível | Pearson = n/d",
        loc="left",
        fontsize=14,
        fontweight="bold",
    )
    ax.set_xlabel("Bolsa Família trimestral médio", fontsize=11, color="#102a43")
    ax.set_ylabel(str(correlacao["variavel_descricao_y"]), fontsize=11, color="#102a43")
    estilizar_eixos(ax, usar_datas=False)
    fig.subplots_adjust(top=0.74, left=0.10, right=0.97, bottom=0.12)
    arquivo = pasta_graficos / f"correlacao_{slug}_nivel_dispersao.png"
    fig.savefig(arquivo, bbox_inches="tight")
    plt.close(fig)
    arquivos.append(arquivo)

    if not variacoes.empty:
        fig, ax = plt.subplots(figsize=(18, 10), dpi=180)
        fig.patch.set_facecolor("white")
        adicionar_cabecalho_correlacao(fig, correlacao, "Variações entre trimestres consecutivos disponíveis")
        ax.bar(variacoes["periodo"], variacoes["var_bf"], width=50, color="#0b6e4f", alpha=0.55, label="Δ BF")
        ax.plot(variacoes["periodo"], variacoes["var_y"], color="#d64550", linewidth=2.2, marker="o", markersize=3.2, label="Δ Y")
        ax.set_title("Variações entre trimestres consecutivos disponíveis", loc="left", fontsize=14, fontweight="bold")
        ax.set_xlabel("Período", fontsize=11, color="#102a43")
        ax.set_ylabel("Variação trimestral", fontsize=11, color="#102a43")
        ax.legend(frameon=False, fontsize=11, loc="upper right")
        estilizar_eixos(ax, usar_datas=True)
        fig.subplots_adjust(top=0.74, left=0.08, right=0.97, bottom=0.12)
        arquivo = pasta_graficos / f"correlacao_{slug}_variacao_series.png"
        fig.savefig(arquivo, bbox_inches="tight")
        plt.close(fig)
        arquivos.append(arquivo)

        fig, ax = plt.subplots(figsize=(14, 10), dpi=180)
        fig.patch.set_facecolor("white")
        adicionar_cabecalho_correlacao(fig, correlacao, "Dispersão das variações entre trimestres consecutivos disponíveis")
        ax.scatter(variacoes["var_bf"], variacoes["var_y"], color="#7a3eb1", alpha=0.85, s=46)
        ax.set_title(
            f"Dispersão das variações entre trimestres consecutivos disponíveis | Pearson = {correlacao['correlacao_variacao']:.3f}" if correlacao["correlacao_variacao"] is not None else "Dispersão das variações entre trimestres consecutivos disponíveis | Pearson = n/d",
            loc="left",
            fontsize=14,
            fontweight="bold",
        )
        ax.set_xlabel("Δ Bolsa Família trimestral médio", fontsize=11, color="#102a43")
        ax.set_ylabel(f"Δ {correlacao['variavel_descricao_y']}", fontsize=11, color="#102a43")
        estilizar_eixos(ax, usar_datas=False)
        fig.subplots_adjust(top=0.74, left=0.10, right=0.97, bottom=0.12)
        arquivo = pasta_graficos / f"correlacao_{slug}_variacao_dispersao.png"
        fig.savefig(arquivo, bbox_inches="tight")
        plt.close(fig)
        arquivos.append(arquivo)

    return arquivos


def salvar_graficos_comovimento(comovimento: dict[str, object], pasta_graficos: Path) -> list[Path]:
    dados = pd.DataFrame(comovimento["dados_pareados_trimestre_unico"])
    if dados.empty:
        return []

    dados["periodo"] = dados["trimestre"].apply(trimestre_para_timestamp)
    slug = slugify(str(comovimento["variavel_y"]))
    arquivos: list[Path] = []

    fig, ax = plt.subplots(figsize=(18, 10), dpi=180)
    fig.patch.set_facecolor("white")
    adicionar_cabecalho_comovimento(fig, comovimento, "Séries padronizadas por z-score")
    ax.plot(dados["periodo"], dados["bf_tri_zscore"], color="#0b6e4f", linewidth=2.5, label="BF tri (z-score)")
    ax.plot(
        dados["periodo"],
        dados[f"{COMOVEMENT_TARGET}_zscore"],
        color="#d64550",
        linewidth=2.5,
        label="Informalidade (z-score)",
    )
    ax.set_title("Co-movimento em séries padronizadas", loc="left", fontsize=14, fontweight="bold")
    ax.set_xlabel("Período", fontsize=11, color="#102a43")
    ax.set_ylabel("Z-score", fontsize=11, color="#102a43")
    ax.legend(frameon=False, fontsize=11, loc="upper right")
    estilizar_eixos(ax, usar_datas=True)
    fig.subplots_adjust(top=0.74, left=0.08, right=0.97, bottom=0.12)
    arquivo = pasta_graficos / f"comovimento_{slug}_zscore.png"
    fig.savefig(arquivo, bbox_inches="tight")
    plt.close(fig)
    arquivos.append(arquivo)

    fig, ax = plt.subplots(figsize=(18, 10), dpi=180)
    fig.patch.set_facecolor("white")
    adicionar_cabecalho_comovimento(fig, comovimento, "Séries em índice base 100")
    ax.plot(dados["periodo"], dados["bf_tri_indice_base_100"], color="#0b6e4f", linewidth=2.5, label="BF tri (base 100)")
    ax.plot(
        dados["periodo"],
        dados[f"{COMOVEMENT_TARGET}_indice_base_100"],
        color="#d64550",
        linewidth=2.5,
        label="Informalidade (base 100)",
    )
    ax.set_title("Co-movimento em índice base 100", loc="left", fontsize=14, fontweight="bold")
    ax.set_xlabel("Período", fontsize=11, color="#102a43")
    ax.set_ylabel("Índice", fontsize=11, color="#102a43")
    ax.legend(frameon=False, fontsize=11, loc="upper right")
    estilizar_eixos(ax, usar_datas=True)
    fig.subplots_adjust(top=0.74, left=0.08, right=0.97, bottom=0.12)
    arquivo = pasta_graficos / f"comovimento_{slug}_indice_base_100.png"
    fig.savefig(arquivo, bbox_inches="tight")
    plt.close(fig)
    arquivos.append(arquivo)

    return arquivos


def gerar_graficos(payload: dict[str, object], pasta_saida: Path) -> list[Path]:
    pasta_graficos = pasta_saida / CHARTS_DIRNAME
    pasta_graficos.mkdir(parents=True, exist_ok=True)

    arquivos: list[Path] = []
    for chave, serie in payload["series"].items():
        arquivo = salvar_grafico_serie(str(chave), dict(serie), pasta_graficos)
        if arquivo is not None:
            arquivos.append(arquivo)

    return arquivos


def gerar_graficos_correlacoes(payload: dict[str, object], pasta_saida: Path) -> list[Path]:
    pasta_graficos = pasta_saida / CORRELATION_CHARTS_DIRNAME
    pasta_graficos.mkdir(parents=True, exist_ok=True)

    arquivos: list[Path] = []
    for correlacao in payload.get("correlacoes", []):
        arquivos.extend(salvar_graficos_correlacao(dict(correlacao), pasta_graficos))

    return arquivos


def gerar_graficos_comovimento(payload: dict[str, object], pasta_saida: Path) -> list[Path]:
    pasta_graficos = pasta_saida / COMOVEMENT_CHARTS_DIRNAME
    pasta_graficos.mkdir(parents=True, exist_ok=True)
    return salvar_graficos_comovimento(dict(payload.get("comovimento", {})), pasta_graficos)


def gerar_payload(arquivo_entrada: Path, arquivo_saida: Path) -> dict[str, object]:
    payload: dict[str, object] = {
        "metadata": {
            "arquivo_entrada": str(arquivo_entrada),
            "arquivo_saida": str(arquivo_saida),
        },
        "series": {
            "bolsa_familia": {
                "tema": "Bolsa Família",
                "aba": "visdata3-download-01-07-2026 17",
                "intervalo": "A1:C136",
                "variavel": "Pessoas beneficiárias no PBF",
                "dados": extrair_bolsa_familia(arquivo_entrada),
            }
        },
    }

    for serie in SERIES_TABELAS:
        payload["series"][serie["chave"]] = {
            "tema": serie["tema"],
            "aba": serie["aba"],
            "intervalo": "B4:BF4 e B6:BF6",
            "variavel": serie["variavel"],
            "dados": extrair_serie_tabela(arquivo_entrada, serie["aba"], serie["chave"]),
        }

    payload["series"]["pessoas_beneficiarias_pbf_media_tri"] = {
        "tema": "Bolsa Família — média trimestral",
        "aba": "visdata3-download-01-07-2026 17",
        "intervalo": "A1:C136 agregado por trimestre",
        "variavel": "Pessoas beneficiárias no PBF, média trimestral",
        "dados": agregar_bolsa_familia_trimestral(payload).to_dict(orient="records"),
    }
    payload["correlacoes"] = calcular_correlacoes(payload)
    payload["comovimento"] = calcular_comovimento(payload)

    return sanitizar_json(payload)


def extrair_series_para_json(
    arquivo_entrada: Path = DEFAULT_INPUT,
    pasta_saida: Path = DEFAULT_OUTPUT_DIR,
) -> tuple[Path, list[Path]]:
    if not arquivo_entrada.exists():
        raise FileNotFoundError(f"Arquivo de entrada nao encontrado: {arquivo_entrada}")

    pasta_saida.mkdir(parents=True, exist_ok=True)
    arquivo_saida = pasta_saida / OUTPUT_FILENAME
    payload = gerar_payload(arquivo_entrada, arquivo_saida)
    arquivo_saida.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    arquivos_graficos = gerar_graficos(payload, pasta_saida)
    arquivos_graficos.extend(gerar_graficos_correlacoes(payload, pasta_saida))
    arquivos_graficos.extend(gerar_graficos_comovimento(payload, pasta_saida))
    return arquivo_saida, arquivos_graficos


def main() -> None:
    args = parse_args()
    arquivo_saida, arquivos_graficos = extrair_series_para_json(
        arquivo_entrada=args.arquivo.resolve(),
        pasta_saida=args.saida.resolve(),
    )
    print("JSON extraido com sucesso.")
    print(f"Arquivo gerado: {arquivo_saida}")
    print(f"Pasta de graficos: {arquivo_saida.parent / CHARTS_DIRNAME}")
    print(f"Imagens geradas: {len(arquivos_graficos)}")


if __name__ == "__main__":
    main()
