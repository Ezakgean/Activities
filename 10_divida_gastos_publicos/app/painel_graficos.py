from __future__ import annotations

from pathlib import Path
import tkinter as tk

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.dates import DateFormatter, YearLocator
from matplotlib.figure import Figure
import pandas as pd

from .tk_lifecycle import gui_session, run_mainloop


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CSV = BASE_DIR / "data" / "output" / "serie_divida_publica_consolidada.csv"

INK = "#17212b"
PAPER = "#f6f2ea"
PANEL = "#fffcf6"
LINE = "#c55d38"
TEAL = "#1d6b69"
GOLD = "#c99730"
MUTED = "#69727a"
EDGE = "#ded6c9"


def reliable_stock_data(dataframe: pd.DataFrame) -> pd.DataFrame:
    data = dataframe.copy()
    data["data"] = pd.to_datetime(data["periodo"] + "-01", errors="coerce")
    data["estoque_nominal_brl_bilhoes"] = pd.to_numeric(data["estoque_nominal_brl_bilhoes"], errors="coerce")
    # A DPF nunca esteve abaixo de R$ 400 bi no período coberto pelo RMD.
    return data.loc[data["estoque_nominal_brl_bilhoes"].between(400, 20_000)].sort_values("data")


def _format_number(value: object, suffix: str = "") -> str:
    value = pd.to_numeric(value, errors="coerce")
    if pd.isna(value):
        return "n/d"
    return f"{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + suffix


def _latest_value(dataframe: pd.DataFrame, column: str) -> object:
    values = dataframe[["periodo", column]].copy().dropna(subset=[column]) if column in dataframe else pd.DataFrame()
    return values.iloc[-1][column] if not values.empty else None


def _line_segments(axis, data: pd.DataFrame, column: str, *, color: str, label: str) -> None:
    series = data[["data", column]].copy()
    series[column] = pd.to_numeric(series[column], errors="coerce")
    series = series.dropna().sort_values("data")
    if series.empty:
        return
    series["segment"] = series["data"].diff().dt.days.gt(62).cumsum()
    first = True
    for _, segment in series.groupby("segment"):
        if len(segment) == 1:
            axis.scatter(segment["data"], segment[column], color=color, s=28, zorder=3, label=label if first else None)
        else:
            axis.plot(segment["data"], segment[column], color=color, linewidth=2.7, label=label if first else None)
        first = False


def _style_axis(axis, title: str, ylabel: str) -> None:
    axis.set_title(title, loc="left", fontsize=17, fontweight="bold", color=INK, pad=16)
    axis.set_ylabel(ylabel, color=MUTED)
    axis.grid(axis="y", color="#d9d2c7", linewidth=0.8, alpha=0.7)
    axis.spines[["top", "right"]].set_visible(False)
    axis.spines[["left", "bottom"]].set_color(EDGE)
    axis.tick_params(colors=MUTED)
    axis.xaxis.set_major_locator(YearLocator(base=2))
    axis.xaxis.set_major_formatter(DateFormatter("%Y"))


