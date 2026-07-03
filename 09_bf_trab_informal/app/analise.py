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
import statsmodels.api as sm


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = BASE_DIR / "data" / "input" / "DadosEconometria.xlsx"
DEFAULT_OUTPUT_DIR = BASE_DIR / "data" / "output"
OUTPUT_FILENAME = "series_extraidas.json"
CHARTS_DIRNAME = "graficos_series"
CORRELATION_CHARTS_DIRNAME = "graficos_correlacoes"
COMOVEMENT_CHARTS_DIRNAME = "graficos_comovimento"
ECONOMETRICS_CHARTS_DIRNAME = "graficos_econometria"
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


def agregar_bolsa_familia_trimestral_completude(payload: dict[str, object]) -> pd.DataFrame:
    serie_bf = payload["series"]["bolsa_familia"]
    dados, _, _ = montar_dataframe_serie("bolsa_familia", serie_bf)
    trimestral = (
        dados.assign(trimestre=dados["periodo"].dt.to_period("Q"))
        .groupby("trimestre", as_index=False)
        .agg(
            pessoas_beneficiarias_pbf_media_tri=("valor", "mean"),
            meses_observados_bf=("valor", "count"),
        )
    )
    trimestral["trimestre"] = trimestral["trimestre"].astype(str).str.replace("Q", "T", regex=False)
    trimestral["trimestre_completo_bf"] = trimestral["meses_observados_bf"] == 3
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


def construir_base_econometrica(payload: dict[str, object]) -> pd.DataFrame:
    bf = agregar_bolsa_familia_trimestral_completude(payload)
    informais = agregar_serie_por_trimestre_unico("pessoas_informais_mil", payload["series"]["pessoas_informais_mil"])
    ocupados = agregar_serie_por_trimestre_unico("pessoas_ocupadas_mil", payload["series"]["pessoas_ocupadas_mil"])
    desocupacao = agregar_serie_por_trimestre_unico("taxa_desocupacao", payload["series"]["taxa_desocupacao"])

    base = (
        bf.merge(informais, on="trimestre", how="inner")
        .merge(ocupados, on="trimestre", how="inner")
        .merge(desocupacao, on="trimestre", how="inner")
        .dropna(
            subset=[
                "pessoas_beneficiarias_pbf_media_tri",
                "pessoas_informais_mil",
                "pessoas_ocupadas_mil",
                "taxa_desocupacao",
            ]
        )
        .sort_values("trimestre")
        .reset_index(drop=True)
    )

    base = base.loc[base["trimestre_completo_bf"]].copy()
    base["trimestre_ordinal"] = base["trimestre"].apply(trimestre_para_ordinal)
    base["periodo"] = base["trimestre"].apply(trimestre_para_timestamp)
    base["ano"] = base["trimestre"].str[:4].astype(int)
    base["trimestre_num"] = base["trimestre"].str[-1].astype(int)
    base["pos_2023"] = (base["trimestre_ordinal"] >= trimestre_para_ordinal("2023T2")).astype(int)
    base["tendencia"] = np.arange(1, len(base) + 1)

    for trimestre_num in (2, 3, 4):
        base[f"d_trimestre_{trimestre_num}"] = (base["trimestre_num"] == trimestre_num).astype(int)

    base["ln_informal"] = np.log(base["pessoas_informais_mil"])
    base["ln_bf"] = np.log(base["pessoas_beneficiarias_pbf_media_tri"])
    base["ln_ocupados"] = np.log(base["pessoas_ocupadas_mil"])

    base["d_ln_informal"] = base["ln_informal"].diff()
    base["d_ln_bf"] = base["ln_bf"].diff()
    base["d_ln_bf_lag1"] = base["d_ln_bf"].shift(1)
    base["d_ln_ocupados"] = base["ln_ocupados"].diff()
    base["d_taxa_desocupacao"] = base["taxa_desocupacao"].diff()
    base["gap_trimestres"] = base["trimestre_ordinal"].diff()

    # Only keep quarter-to-quarter changes when both endpoints are consecutive and the lag also comes from a consecutive step.
    invalid_current = base["gap_trimestres"] != 1
    base.loc[invalid_current, ["d_ln_informal", "d_ln_bf", "d_ln_ocupados", "d_taxa_desocupacao"]] = np.nan
    base["gap_trimestres_lag1"] = base["gap_trimestres"].shift(1)
    invalid_lag = (base["gap_trimestres"] != 1) | (base["gap_trimestres_lag1"] != 1)
    base.loc[invalid_lag, "d_ln_bf_lag1"] = np.nan

    return base


