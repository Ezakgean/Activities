from __future__ import annotations

import argparse
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib import dates as mdates
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = BASE_DIR / "data" / "input"
DEFAULT_OUTPUT_DIR = BASE_DIR / "data" / "output"
DEFAULT_IPCA_FILE = DEFAULT_INPUT_DIR / "ipca.csv"
DEFAULT_PIB_FILE = DEFAULT_INPUT_DIR / "pib.csv"
OUTPUT_JSON = "serie_divida_publica_consolidada.json"
OUTPUT_CSV = "serie_divida_publica_consolidada.csv"
OUTPUT_SUMMARY = "resumo_divida_publica.txt"
OUTPUT_CHART = "dashboard_divida_publica.png"

MONTH_NAMES = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Marco",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro",
}


@dataclass
class PipelineResult:
    dataframe: pd.DataFrame
    output_files: dict[str, Path]
    summary_text: str
    base_label: str | None
    records: list[dict[str, Any]]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Consolida arquivos JSON do RMD em uma serie historica nominal e real."
    )
    parser.add_argument("--entrada", type=Path, default=DEFAULT_INPUT_DIR, help="Pasta com arquivos JSON do RMD.")
    parser.add_argument("--saida", type=Path, default=DEFAULT_OUTPUT_DIR, help="Pasta para artefatos gerados.")
    parser.add_argument(
        "--ipca",
        type=Path,
        default=DEFAULT_IPCA_FILE,
        help="Arquivo CSV ou JSON com colunas periodo e ipca_indice.",
    )
    parser.add_argument(
        "--pib",
        type=Path,
        default=DEFAULT_PIB_FILE,
        help="Arquivo CSV ou JSON com colunas periodo e pib_nominal_brl_bilhoes.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _get_nested(payload: dict[str, Any], *keys: str) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _normalize_month_name(text: str | None) -> str:
    if not text:
        return ""
    cleaned = (
        str(text)
        .strip()
        .replace("ç", "c")
        .replace("Ç", "C")
        .replace("ã", "a")
        .replace("Ã", "A")
        .replace("á", "a")
        .replace("Á", "A")
        .replace("é", "e")
        .replace("É", "E")
        .replace("ê", "e")
        .replace("Ê", "E")
        .replace("í", "i")
        .replace("Í", "I")
        .replace("ó", "o")
        .replace("Ó", "O")
        .replace("ô", "o")
        .replace("Ô", "O")
        .replace("ú", "u")
        .replace("Ú", "U")
    )
    return cleaned


def _find_month_entry(series: list[dict[str, Any]], month_number: int, month_name: str | None) -> dict[str, Any] | None:
    target_names = {
        _normalize_month_name(month_name),
        _normalize_month_name(MONTH_NAMES.get(month_number)),
    }
    for entry in series:
        current_name = _normalize_month_name(entry.get("mes"))
        if current_name in target_names:
            return entry
    if 1 <= month_number <= len(series):
        return series[month_number - 1]
    return series[-1] if series else None


def _extract_percent_pair(entry: dict[str, Any], key: str) -> float | None:
    value = entry.get(key)
    if isinstance(value, list) and len(value) >= 2:
        return _to_float(value[1])
    return None


def _extract_volume_pair(entry: dict[str, Any], key: str = "total") -> float | None:
    value = entry.get(key)
    if isinstance(value, list) and value:
        return _to_float(value[0])
    return None


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return None
        return float(value)
    text = str(value).strip()
    if text in {"", "-", "...", "null", "None"}:
        return None
    text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def extract_record(payload: dict[str, Any], source_path: Path) -> dict[str, Any]:
    period_info = payload.get("periodo_referencia", {})
    year = int(period_info["ano"])
    month = int(period_info["mes"])
    period = f"{year:04d}-{month:02d}"
    month_name = period_info.get("mes_nome")
    summary_key = next((key for key in payload if key.startswith("resumo_")), None)
    summary = payload.get(summary_key or "", {})

    composition_series = _get_nested(payload, "dpfi_composicao_por_rentabilidade", "serie_historica") or []
    composition_entry = _find_month_entry(composition_series, month, month_name)

    secondary_series = _get_nested(payload, "mercado_secundario_volume_negociado_por_titulo", "serie_historica") or []
    secondary_entry = _find_month_entry(secondary_series, month, month_name)

    record = {
        "periodo": period,
        "arquivo_origem": source_path.name,
        "fonte_pagina": _get_nested(payload, "publicacao", "fonte_pagina"),
        "fonte_pdf": _get_nested(payload, "publicacao", "fonte_pdf"),
        "publicacao_data": _get_nested(payload, "publicacao", "data_publicacao"),
        "estoque_nominal_brl_bilhoes": _to_float(summary.get("dpfi_estoque_poder_publico_brl_bilhoes")),
        "estoque_nominal_mes_anterior_brl_bilhoes": _to_float(summary.get("dpfi_estoque_outubro_2000_brl_bilhoes")),
        "prazo_medio_meses": _to_float(summary.get("prazo_medio_estoque_meses")),
        "vencimento_12_meses_pct": _to_float(summary.get("titulos_vencendo_em_12_meses_percentual_total")),
        "vencimento_12_meses_brl_bilhoes": _to_float(summary.get("titulos_vencendo_em_12_meses_brl_bilhoes")),
        "emissoes_nominais_brl_milhoes": _to_float(_get_nested(summary, "ofertas_publicas", "emissoes_brl_milhoes")),
        "resgates_nominais_brl_milhoes": _to_float(_get_nested(summary, "ofertas_publicas", "resgates_brl_milhoes")),
        "impacto_liquidez_nominal_brl_milhoes": _to_float(
            _get_nested(summary, "ofertas_publicas", "impacto_liquidez_brl_milhoes")
        ),
        "emissoes_diretas_nominais_brl_milhoes": _to_float(summary.get("emissoes_diretas_brl_milhoes")),
        "mercado_secundario_volume_diario_medio_brl_bilhoes": _to_float(
            summary.get("mercado_secundario_volume_diario_medio_brl_bilhoes")
        )
        or _extract_volume_pair(secondary_entry or {}),
        "prefixada_pct": _extract_percent_pair(composition_entry or {}, "prefixada"),
        "selic_pct": _extract_percent_pair(composition_entry or {}, "selic"),
        "indice_precos_pct": _extract_percent_pair(composition_entry or {}, "indice_precos"),
        "cambio_pct": _extract_percent_pair(composition_entry or {}, "cambio"),
        "tr_pct": _extract_percent_pair(composition_entry or {}, "TR"),
        "outros_pct": _extract_percent_pair(composition_entry or {}, "outros"),
    }
    for key, value in (summary.get("composicao_percentual") or {}).items():
        record[f"{key}_pct"] = _to_float(value)
    flows = summary.get("fluxos_dpf") or {}
    for key in ("emissoes", "resgates"):
        if flows.get(f"{key}_brl_milhoes") is not None:
            record[f"{key}_nominais_brl_milhoes"] = _to_float(flows[f"{key}_brl_milhoes"])
    record["abrangencia_fluxos"] = "DPF" if flows else "ofertas_publicas"
    record.setdefault("taxa_flutuante_pct", None)
    return record


def discover_rmd_files(input_dir: Path) -> list[Path]:
    if not input_dir.exists():
        return []
    return sorted(path for path in input_dir.glob("rmd_divida_publica_????_??.json") if path.is_file())


def load_ipca_dataframe(path: Path) -> tuple[pd.DataFrame | None, str | None]:
    if not path.exists():
        return None, None
    if path.suffix.lower() == ".json":
        raw = load_json(path)
        rows = raw["dados"] if isinstance(raw, dict) and "dados" in raw else raw
        df = pd.DataFrame(rows)
    else:
        df = pd.read_csv(path)

    rename_map = {
        "mes": "periodo",
        "month": "periodo",
        "date": "periodo",
        "indice": "ipca_indice",
        "ipca": "ipca_indice",
        "valor": "ipca_indice",
    }
    df = df.rename(columns={key: value for key, value in rename_map.items() if key in df.columns})
    if "periodo" not in df.columns or "ipca_indice" not in df.columns:
        raise ValueError("Arquivo de IPCA precisa ter colunas 'periodo' e 'ipca_indice'.")

    ipca = df[["periodo", "ipca_indice"]].copy()
    ipca["periodo"] = ipca["periodo"].astype(str).str.slice(0, 7)
    ipca["ipca_indice"] = pd.to_numeric(ipca["ipca_indice"], errors="coerce")
    ipca = ipca.dropna(subset=["periodo", "ipca_indice"]).drop_duplicates("periodo").sort_values("periodo")
    if ipca.empty:
        return None, None

    base_period = str(ipca.iloc[-1]["periodo"])
    base_index = float(ipca.iloc[-1]["ipca_indice"])
    ipca["fator_deflator"] = base_index / ipca["ipca_indice"]
    ipca["ipca_variacao_mensal_pct"] = ipca["ipca_indice"].pct_change() * 100.0
    return ipca, base_period


def load_pib_dataframe(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    if path.suffix.lower() == ".json":
        raw = load_json(path)
        rows = raw["dados"] if isinstance(raw, dict) and "dados" in raw else raw
        df = pd.DataFrame(rows)
    else:
        df = pd.read_csv(path)

    rename_map = {
        "mes": "periodo",
        "month": "periodo",
        "date": "periodo",
        "pib": "pib_nominal_brl_bilhoes",
        "valor": "pib_nominal_brl_bilhoes",
    }
    df = df.rename(columns={key: value for key, value in rename_map.items() if key in df.columns})
    if "periodo" not in df.columns or "pib_nominal_brl_bilhoes" not in df.columns:
        raise ValueError("Arquivo de PIB precisa ter colunas 'periodo' e 'pib_nominal_brl_bilhoes'.")

    pib = df[["periodo", "pib_nominal_brl_bilhoes"]].copy()
    pib["periodo"] = pib["periodo"].astype(str).str.slice(0, 7)
    pib["pib_nominal_brl_bilhoes"] = pd.to_numeric(pib["pib_nominal_brl_bilhoes"], errors="coerce")
    pib = pib.dropna(subset=["periodo", "pib_nominal_brl_bilhoes"]).drop_duplicates("periodo").sort_values("periodo")
    return pib if not pib.empty else None


def build_dataframe(files: list[Path]) -> pd.DataFrame:
    records = [extract_record(load_json(path), path) for path in files]
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records).sort_values("periodo").reset_index(drop=True)
    df["variacao_nominal_percentual"] = df["estoque_nominal_brl_bilhoes"].pct_change() * 100.0
    return df


def apply_ipca(df: pd.DataFrame, ipca: pd.DataFrame | None) -> tuple[pd.DataFrame, str | None]:
    if ipca is None or df.empty:
        for column in [
            "ipca_indice",
            "ipca_variacao_mensal_pct",
            "fator_deflator",
            "estoque_real_brl_bilhoes",
            "emissoes_reais_brl_milhoes",
            "resgates_reais_brl_milhoes",
            "impacto_liquidez_real_brl_milhoes",
            "variacao_real_percentual",
        ]:
            df[column] = pd.NA
        return df, None

    merged = df.merge(ipca, on="periodo", how="left")
    merged["estoque_real_brl_bilhoes"] = merged["estoque_nominal_brl_bilhoes"] * merged["fator_deflator"]
    merged["emissoes_reais_brl_milhoes"] = merged["emissoes_nominais_brl_milhoes"] * merged["fator_deflator"]
    merged["resgates_reais_brl_milhoes"] = merged["resgates_nominais_brl_milhoes"] * merged["fator_deflator"]
    merged["impacto_liquidez_real_brl_milhoes"] = merged["impacto_liquidez_nominal_brl_milhoes"] * merged["fator_deflator"]
    merged["variacao_real_percentual"] = merged["estoque_real_brl_bilhoes"].pct_change() * 100.0
    base_period = str(ipca.iloc[-1]["periodo"])
    return merged, base_period


def apply_pib(df: pd.DataFrame, pib: pd.DataFrame | None) -> pd.DataFrame:
    if pib is None or df.empty:
        df["pib_nominal_brl_bilhoes"] = pd.NA
        df["divida_pib_pct"] = pd.NA
        return df
    merged = df.merge(pib, on="periodo", how="left")
    merged["divida_pib_pct"] = (merged["estoque_nominal_brl_bilhoes"] / merged["pib_nominal_brl_bilhoes"]) * 100.0
    return merged


def _round_record_values(record: dict[str, Any]) -> dict[str, Any]:
    rounded: dict[str, Any] = {}
    for key, value in record.items():
        if pd.isna(value):
            rounded[key] = None
        elif isinstance(value, float):
            rounded[key] = round(value, 4)
        else:
            rounded[key] = value
    return rounded


def dataframe_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in df.to_dict(orient="records"):
        records.append(_round_record_values(row))
    return records


def format_brl_bi(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "n/d"
    return f"R$ {value:,.2f} bi".replace(",", "X").replace(".", ",").replace("X", ".")


def format_brl_mi(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "n/d"
    return f"R$ {value:,.2f} mi".replace(",", "X").replace(".", ",").replace("X", ".")


def format_pct(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "n/d"
    return f"{value:.2f}%".replace(".", ",")


def create_summary(df: pd.DataFrame, base_period: str | None) -> str:
    if df.empty:
        return "Nenhum arquivo de RMD foi encontrado."

    latest = df.iloc[-1]
    earliest = df.iloc[0]
    lines = [
        "Serie consolidada da divida publica federal",
        f"Observacoes: {len(df)}",
        f"Periodo inicial: {earliest['periodo']}",
        f"Periodo final: {latest['periodo']}",
        f"Estoque nominal final: {format_brl_bi(latest.get('estoque_nominal_brl_bilhoes'))}",
        f"Variacao nominal mensal final: {format_pct(latest.get('variacao_nominal_percentual'))}",
        f"Prazo medio final: {latest.get('prazo_medio_meses', pd.NA)} meses",
        f"Vencendo em 12 meses: {format_pct(latest.get('vencimento_12_meses_pct'))}",
        f"Emissoes finais: {format_brl_mi(latest.get('emissoes_nominais_brl_milhoes'))}",
        f"Resgates finais: {format_brl_mi(latest.get('resgates_nominais_brl_milhoes'))}",
    ]
    if base_period and pd.notna(latest.get("estoque_real_brl_bilhoes")):
        lines.append(f"Estoque real final a precos de {base_period}: {format_brl_bi(latest.get('estoque_real_brl_bilhoes'))}")
        lines.append(f"Variacao real mensal final: {format_pct(latest.get('variacao_real_percentual'))}")
    else:
        lines.append("Serie real nao calculada: forneca data/input/ipca.csv com colunas periodo e ipca_indice.")
    if pd.notna(latest.get("divida_pib_pct")):
        lines.append(f"Relacao divida/PIB final: {format_pct(latest.get('divida_pib_pct'))}")
    else:
        lines.append("Relacao divida/PIB nao calculada: forneca data/input/pib.csv com colunas periodo e pib_nominal_brl_bilhoes.")
    return "\n".join(lines)


def save_outputs(df: pd.DataFrame, output_dir: Path, base_period: str | None) -> tuple[dict[str, Path], str, list[dict[str, Any]]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    records = dataframe_to_records(df)
    json_path = output_dir / OUTPUT_JSON
    csv_path = output_dir / OUTPUT_CSV
    summary_path = output_dir / OUTPUT_SUMMARY
    chart_path = output_dir / OUTPUT_CHART

    payload = {
        "metadata": {
            "dataset": "Serie consolidada de RMD",
            "base_real_ipca_periodo": base_period,
            "gerado_em": pd.Timestamp.now().isoformat(),
            "observacoes": len(records),
        },
        "dados": records,
    }

    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    df.to_csv(csv_path, index=False)

    summary_text = create_summary(df, base_period)
    summary_path.write_text(summary_text, encoding="utf-8")
    save_dashboard(df, chart_path, base_period)

    return {
        "json": json_path,
        "csv": csv_path,
        "summary": summary_path,
        "chart": chart_path,
    }, summary_text, records


def save_dashboard(df: pd.DataFrame, chart_path: Path, base_period: str | None) -> None:
    if df.empty:
        return
    dates = pd.to_datetime(df["periodo"] + "-01", errors="coerce")
    stock = pd.to_numeric(df["estoque_nominal_brl_bilhoes"], errors="coerce")
    figure = Figure(figsize=(12, 12), constrained_layout=True)
    FigureCanvasAgg(figure)
    axes = figure.subplots(3, 1)

    axes[0].plot(
        dates,
        stock,
        color="#f5821f",
        linewidth=2.2,
        marker="o",
        markersize=6,
        label="Nominal",
    )
    if "estoque_real_brl_bilhoes" in df.columns and df["estoque_real_brl_bilhoes"].notna().any():
        label = f"Real ({base_period})" if base_period else "Real"
        axes[0].plot(
            dates,
            df["estoque_real_brl_bilhoes"],
            color="#2f6bff",
            linewidth=2.0,
            marker="o",
            markersize=5,
            label=label,
        )
    axes[0].set_title("Estoque da divida")
    axes[0].set_ylabel("R$ bi")
    axes[0].grid(alpha=0.25)
    axes[0].legend()

    comp_columns = ["prefixada_pct", "selic_pct", "taxa_flutuante_pct", "indice_precos_pct", "cambio_pct", "tr_pct"]
    available_comp = [column for column in comp_columns if column in df.columns and df[column].notna().any()]
    for column in available_comp:
        axes[1].plot(dates, df[column], linewidth=1.8, marker="o", markersize=4, label=column.replace("_pct", ""))
    axes[1].set_title("Composicao por indexador")
    axes[1].set_ylabel("%")
    axes[1].grid(alpha=0.25)
    if available_comp:
        axes[1].legend(ncol=3)

    flows = {
        "Emissoes": ("emissoes_nominais_brl_milhoes", "#29a36a", 1),
        "Resgates": ("resgates_nominais_brl_milhoes", "#d04d4d", -1),
    }
    for label, (column, color, direction) in flows.items():
        values = pd.to_numeric(df[column], errors="coerce")
        if values.notna().any():
            axes[2].bar(dates, direction * values, width=20, alpha=0.65, color=color, label=label)
    liquidity = pd.to_numeric(df["impacto_liquidez_nominal_brl_milhoes"], errors="coerce")
    if liquidity.notna().any():
        axes[2].plot(dates, liquidity, color="#1f1f1f", linewidth=1.8, marker="o", label="Impacto liquidez")
    axes[2].set_title("Fluxos nominais")
    axes[2].set_ylabel("R$ mi")
    axes[2].grid(alpha=0.25)
    handles, labels = axes[2].get_legend_handles_labels()
    if handles:
        axes[2].legend(handles, labels)
    else:
        axes[2].text(0.5, 0.5, "Fluxos não extraídos nesta execução", transform=axes[2].transAxes, ha="center", color="#666666")

    for axis in axes:
        valid_dates = dates.dropna()
        if len(valid_dates) == 1:
            center = valid_dates.iloc[0]
            axis.set_xlim(center - pd.Timedelta(days=20), center + pd.Timedelta(days=20))
            axis.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
            axis.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m/%Y"))
        axis.tick_params(axis="x", rotation=45)

    figure.savefig(chart_path, dpi=160)


def run_pipeline(
    input_dir: Path = DEFAULT_INPUT_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    ipca_path: Path = DEFAULT_IPCA_FILE,
    pib_path: Path = DEFAULT_PIB_FILE,
) -> PipelineResult:
    files = discover_rmd_files(input_dir)
    df = build_dataframe(files)
    ipca_df, base_period = load_ipca_dataframe(ipca_path)
    df, base_period = apply_ipca(df, ipca_df)
    pib_df = load_pib_dataframe(pib_path)
    df = apply_pib(df, pib_df)
    output_files, summary_text, records = save_outputs(df, output_dir, base_period)
    return PipelineResult(
        dataframe=df,
        output_files=output_files,
        summary_text=summary_text,
        base_label=base_period,
        records=records,
    )


def main() -> None:
    args = parse_args()
    result = run_pipeline(
        input_dir=args.entrada,
        output_dir=args.saida,
        ipca_path=args.ipca,
        pib_path=args.pib,
    )
    print(result.summary_text)
    print("")
    for label, path in result.output_files.items():
        print(f"{label}: {path}")


if __name__ == "__main__":
    main()