def _draw_chart(frame: ctk.CTkFrame, dataframe: pd.DataFrame, view: str) -> None:
    for child in frame.winfo_children():
        child.destroy()

    reliable = reliable_stock_data(dataframe)
    figure = Figure(figsize=(10.5, 6.5), dpi=110, facecolor=PANEL)
    axis = figure.add_subplot(111)
    axis.set_facecolor(PANEL)
    has_series = False

    if view == "Composição":
        source = dataframe.copy()
        source["data"] = pd.to_datetime(source["periodo"] + "-01", errors="coerce")
        series = {
            "Prefixada": ("prefixada_pct", LINE),
            "Selic": ("selic_pct", TEAL),
            "Taxa flutuante": ("taxa_flutuante_pct", "#327b8c"),
            "Índice de preços": ("indice_precos_pct", GOLD),
            "Câmbio": ("cambio_pct", "#7763a6"),
            "TR": ("tr_pct", "#9a784c"),
            "Outros": ("outros_pct", "#888888"),
        }
        for label, (column, color) in series.items():
            if column in source:
                values = pd.to_numeric(source[column], errors="coerce")
                if values.notna().any():
                    _line_segments(axis, source, column, color=color, label=label)
                    has_series = True
        _style_axis(axis, "Composição por indexador", "Participação (%)")
    elif view == "Fluxos":
        source = dataframe.copy()
        source["data"] = pd.to_datetime(source["periodo"] + "-01", errors="coerce")
        flows = {
            "Emissões": ("emissoes_nominais_brl_milhoes", TEAL),
            "Resgates": ("resgates_nominais_brl_milhoes", LINE),
            "Impacto de liquidez": ("impacto_liquidez_nominal_brl_milhoes", GOLD),
        }
        for label, (column, color) in flows.items():
            if column in source:
                values = pd.to_numeric(source[column], errors="coerce")
                if values.notna().any():
                    _line_segments(axis, source, column, color=color, label=label)
                    has_series = True
        axis.axhline(0, color=EDGE, linewidth=1)
        _style_axis(axis, "Fluxos mensais", "R$ milhões")
    else:
        _line_segments(axis, reliable, "estoque_nominal_brl_bilhoes", color=LINE, label="Estoque nominal")
        has_series = not reliable.empty
        if "estoque_real_brl_bilhoes" in reliable:
            _line_segments(axis, reliable, "estoque_real_brl_bilhoes", color=TEAL, label="Estoque real")
        _style_axis(axis, "Estoque da dívida pública", "R$ bilhões")

    handles, labels = axis.get_legend_handles_labels()
    if handles:
        axis.legend(handles, labels, loc="upper left", frameon=False, ncol=3)
    if not has_series:
        axis.text(
            0.5,
            0.5,
            "Não há dados disponíveis para esta visualização.\nExecute a coleta completa e consolide novamente.",
            transform=axis.transAxes,
            ha="center",
            va="center",
            fontsize=13,
            color=MUTED,
        )
        axis.set_xticks([])
    figure.tight_layout(pad=2.2)
    canvas = FigureCanvasTkAgg(figure, master=frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)