def resumir_resultado_modelo(
    nome_modelo: str,
    resultado: sm.regression.linear_model.RegressionResultsWrapper,
    dados_modelo: pd.DataFrame,
    variavel_dependente: str,
) -> dict[str, object]:
    parametros = []
    for nome in resultado.params.index:
        parametros.append(
            {
                "variavel": nome,
                "coeficiente": float(resultado.params[nome]),
                "erro_padrao": float(resultado.bse[nome]),
                "estatistica_t": float(resultado.tvalues[nome]),
                "p_valor": float(resultado.pvalues[nome]),
            }
        )

    return {
        "nome_modelo": nome_modelo,
        "variavel_dependente": variavel_dependente,
        "n_observacoes": int(resultado.nobs),
        "r2": float(resultado.rsquared),
        "r2_ajustado": float(resultado.rsquared_adj),
        "estatistica_f": float(resultado.fvalue) if resultado.fvalue is not None else None,
        "p_valor_f": float(resultado.f_pvalue) if resultado.f_pvalue is not None else None,
        "parametros": parametros,
        "valores_ajustados": [
            {
                "trimestre": linha["trimestre"],
                "real": float(linha[variavel_dependente]),
                "ajustado": float(resultado.fittedvalues.loc[idx]),
                "residuo": float(resultado.resid.loc[idx]),
            }
            for idx, linha in dados_modelo.iterrows()
        ],
    }


