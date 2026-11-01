from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

import customtkinter as ctk
import pandas as pd

from .analise import DEFAULT_INPUT_DIR, DEFAULT_IPCA_FILE, DEFAULT_OUTPUT_DIR, DEFAULT_PIB_FILE, run_pipeline
from .painel_graficos import open_dashboard
from .tk_lifecycle import gui_session, run_mainloop


APP_BG = "#f4efe7"
CARD_BG = "#fffaf4"
CARD_ALT = "#efe5d7"
TEXT = "#1f1a17"
MUTED = "#6d625b"
ACCENT = "#b85c38"
ACCENT_ALT = "#264653"
BORDER = "#d8c8b5"


def _pick_directory(entry: ctk.CTkEntry) -> None:
    directory = filedialog.askdirectory()
    if directory:
        entry.delete(0, tk.END)
        entry.insert(0, directory)


def _pick_file(entry: ctk.CTkEntry) -> None:
    filename = filedialog.askopenfilename(filetypes=[("CSV ou JSON", "*.csv *.json"), ("Todos", "*.*")])
    if filename:
        entry.delete(0, tk.END)
        entry.insert(0, filename)


def _configure_tree(root: ctk.CTk) -> None:
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure(
        "Debt.Treeview",
        background="#fffdf9",
        fieldbackground="#fffdf9",
        foreground=TEXT,
        bordercolor=BORDER,
        rowheight=28,
        font=("Segoe UI", 10),
    )
    style.configure(
        "Debt.Treeview.Heading",
        background=CARD_ALT,
        foreground=TEXT,
        bordercolor=BORDER,
        font=("Segoe UI", 10, "bold"),
        relief="flat",
    )


def _format_value(value: object, kind: str = "float") -> str:
    if value is None or pd.isna(value):
        return "n/d"
    if kind == "pct":
        return f"{float(value):.2f}%".replace(".", ",")
    if kind == "money_bi":
        return f"R$ {float(value):,.2f} bi".replace(",", "X").replace(".", ",").replace("X", ".")
    if kind == "money_mi":
        return f"R$ {float(value):,.2f} mi".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{float(value):.2f}".replace(".", ",")