def open_dashboard(parent: tk.Misc, dataframe: pd.DataFrame) -> None:
    window = ctk.CTkToplevel(parent)
    window.title("Painel de gráficos | Dívida Pública")
    window.geometry("1280x790")
    window.minsize(1000, 650)
    window.configure(fg_color=PAPER)
    window.grid_columnconfigure(1, weight=1)
    window.grid_rowconfigure(0, weight=1)

    sidebar = ctk.CTkFrame(window, width=245, corner_radius=0, fg_color=INK)
    sidebar.grid(row=0, column=0, sticky="nsew")
    sidebar.grid_propagate(False)
    ctk.CTkLabel(sidebar, text="DÍVIDA\nEM FOCO", font=("Georgia", 23, "bold"), text_color="#f7e6c8", justify="left").pack(
        anchor="w", padx=25, pady=(35, 10)
    )
    ctk.CTkLabel(
        sidebar,
        text="Série histórica consolidada\ncom quebras em lacunas de dados.",
        font=("Segoe UI", 11),
        text_color="#b8c1c8",
        justify="left",
    ).pack(anchor="w", padx=25, pady=(0, 34))

    content = ctk.CTkFrame(window, fg_color="transparent")
    content.grid(row=0, column=1, sticky="nsew", padx=34, pady=28)
    content.grid_rowconfigure(3, weight=1)
    content.grid_columnconfigure(0, weight=1)

    reliable = reliable_stock_data(dataframe)
    ctk.CTkLabel(content, text="Gráficos", font=("Georgia", 30, "bold"), text_color=INK).grid(row=0, column=0, sticky="w")
    subtitle = tk.StringVar()
    ctk.CTkLabel(content, textvariable=subtitle, font=("Segoe UI", 12), text_color=MUTED).grid(row=1, column=0, sticky="w", pady=(4, 22))

    metrics = ctk.CTkFrame(content, fg_color="transparent")
    metrics.grid(row=2, column=0, sticky="ew", pady=(0, 18))
    for index in range(3):
        metrics.grid_columnconfigure(index, weight=1)
    metric_values = [tk.StringVar(value="n/d") for _ in range(3)]
    metric_titles = [tk.StringVar(value="Referência") for _ in range(3)]
    for index in range(3):
        card = ctk.CTkFrame(metrics, fg_color="#efe8dd", corner_radius=12)
        card.grid(row=0, column=index, sticky="ew", padx=(0 if index == 0 else 9, 0))
        ctk.CTkLabel(card, textvariable=metric_titles[index], font=("Segoe UI", 10, "bold"), text_color=MUTED).pack(
            anchor="w", padx=14, pady=(10, 1)
        )
        ctk.CTkLabel(card, textvariable=metric_values[index], font=("Georgia", 17, "bold"), text_color=INK).pack(
            anchor="w", padx=14, pady=(0, 11)
        )

    chart_card = ctk.CTkFrame(content, fg_color=PANEL, corner_radius=18, border_width=1, border_color=EDGE)
    chart_card.grid(row=3, column=0, sticky="nsew")
    chart_card.grid_rowconfigure(0, weight=1)
    chart_card.grid_columnconfigure(0, weight=1)

    def select_view(view: str) -> None:
        _draw_chart(chart_card, dataframe, view)
        columns = {
            "Composição": ["prefixada_pct", "selic_pct", "taxa_flutuante_pct", "indice_precos_pct", "cambio_pct"],
            "Fluxos": ["emissoes_nominais_brl_milhoes", "resgates_nominais_brl_milhoes"],
        }.get(view, [])
        if columns:
            available = dataframe.reindex(columns=columns).notna().any(axis=1)
            periods = dataframe.loc[available, "periodo"]
            subtitle.set(f"{len(periods)} competências com dados de {view.lower()}" + (f" • última: {periods.max()}" if not periods.empty else ""))
        else:
            subtitle.set(f"{len(reliable)} observações de estoque dentro da faixa plausível")
        if view == "Estoque" and not reliable.empty:
            latest = reliable.iloc[-1]
            previous = reliable.iloc[-2] if len(reliable) > 1 else None
            variation = "n/d" if previous is None else f"{((latest['estoque_nominal_brl_bilhoes'] / previous['estoque_nominal_brl_bilhoes']) - 1) * 100:.2f}%"
            values = [
                ("Estoque nominal", f"R$ {_format_number(latest['estoque_nominal_brl_bilhoes'])} bi"),
                ("Variação entre pontos", variation.replace(".", ",")),
                ("Última competência confiável", str(latest["periodo"])),
            ]
        elif view == "Composição":
            floating = "taxa_flutuante_pct" in dataframe and dataframe["taxa_flutuante_pct"].notna().any()
            values = [
                ("Prefixada", _format_number(_latest_value(dataframe, "prefixada_pct"), "%")),
                ("Taxa flutuante" if floating else "Selic", _format_number(_latest_value(dataframe, "taxa_flutuante_pct" if floating else "selic_pct"), "%")),
                ("Índice de preços", _format_number(_latest_value(dataframe, "indice_precos_pct"), "%")),
            ]
        else:
            latest = dataframe.dropna(subset=["periodo"]).iloc[-1]
            values = [
                ("Emissões", f"R$ {_format_number(_latest_value(dataframe, 'emissoes_nominais_brl_milhoes'))} mi"),
                ("Resgates", f"R$ {_format_number(_latest_value(dataframe, 'resgates_nominais_brl_milhoes'))} mi"),
                ("Competência", str(latest["periodo"])),
            ]
        for index, (title, value) in enumerate(values):
            metric_titles[index].set(title)
            metric_values[index].set(value)
        for name, button in buttons.items():
            button.configure(fg_color="#d27950" if name == view else "transparent")

    buttons: dict[str, ctk.CTkButton] = {}
    for name in ("Estoque", "Composição", "Fluxos"):
        button = ctk.CTkButton(
            sidebar,
            text=name,
            anchor="w",
            height=42,
            corner_radius=8,
            fg_color="transparent",
            hover_color="#2b3a47",
            text_color="#f5efe6",
            font=("Segoe UI", 13, "bold"),
            command=lambda value=name: select_view(value),
        )
        button.pack(fill=tk.X, padx=16, pady=4)
        buttons[name] = button
    select_view("Estoque")
    window.focus_set()


@gui_session
def main() -> None:
    if not DEFAULT_CSV.exists():
        raise FileNotFoundError("Execute a consolidação antes de abrir o painel de gráficos.")
    ctk.set_appearance_mode("light")
    root = ctk.CTk()
    root.withdraw()
    open_dashboard(root, pd.read_csv(DEFAULT_CSV))
    run_mainloop(root)


if __name__ == "__main__":
    main()