def rodar_econometria(payload: dict[str, object]) -> dict[str, object]:
    base = construir_base_econometrica(payload)

    colunas_modelo_simples_nivel = ["ln_bf"]
    dados_simples_nivel = base.dropna(subset=["ln_informal", *colunas_modelo_simples_nivel]).copy()
    x_simples_nivel = sm.add_constant(dados_simples_nivel[colunas_modelo_simples_nivel])
    y_simples_nivel = dados_simples_nivel["ln_informal"]
    modelo_simples_nivel = sm.OLS(y_simples_nivel, x_simples_nivel).fit(
        cov_type="HAC", cov_kwds={"maxlags": 1}
    )
    teste_f_simples_nivel = modelo_simples_nivel.f_test("ln_bf = 0")

    colunas_modelo_principal = [
        "d_ln_bf",
        "d_ln_bf_lag1",
        "d_ln_ocupados",
        "d_taxa_desocupacao",
        "pos_2023",
        "d_trimestre_2",
        "d_trimestre_3",
        "d_trimestre_4",
    ]
    dados_principal = base.dropna(subset=["d_ln_informal", *colunas_modelo_principal]).copy()
    x_principal = sm.add_constant(dados_principal[colunas_modelo_principal])
    y_principal = dados_principal["d_ln_informal"]
    modelo_principal = sm.OLS(y_principal, x_principal).fit(cov_type="HAC", cov_kwds={"maxlags": 1})
    teste_f = modelo_principal.f_test("d_ln_bf = 0, d_ln_bf_lag1 = 0")

    colunas_modelo_principal_sem_dummies = [
        "d_ln_bf",
        "d_ln_bf_lag1",
        "d_ln_ocupados",
        "d_taxa_desocupacao",
        "pos_2023",
    ]
    dados_principal_sem_dummies = base.dropna(
        subset=["d_ln_informal", *colunas_modelo_principal_sem_dummies]
    ).copy()
    x_principal_sem_dummies = sm.add_constant(dados_principal_sem_dummies[colunas_modelo_principal_sem_dummies])
    y_principal_sem_dummies = dados_principal_sem_dummies["d_ln_informal"]
    modelo_principal_sem_dummies = sm.OLS(y_principal_sem_dummies, x_principal_sem_dummies).fit(
        cov_type="HAC", cov_kwds={"maxlags": 1}
    )
    teste_f_sem_dummies = modelo_principal_sem_dummies.f_test("d_ln_bf = 0, d_ln_bf_lag1 = 0")

    colunas_modelo_nivel = [
        "ln_bf",
        "ln_ocupados",
        "taxa_desocupacao",
        "tendencia",
        "pos_2023",
        "d_trimestre_2",
        "d_trimestre_3",
        "d_trimestre_4",
    ]
    dados_nivel = base.dropna(subset=["ln_informal", *colunas_modelo_nivel]).copy()
    x_nivel = sm.add_constant(dados_nivel[colunas_modelo_nivel])
    y_nivel = dados_nivel["ln_informal"]
    modelo_nivel = sm.OLS(y_nivel, x_nivel).fit(cov_type="HAC", cov_kwds={"maxlags": 1})
    teste_f_nivel = modelo_nivel.f_test("ln_bf = 0")

    colunas_modelo_nivel_sem_dummies = [
        "ln_bf",
        "ln_ocupados",
        "taxa_desocupacao",
        "tendencia",
        "pos_2023",
    ]
    dados_nivel_sem_dummies = base.dropna(
        subset=["ln_informal", *colunas_modelo_nivel_sem_dummies]
    ).copy()
    x_nivel_sem_dummies = sm.add_constant(dados_nivel_sem_dummies[colunas_modelo_nivel_sem_dummies])
    y_nivel_sem_dummies = dados_nivel_sem_dummies["ln_informal"]
    modelo_nivel_sem_dummies = sm.OLS(y_nivel_sem_dummies, x_nivel_sem_dummies).fit(
        cov_type="HAC", cov_kwds={"maxlags": 1}
    )
    teste_f_nivel_sem_dummies = modelo_nivel_sem_dummies.f_test("ln_bf = 0")

    return {
        "biblioteca": "statsmodels",
        "observacao_metodologica": (
            "Modelos estimados via OLS com erros-padrao HAC (Newey-West, maxlags=1) "
            "para reduzir sensibilidade a autocorrelacao e heterocedasticidade."
        ),
        "base_trimestral": base.to_dict(orient="records"),
        "modelo_simples_nivel_logaritmico": {
            **resumir_resultado_modelo(
                "modelo_simples_nivel_logaritmico",
                modelo_simples_nivel,
                dados_simples_nivel,
                "ln_informal",
            ),
            "formula_descricao": "ln_informal ~ ln_bf",
            "teste_f_beta_bf": {
                "hipotese_nula": "ln_bf = 0",
                "estatistica_f": float(teste_f_simples_nivel.fvalue),
                "p_valor": float(teste_f_simples_nivel.pvalue),
            },
        },
        "modelo_principal_variacoes_logaritmicas": {
            **resumir_resultado_modelo(
                "modelo_principal_variacoes_logaritmicas",
                modelo_principal,
                dados_principal,
                "d_ln_informal",
            ),
            "formula_descricao": (
                "d_ln_informal ~ d_ln_bf + d_ln_bf_lag1 + d_ln_ocupados + "
                "d_taxa_desocupacao + pos_2023 + d_trimestre_2 + d_trimestre_3 + d_trimestre_4"
            ),
            "teste_f_beta_bf_contemporaneo_e_defasado": {
                "hipotese_nula": "d_ln_bf = 0 e d_ln_bf_lag1 = 0",
                "estatistica_f": float(teste_f.fvalue),
                "p_valor": float(teste_f.pvalue),
            },
        },
        "modelo_principal_variacoes_logaritmicas_sem_dummies": {
            **resumir_resultado_modelo(
                "modelo_principal_variacoes_logaritmicas_sem_dummies",
                modelo_principal_sem_dummies,
                dados_principal_sem_dummies,
                "d_ln_informal",
            ),
            "formula_descricao": (
                "d_ln_informal ~ d_ln_bf + d_ln_bf_lag1 + d_ln_ocupados + "
                "d_taxa_desocupacao + pos_2023"
            ),
            "teste_f_beta_bf_contemporaneo_e_defasado": {
                "hipotese_nula": "d_ln_bf = 0 e d_ln_bf_lag1 = 0",
                "estatistica_f": float(teste_f_sem_dummies.fvalue),
                "p_valor": float(teste_f_sem_dummies.pvalue),
            },
        },
        "modelo_secundario_nivel_logaritmico": {
            **resumir_resultado_modelo(
                "modelo_secundario_nivel_logaritmico",
                modelo_nivel,
                dados_nivel,
                "ln_informal",
            ),
            "formula_descricao": (
                "ln_informal ~ ln_bf + ln_ocupados + taxa_desocupacao + tendencia + "
                "pos_2023 + d_trimestre_2 + d_trimestre_3 + d_trimestre_4"
            ),
            "teste_f_beta_bf": {
                "hipotese_nula": "ln_bf = 0",
                "estatistica_f": float(teste_f_nivel.fvalue),
                "p_valor": float(teste_f_nivel.pvalue),
            },
        },
        "modelo_secundario_nivel_logaritmico_sem_dummies": {
            **resumir_resultado_modelo(
                "modelo_secundario_nivel_logaritmico_sem_dummies",
                modelo_nivel_sem_dummies,
                dados_nivel_sem_dummies,
                "ln_informal",
            ),
            "formula_descricao": (
                "ln_informal ~ ln_bf + ln_ocupados + taxa_desocupacao + tendencia + pos_2023"
            ),
            "teste_f_beta_bf": {
                "hipotese_nula": "ln_bf = 0",
                "estatistica_f": float(teste_f_nivel_sem_dummies.fvalue),
                "p_valor": float(teste_f_nivel_sem_dummies.pvalue),
            },
        },
    }