def _render_chart(frame: ctk.CTkFrame, df: pd.DataFrame, chart_kind: str) -> None:
    from matplotlib import dates as mdates
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure

    for child in frame.winfo_children():
        child.destroy()

    if df.empty:
        ctk.CTkLabel(frame, text="Sem dados para plotar.", text_color=MUTED).pack(padx=20, pady=20)
        return

    dates = pd.to_datetime(df["periodo"] + "-01", errors="coerce")
    figure = Figure(figsize=(9, 4.8), dpi=110, facecolor=CARD_BG)
    axis = figure.add_subplot(111)
    axis.set_facecolor("#fffdf9")

    if chart_kind == "Composicao":
        series = {
            "Prefixada": ("prefixada_pct", ACCENT),
            "Selic": ("selic_pct", "#457b9d"),
            "Taxa flutuante": ("taxa_flutuante_pct", "#327b8c"),
            "Indice de precos": ("indice_precos_pct", "#2a9d8f"),
            "Cambio": ("cambio_pct", "#e9a23b"),
            "TR": ("tr_pct", "#8d6a9f"),
        }
        for label, (column, color) in series.items():
            if column in df.columns and df[column].notna().any():
                axis.plot(dates, df[column], color=color, linewidth=2, marker="o", markersize=5, label=label)
        axis.set_title("Composicao da divida por indexador")
        axis.set_ylabel("Participacao (%)")
        axis.legend(loc="best", ncol=2)
    elif chart_kind == "Fluxos":
        axis.bar(dates, df["emissoes_nominais_brl_milhoes"], width=20, color="#2a9d8f", alpha=0.8, label="Emissoes")
        axis.bar(dates, -df["resgates_nominais_brl_milhoes"], width=20, color="#d65a4a", alpha=0.8, label="Resgates")
        if df["impacto_liquidez_nominal_brl_milhoes"].notna().any():
            axis.plot(
                dates,
                df["impacto_liquidez_nominal_brl_milhoes"],
                color=TEXT,
                linewidth=2,
                marker="o",
                label="Impacto de liquidez",
            )
        axis.axhline(0, color=MUTED, linewidth=0.8)
        axis.set_title("Fluxos mensais da divida")
        axis.set_ylabel("R$ mi")
        axis.legend(loc="best")
    else:
        axis.plot(
            dates,
            df["estoque_nominal_brl_bilhoes"],
            color=ACCENT,
            linewidth=2.4,
            marker="o",
            markersize=7,
            label="Nominal",
        )
        if "estoque_real_brl_bilhoes" in df.columns and df["estoque_real_brl_bilhoes"].notna().any():
            axis.plot(
                dates,
                df["estoque_real_brl_bilhoes"],
                color=ACCENT_ALT,
                linewidth=2.2,
                marker="o",
                markersize=6,
                label="Real",
            )
        axis.set_title("Evolucao do estoque da divida publica")
        axis.set_ylabel("R$ bi")
        axis.legend(loc="best")

    axis.grid(alpha=0.25)
    valid_dates = dates.dropna()
    if len(valid_dates) == 1:
        center = valid_dates.iloc[0]
        axis.set_xlim(center - pd.Timedelta(days=20), center + pd.Timedelta(days=20))
        axis.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
        axis.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m/%Y"))
    for label in axis.get_xticklabels():
        label.set_rotation(40)
        label.set_horizontalalignment("right")

    canvas = FigureCanvasTkAgg(figure, master=frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)