def obter_metadados_modelos_econometricos() -> list[tuple[str, str, tuple[str, ...], str | None]]:
    return [
        ("modelo_simples_nivel_logaritmico", "Modelo Simples em Nível", ("ln_bf",), "teste_f_beta_bf"),
        (
            "modelo_principal_variacoes_logaritmicas",
            "Modelo Principal",
            ("d_ln_bf", "d_ln_bf_lag1"),
            "teste_f_beta_bf_contemporaneo_e_defasado",
        ),
        (
            "modelo_principal_variacoes_logaritmicas_sem_dummies",
            "Modelo Principal Sem Dummies",
            ("d_ln_bf", "d_ln_bf_lag1"),
            "teste_f_beta_bf_contemporaneo_e_defasado",
        ),
        ("modelo_secundario_nivel_logaritmico", "Modelo Secundário", ("ln_bf",), "teste_f_beta_bf"),
        (
            "modelo_secundario_nivel_logaritmico_sem_dummies",
            "Modelo Secundário Sem Dummies",
            ("ln_bf",),
            "teste_f_beta_bf",
        ),
    ]


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


def adicionar_cabecalho_econometria(fig: plt.Figure, titulo: str, subtitulo: str, resumo: str) -> None:
    fig.suptitle(titulo, x=0.05, y=0.97, ha="left", va="top", fontsize=22, fontweight="bold")
    fig.text(0.05, 0.935, subtitulo, ha="left", va="top", fontsize=13, color="#243b53")
    fig.text(
        0.05,
        0.895,
        resumo,
        ha="left",
        va="top",
        fontsize=11,
        color="#334e68",
        bbox={"boxstyle": "round,pad=0.5", "facecolor": "#eef4f7", "edgecolor": "#d9e2ec"},
    )


def formatar_p_valor(p_valor: float | None) -> str:
    if p_valor is None:
        return "n/d"
    if p_valor < 0.0001:
        return "< 0,0001"
    return f"{p_valor:.4f}".replace(".", ",")


def formatar_numero(valor: float | None, casas: int = 4) -> str:
    if valor is None:
        return "n/d"
    return f"{valor:.{casas}f}".replace(".", ",")


def contar_linhas_texto(valor: object) -> int:
    texto = str(valor) if valor is not None else ""
    return max(1, texto.count("\n") + 1)


def formatar_rotulo_teste_f(hipotese_nula: object) -> str:
    if hipotese_nula is None:
        return "n/d"
    return str(hipotese_nula).replace(" e ", "; ")


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


def salvar_graficos_testes_econometricos(econometria: dict[str, object], pasta_graficos: Path) -> list[Path]:
    arquivos: list[Path] = []
    modelos_alvo = [
        "modelo_principal_variacoes_logaritmicas",
        "modelo_principal_variacoes_logaritmicas_sem_dummies",
    ]

    for chave_modelo in modelos_alvo:
        modelo = econometria.get(chave_modelo, {})
        if not modelo:
            continue

        parametros = {
            item["variavel"]: item
            for item in modelo.get("parametros", [])
            if item["variavel"] in {"d_ln_bf", "d_ln_bf_lag1"}
        }
        teste_f = modelo.get("teste_f_beta_bf_contemporaneo_e_defasado")
        titulo_base = chave_modelo.replace("_", " ").title()
        slug = slugify(chave_modelo)

        fig, ax = plt.subplots(figsize=(14, 8), dpi=180)
        fig.patch.set_facecolor("white")
        ax.axis("off")
        adicionar_cabecalho_econometria(
            fig,
            f"Teste t: {titulo_base}",
            "Significância individual dos coeficientes do Bolsa Família",
            (
                "Hipóteses nulas:\n"
                "H0: β1 = 0 para d_ln_bf\n"
                "H0: β2 = 0 para d_ln_bf_lag1"
            ),
        )

        linhas = []
        for nome, rotulo in (("d_ln_bf", "β1: efeito contemporâneo"), ("d_ln_bf_lag1", "β2: efeito defasado")):
            p = parametros.get(nome, {})
            decisao = "Rejeita H0 a 5%" if p.get("p_valor") is not None and p["p_valor"] < 0.05 else "Não rejeita H0 a 5%"
            linhas.append(
                f"{rotulo}\n"
                f"coef = {formatar_numero(p.get('coeficiente'))} | se = {formatar_numero(p.get('erro_padrao'))}\n"
                f"t = {formatar_numero(p.get('estatistica_t'))} | p = {formatar_p_valor(p.get('p_valor'))}\n"
                f"decisão: {decisao}"
            )

        ax.text(
            0.03,
            0.72,
            "\n\n".join(linhas),
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=14,
            color="#102a43",
            bbox={"boxstyle": "round,pad=0.7", "facecolor": "#fbfbfc", "edgecolor": "#d9e2ec"},
        )
        fig.subplots_adjust(top=0.78, left=0.04, right=0.98, bottom=0.08)
        arquivo = pasta_graficos / f"{slug}_teste_t.png"
        fig.savefig(arquivo, bbox_inches="tight")
        plt.close(fig)
        arquivos.append(arquivo)

        if teste_f:
            fig, ax = plt.subplots(figsize=(14, 8), dpi=180)
            fig.patch.set_facecolor("white")
            ax.axis("off")
            adicionar_cabecalho_econometria(
                fig,
                f"Teste F: {titulo_base}",
                "Significância conjunta dos coeficientes do Bolsa Família",
                (
                    "Hipótese nula conjunta:\n"
                    "H0: β1 = 0 e β2 = 0\n"
                    "com q = 2 restrições"
                ),
            )
            decisao = (
                "Rejeita H0 a 5%"
                if teste_f.get("p_valor") is not None and teste_f["p_valor"] < 0.05
                else "Não rejeita H0 a 5%"
            )
            texto_f = (
                f"Estatística F = {formatar_numero(teste_f.get('estatistica_f'))}\n"
                f"p-valor = {formatar_p_valor(teste_f.get('p_valor'))}\n"
                f"decisão: {decisao}\n\n"
                "Interpretação:\n"
                "o teste verifica se as variações contemporânea e defasada do Bolsa Família\n"
                "ajudam conjuntamente a explicar a variável dependente."
            )
            ax.text(
                0.03,
                0.72,
                texto_f,
                transform=ax.transAxes,
                ha="left",
                va="top",
                fontsize=14,
                color="#102a43",
                bbox={"boxstyle": "round,pad=0.7", "facecolor": "#fbfbfc", "edgecolor": "#d9e2ec"},
            )
            fig.subplots_adjust(top=0.78, left=0.04, right=0.98, bottom=0.08)
            arquivo = pasta_graficos / f"{slug}_teste_f.png"
            fig.savefig(arquivo, bbox_inches="tight")
            plt.close(fig)
            arquivos.append(arquivo)

    return arquivos