@gui_session
def main() -> None:
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("Dívida e gastos públicos da União")
    root.geometry("1380x900")
    root.configure(fg_color=APP_BG)
    _configure_tree(root)

    input_var = tk.StringVar(value=str(DEFAULT_INPUT_DIR))
    output_var = tk.StringVar(value=str(DEFAULT_OUTPUT_DIR))
    ipca_var = tk.StringVar(value=str(DEFAULT_IPCA_FILE))
    pib_var = tk.StringVar(value=str(DEFAULT_PIB_FILE))
    status_var = tk.StringVar(value="Configure as pastas e rode a consolidacao.")
    cards_vars = {
        "periodo": tk.StringVar(value="n/d"),
        "estoque": tk.StringVar(value="n/d"),
        "real": tk.StringVar(value="n/d"),
        "divida_pib": tk.StringVar(value="n/d"),
    }
    current_dataframe = pd.DataFrame()

    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(1, weight=1)

    header = ctk.CTkFrame(root, fg_color="transparent")
    header.grid(row=0, column=0, sticky="ew", padx=24, pady=(18, 10))
    ctk.CTkLabel(
        header,
        text="Dívida e gastos públicos",
        font=("Segoe UI", 28, "bold"),
        text_color=TEXT,
    ).pack(anchor="w")
    ctk.CTkLabel(
        header,
        text="Serie nominal, serie real por IPCA e relacao divida/PIB em um fluxo unico.",
        font=("Segoe UI", 12),
        text_color=MUTED,
    ).pack(anchor="w", pady=(4, 0))

    body = ctk.CTkFrame(root, fg_color="transparent")
    body.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 24))
    body.grid_columnconfigure(0, weight=0)
    body.grid_columnconfigure(1, weight=1)
    body.grid_rowconfigure(0, weight=1)

    sidebar = ctk.CTkFrame(body, fg_color=CARD_BG, corner_radius=18, border_width=1, border_color=BORDER, width=360)
    sidebar.grid(row=0, column=0, sticky="nsw", padx=(0, 18))
    sidebar.grid_propagate(False)

    content = ctk.CTkFrame(body, fg_color="transparent")
    content.grid(row=0, column=1, sticky="nsew")
    content.grid_columnconfigure(0, weight=1)
    content.grid_rowconfigure(2, weight=1)

    ctk.CTkLabel(sidebar, text="Entradas", font=("Segoe UI", 18, "bold"), text_color=TEXT).pack(
        anchor="w", padx=18, pady=(18, 12)
    )

    def add_field(label: str, variable: tk.StringVar, picker: callable, file_mode: bool = False) -> None:
        ctk.CTkLabel(sidebar, text=label, text_color=MUTED, font=("Segoe UI", 11)).pack(anchor="w", padx=18, pady=(8, 4))
        row = ctk.CTkFrame(sidebar, fg_color="transparent")
        row.pack(fill=tk.X, padx=18)
        entry = ctk.CTkEntry(row, textvariable=variable, width=250, fg_color="#fffdf9", border_color=BORDER, text_color=TEXT)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ctk.CTkButton(
            row,
            text="...",
            width=42,
            fg_color=ACCENT,
            hover_color="#9d4b2d",
            command=lambda e=entry: picker(e),
        ).pack(side=tk.LEFT, padx=(8, 0))

    add_field("Pasta com RMDs", input_var, _pick_directory)
    add_field("Pasta de saida", output_var, _pick_directory)
    add_field("Arquivo IPCA", ipca_var, _pick_file, file_mode=True)
    add_field("Arquivo PIB", pib_var, _pick_file, file_mode=True)

    summary_box = scrolledtext.ScrolledText(
        sidebar,
        height=15,
        wrap=tk.WORD,
        bg="#fffdf9",
        fg=TEXT,
        insertbackground=TEXT,
        relief="flat",
        font=("Consolas", 10),
    )
    summary_box.pack(fill=tk.BOTH, expand=True, padx=18, pady=(18, 12))

    status_label = ctk.CTkLabel(sidebar, textvariable=status_var, text_color=MUTED, wraplength=310, justify="left")
    status_label.pack(anchor="w", padx=18, pady=(0, 12))

    from .painel_gastos import open_spending_dashboard

    ctk.CTkButton(
        sidebar,
        text="Gastos públicos por categoria",
        fg_color=ACCENT_ALT,
        command=lambda: open_spending_dashboard(root, Path(output_var.get()) / "gastos_publicos"),
    ).pack(fill=tk.X, padx=18, pady=(0, 12))

    ctk.CTkButton(
        sidebar,
        text="Abrir painel de gráficos",
        fg_color=ACCENT_ALT,
        hover_color="#1e3944",
        command=lambda: open_dashboard(root, current_dataframe),
    ).pack(fill=tk.X, padx=18, pady=(0, 12))

    columns = ("periodo", "estoque", "real", "divida_pib", "prazo", "selic")
    tree = ttk.Treeview(content, columns=columns, show="headings", style="Debt.Treeview", height=12)
    headings = {
        "periodo": "Periodo",
        "estoque": "Estoque nominal",
        "real": "Estoque real",
        "divida_pib": "Divida/PIB",
        "prazo": "Prazo medio",
        "selic": "Selic %",
    }
    widths = {"periodo": 100, "estoque": 170, "real": 170, "divida_pib": 100, "prazo": 100, "selic": 90}
    for column in columns:
        tree.heading(column, text=headings[column])
        tree.column(column, width=widths[column], anchor="center")

    cards = ctk.CTkFrame(content, fg_color="transparent")
    cards.grid(row=0, column=0, sticky="ew", pady=(0, 16))
    for index in range(4):
        cards.grid_columnconfigure(index, weight=1)

    card_defs = [
        ("Periodo final", "periodo"),
        ("Estoque nominal", "estoque"),
        ("Estoque real", "real"),
        ("Divida / PIB", "divida_pib"),
    ]
    for idx, (title, key) in enumerate(card_defs):
        card = ctk.CTkFrame(cards, fg_color=CARD_BG, corner_radius=18, border_width=1, border_color=BORDER)
        card.grid(row=0, column=idx, sticky="ew", padx=(0 if idx == 0 else 8, 0))
        ctk.CTkLabel(card, text=title, text_color=MUTED, font=("Segoe UI", 11)).pack(anchor="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(card, textvariable=cards_vars[key], text_color=TEXT, font=("Segoe UI", 20, "bold")).pack(
            anchor="w", padx=16, pady=(0, 14)
        )

    chart_frame = ctk.CTkFrame(content, fg_color=CARD_BG, corner_radius=18, border_width=1, border_color=BORDER)
    chart_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 16))
    ctk.CTkLabel(
        chart_frame,
        text="Visualizações em painel dedicado",
        font=("Georgia", 20, "bold"),
        text_color=TEXT,
    ).pack(anchor="w", padx=22, pady=(22, 4))
    ctk.CTkLabel(
        chart_frame,
        text="Use “Abrir painel de gráficos” para analisar estoque, composição e fluxos sem poluir esta tela.",
        font=("Segoe UI", 12),
        text_color=MUTED,
    ).pack(anchor="w", padx=22, pady=(0, 22))

    table_frame = ctk.CTkFrame(content, fg_color=CARD_BG, corner_radius=18, border_width=1, border_color=BORDER)
    table_frame.grid(row=2, column=0, sticky="nsew")
    table_frame.grid_rowconfigure(0, weight=1)
    table_frame.grid_columnconfigure(0, weight=1)
    tree.grid(in_=table_frame, row=0, column=0, sticky="nsew", padx=12, pady=12)

    def execute() -> None:
        nonlocal current_dataframe
        try:
            status_var.set("Processando arquivos e consolidando a serie...")
            root.update_idletasks()
            result = run_pipeline(
                input_dir=Path(input_var.get()),
                output_dir=Path(output_var.get()),
                ipca_path=Path(ipca_var.get()),
                pib_path=Path(pib_var.get()),
            )
        except Exception as exc:
            status_var.set("Falha na consolidacao.")
            messagebox.showerror("Erro", str(exc))
            return

        df = result.dataframe.copy()
        current_dataframe = df
        summary_box.delete("1.0", tk.END)
        summary_box.insert("1.0", result.summary_text)

        for item in tree.get_children():
            tree.delete(item)

        for _, row in df.tail(24).iterrows():
            tree.insert(
                "",
                tk.END,
                values=(
                    row.get("periodo"),
                    _format_value(row.get("estoque_nominal_brl_bilhoes"), "money_bi"),
                    _format_value(row.get("estoque_real_brl_bilhoes"), "money_bi"),
                    _format_value(row.get("divida_pib_pct"), "pct"),
                    _format_value(row.get("prazo_medio_meses")),
                    _format_value(row.get("selic_pct"), "pct"),
                ),
            )

        if not df.empty:
            latest = df.iloc[-1]
            cards_vars["periodo"].set(str(latest.get("periodo", "n/d")))
            cards_vars["estoque"].set(_format_value(latest.get("estoque_nominal_brl_bilhoes"), "money_bi"))
            cards_vars["real"].set(_format_value(latest.get("estoque_real_brl_bilhoes"), "money_bi"))
            cards_vars["divida_pib"].set(_format_value(latest.get("divida_pib_pct"), "pct"))

        status_var.set(
            "Consolidacao concluida. Saidas em "
            + str(result.output_files["json"].parent)
        )

    ctk.CTkButton(
        sidebar,
        text="Rodar consolidacao",
        fg_color=ACCENT,
        hover_color="#9d4b2d",
        text_color="#fffaf4",
        height=42,
        command=execute,
    ).pack(fill=tk.X, padx=18, pady=(0, 18))

    execute()
    run_mainloop(root)