def salvar_grafico_resumo_testes_bf(econometria: dict[str, object], pasta_graficos: Path) -> Path | None:
    linhas_tabela: list[list[str]] = []

    for chave_modelo, rotulo_modelo, variaveis_bf, chave_teste_f in obter_metadados_modelos_econometricos():
        modelo = econometria.get(chave_modelo, {})
        if not modelo:
            continue

        parametros = {item["variavel"]: item for item in modelo.get("parametros", [])}
        resumo_t = []
        for variavel_bf in variaveis_bf:
            parametro = parametros.get(variavel_bf)
            if not parametro:
                continue
            resumo_t.append(
                f"{variavel_bf}: t={formatar_numero(parametro.get('estatistica_t'))} | "
                f"p={formatar_p_valor(parametro.get('p_valor'))}"
            )

        teste_f = modelo.get(chave_teste_f) if chave_teste_f else None
        if teste_f:
            resumo_f = (
                f"{formatar_rotulo_teste_f(teste_f.get('hipotese_nula', 'n/d'))}\n"
                f"F={formatar_numero(teste_f.get('estatistica_f'))} | "
                f"p={formatar_p_valor(teste_f.get('p_valor'))}"
            )
        else:
            resumo_f = "n/d"

        linhas_tabela.append(
            [
                rotulo_modelo,
                modelo.get("variavel_dependente", "n/d"),
                "\n".join(resumo_t) if resumo_t else "n/d",
                resumo_f,
            ]
        )

    if not linhas_tabela:
        return None

    linhas_por_registro = [max(contar_linhas_texto(celula) for celula in linha) for linha in linhas_tabela]
    altura = max(8.4, 3.0 + sum(0.40 + linhas * 0.26 for linhas in linhas_por_registro))
    fig, ax = plt.subplots(figsize=(18, altura), dpi=180)
    fig.patch.set_facecolor("white")
    ax.axis("off")
    adicionar_cabecalho_econometria(
        fig,
        "Resumo dos Testes: Bolsa Família",
        "Tabela consolidada de testes t e F para os coeficientes do Bolsa Família em todos os modelos",
        (
            f"Biblioteca: {econometria.get('biblioteca', 'n/d')}\n"
            "Teste t: significância individual dos coeficientes ligados ao Bolsa Família\n"
            "Teste F: significância da hipótese nula indicada em cada modelo"
        ),
    )

    tabela = ax.table(
        cellText=linhas_tabela,
        colLabels=["Modelo", "Dependente", "Teste t", "Teste F"],
        colWidths=[0.23, 0.16, 0.305, 0.305],
        cellLoc="left",
        colLoc="left",
        bbox=[0.035, 0.045, 0.93, 0.80],
    )
    tabela.auto_set_font_size(False)
    tabela.set_fontsize(10)
    tabela.scale(1, 1.10)

    for (linha, coluna), celula in tabela.get_celld().items():
        celula.set_edgecolor("#d9e2ec")
        celula.PAD = 0.08
        if linha == 0:
            celula.set_facecolor("#dceefb")
            celula.set_text_props(weight="bold", color="#102a43")
        else:
            celula.set_facecolor("#fbfbfc" if linha % 2 else "#f4f7fb")
            celula.set_text_props(color="#243b53")
        celula.get_text().set_va("center")
        celula.get_text().set_ha("left")
        celula.get_text().set_wrap(False)

    altura_cabecalho = 0.085
    for coluna in range(4):
        tabela[(0, coluna)].set_height(altura_cabecalho)

    for indice_linha, linhas_texto in enumerate(linhas_por_registro, start=1):
        altura_linha = 0.075 + max(0, linhas_texto - 1) * 0.030
        for coluna in range(4):
            tabela[(indice_linha, coluna)].set_height(altura_linha)

    fig.subplots_adjust(top=0.92, left=0.03, right=0.97, bottom=0.03)
    arquivo = pasta_graficos / "resumo_testes_bolsa_familia_modelos.png"
    fig.savefig(arquivo, bbox_inches="tight", pad_inches=0.18)
    plt.close(fig)
    return arquivo


def salvar_graficos_econometria(econometria: dict[str, object], pasta_graficos: Path) -> list[Path]:
    arquivos: list[Path] = []

    for chave_modelo, rotulo_modelo, _, _ in obter_metadados_modelos_econometricos():
        modelo = econometria.get(chave_modelo, {})
        dados = pd.DataFrame(modelo.get("valores_ajustados", []))
        if dados.empty:
            continue

        dados["periodo"] = dados["trimestre"].apply(trimestre_para_timestamp)
        resumo = (
            f"Biblioteca: {econometria['biblioteca']}\n"
            f"n: {modelo['n_observacoes']}\n"
            f"R²: {modelo['r2']:.4f}\n"
            f"R² ajustado: {modelo['r2_ajustado']:.4f}"
        )

        fig, ax = plt.subplots(figsize=(18, 10), dpi=180)
        fig.patch.set_facecolor("white")
        adicionar_cabecalho_econometria(
            fig,
            f"Econometria: {rotulo_modelo}",
            modelo["formula_descricao"],
            resumo,
        )
        ax.plot(dados["periodo"], dados["real"], color="#0b6e4f", linewidth=2.5, label="Real")
        ax.plot(dados["periodo"], dados["ajustado"], color="#d64550", linewidth=2.5, linestyle="--", label="Ajustado")
        ax.set_title("Série observada versus ajustada", loc="left", fontsize=14, fontweight="bold")
        ax.set_xlabel("Período", fontsize=11, color="#102a43")
        ax.set_ylabel(modelo["variavel_dependente"], fontsize=11, color="#102a43")
        ax.legend(frameon=False, fontsize=11, loc="upper right")
        estilizar_eixos(ax, usar_datas=True)
        fig.subplots_adjust(top=0.74, left=0.08, right=0.97, bottom=0.12)
        arquivo = pasta_graficos / f"{slugify(chave_modelo)}_ajuste.png"
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


def gerar_graficos_econometria(payload: dict[str, object], pasta_saida: Path) -> list[Path]:
    pasta_graficos = pasta_saida / ECONOMETRICS_CHARTS_DIRNAME
    pasta_graficos.mkdir(parents=True, exist_ok=True)
    arquivos = salvar_graficos_econometria(dict(payload.get("econometria", {})), pasta_graficos)
    arquivos.extend(salvar_graficos_testes_econometricos(dict(payload.get("econometria", {})), pasta_graficos))
    arquivo_resumo = salvar_grafico_resumo_testes_bf(dict(payload.get("econometria", {})), pasta_graficos)
    if arquivo_resumo is not None:
        arquivos.append(arquivo_resumo)
    return arquivos


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
    payload["econometria"] = rodar_econometria(payload)

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
    arquivos_graficos.extend(gerar_graficos_econometria(payload, pasta_saida))
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
