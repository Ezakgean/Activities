from __future__ import annotations

import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd

from .analise import (
    DEFAULT_INPUT,
    DEFAULT_OUTPUT_DIR,
    format_brl,
    format_brl_compact,
    format_p_value,
    format_percent,
    run_pipeline,
    save_pdf_report,
)


APP_BG = "#0f0f10"
SHELL_BG = "#141516"
CARD_BG = "#141516"
CARD_ALT = "#17181a"
FIELD_BG = "#17181a"
BORDER_COLOR = "#2a2b2e"
TEXT_PRIMARY = "#f7f7f7"
TEXT_MUTED = "#9aa0a6"
TEXT_SOFT = "#9aa0a6"
ACCENT = "#f5821f"
ACCENT_HOVER = "#ff8c33"
SECONDARY = "#2a2b2e"
SECONDARY_HOVER = "#33353a"
GHOST_BG = "#2a2b2e"
GHOST_HOVER = "#33353a"
SUCCESS = "#f5821f"
TABLE_BAND_A = "#17181a"
TABLE_BAND_B = "#1b1d20"

NAV_ITEMS = [
    ("execution", "Execucao"),
    ("dashboard", "Dashboard"),
    ("summary", "Resumo"),
    ("regressions", "Regressoes"),
    ("means", "Medias"),
    ("files", "Arquivos"),
]


def _load_logo_image() -> tk.PhotoImage | None:
    logo_path = Path(__file__).resolve().parents[2] / "src" / "logo2.png"
    if not logo_path.exists():
        return None
    try:
        return tk.PhotoImage(file=str(logo_path))
    except Exception:
        return None


def _bind_responsive_logo(root: ctk.CTk, logo_label: ctk.CTkLabel, logo_image: tk.PhotoImage) -> None:
    def on_resize(event: tk.Event | None = None) -> None:
        width = root.winfo_width() or 1360
        target_height = max(32, min(52, int(width * 0.034)))
        original_height = max(1, logo_image.height())
        scale = max(1, int(original_height / target_height))
        scaled = logo_image.subsample(scale, scale)
        logo_label.configure(image=scaled)
        logo_label.image = scaled

    root.bind("<Configure>", on_resize, add="+")
    on_resize()


def _select_file(entry: ctk.CTkEntry) -> None:
    filename = filedialog.askopenfilename(
        title="Selecione o arquivo JSON",
        filetypes=[("JSON", "*.json"), ("Todos", "*")],
    )
    if filename:
        entry.delete(0, tk.END)
        entry.insert(0, filename)


def _select_folder(entry: ctk.CTkEntry) -> None:
    folder = filedialog.askdirectory(title="Selecione a pasta de saida")
    if folder:
        entry.delete(0, tk.END)
        entry.insert(0, folder)


def _configure_treeview_style(root: ctk.CTk) -> None:
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(
        "Dashboard.Treeview",
        background=FIELD_BG,
        fieldbackground=FIELD_BG,
        foreground=TEXT_PRIMARY,
        rowheight=30,
        borderwidth=0,
        relief="flat",
        font=("Segoe UI", 10),
    )
    style.map(
        "Dashboard.Treeview",
        background=[("selected", ACCENT)],
        foreground=[("selected", "#1b1b1b")],
    )
    style.configure(
        "Dashboard.Treeview.Heading",
        background=CARD_BG,
        foreground=TEXT_PRIMARY,
        relief="flat",
        borderwidth=0,
        font=("Segoe UI", 10, "bold"),
        padding=(10, 8),
    )
    style.map("Dashboard.Treeview.Heading", background=[("active", GHOST_BG)])


def _show_screen(
    screen_name: str,
    screens: dict[str, ctk.CTkFrame],
    nav_buttons: dict[str, ctk.CTkButton],
    screen_title_var: tk.StringVar,
    screen_subtitle_var: tk.StringVar,
) -> None:
    labels = {
        "execution": (
            "Execucao",
            "Configure a entrada, dispare a analise e acompanhe o status da rodada.",
        ),
        "dashboard": (
            "Dashboard",
            "Visao executiva com cards e charts reorganizados para leitura por estado.",
        ),
        "summary": (
            "Resumo",
            "Texto interpretativo completo com metodologia, achados e conclusoes.",
        ),
        "regressions": (
            "Regressoes",
            "Coeficientes do modelo salario = beta0 + beta1 * ensino_superior por UF.",
        ),
        "means": (
            "Medias",
            "Comparacao das medias estimadas entre grupos com e sem exigencia de superior.",
        ),
        "files": (
            "Arquivos",
            "Inventario dos artefatos gerados na rodada atual.",
        ),
    }

    for name, frame in screens.items():
        if name == screen_name:
            frame.pack(fill=tk.BOTH, expand=True)
        else:
            frame.pack_forget()

    for name, button in nav_buttons.items():
        is_active = name == screen_name
        button.configure(
            fg_color=ACCENT if is_active else "transparent",
            hover_color=ACCENT_HOVER if is_active else GHOST_HOVER,
            text_color="#1b1b1b" if is_active else TEXT_MUTED,
            border_color=ACCENT if is_active else BORDER_COLOR,
        )

    title, subtitle = labels[screen_name]
    screen_title_var.set(title)
    screen_subtitle_var.set(subtitle)


def _create_surface(parent: ctk.CTkFrame) -> ctk.CTkFrame:
    return ctk.CTkFrame(parent, fg_color=CARD_BG, corner_radius=18, border_width=1, border_color=BORDER_COLOR)


def _create_stat_card(
    parent: ctk.CTkFrame,
    title: str,
    value_var: tk.StringVar,
    detail_var: tk.StringVar,
    accent_color: str,
) -> ctk.CTkFrame:
    card = _create_surface(parent)
    ctk.CTkFrame(card, fg_color=accent_color, width=8, corner_radius=8).pack(
        side=tk.LEFT, fill=tk.Y, padx=(0, 12), pady=14
    )

    text_block = ctk.CTkFrame(card, fg_color="transparent")
    text_block.pack(fill=tk.BOTH, expand=True, padx=(2, 16), pady=16)

    ctk.CTkLabel(
        text_block,
        text=title,
        text_color=TEXT_MUTED,
        font=("Segoe UI", 11),
    ).pack(anchor="w")
    ctk.CTkLabel(
        text_block,
        textvariable=value_var,
        text_color=TEXT_PRIMARY,
        font=("Segoe UI", 20, "bold"),
    ).pack(anchor="w", pady=(4, 4))
    detail_label = ctk.CTkLabel(
        text_block,
        textvariable=detail_var,
        text_color=TEXT_MUTED,
        font=("Segoe UI", 10),
        justify="left",
        wraplength=220,
    )
    detail_label.pack(anchor="w")
    card.detail_label = detail_label
    return card


def _create_info_panel(parent: ctk.CTkFrame, title: str, body: str) -> ctk.CTkFrame:
    card = _create_surface(parent)
    ctk.CTkLabel(
        card,
        text=title,
        text_color=TEXT_PRIMARY,
        font=("Segoe UI", 13, "bold"),
    ).pack(anchor="w", padx=18, pady=(16, 6))
    body_label = ctk.CTkLabel(
        card,
        text=body,
        text_color=TEXT_MUTED,
        font=("Segoe UI", 11),
        justify="left",
        wraplength=320,
    )
    body_label.pack(anchor="w", padx=18, pady=(0, 16))
    card.body_label = body_label
    return card


def _set_grid_columns(container: tk.Misc, count: int, uniform: str = "") -> None:
    for index in range(6):
        container.grid_columnconfigure(index, weight=0, uniform="")
    for index in range(count):
        container.grid_columnconfigure(index, weight=1, uniform=uniform)


def _layout_nav_buttons(nav_right: ctk.CTkFrame, nav_buttons: dict[str, ctk.CTkButton], width: int) -> None:
    if width >= 1360:
        columns = 6
    elif width >= 1120:
        columns = 3
    else:
        columns = 2

    _set_grid_columns(nav_right, columns, uniform="nav")
    for button in nav_buttons.values():
        button.grid_forget()

    for index, (key, _label) in enumerate(NAV_ITEMS):
        row = index // columns
        column = index % columns
        nav_buttons[key].configure(width=0, height=36)
        nav_buttons[key].grid(
            row=row,
            column=column,
            sticky="ew",
            padx=(0, 10 if column < columns - 1 else 0),
            pady=(0, 8 if row == 0 and len(NAV_ITEMS) > columns else 0),
        )


def _layout_dashboard_cards(
    metrics_frame: ctk.CTkFrame,
    cards: list[ctk.CTkFrame],
    width: int,
) -> None:
    if width >= 1380:
        columns = 4
    elif width >= 1040:
        columns = 2
    else:
        columns = 1

    _set_grid_columns(metrics_frame, columns, uniform="metrics")
    for card in cards:
        card.grid_forget()
        if hasattr(card, "detail_label"):
            card.detail_label.configure(wraplength=max(220, min(360, width // max(columns, 1) - 90)))

    for index, card in enumerate(cards):
        row = index // columns
        column = index % columns
        card.grid(
            row=row,
            column=column,
            sticky="nsew",
            padx=(0, 10 if column < columns - 1 else 0),
            pady=(0, 10 if index + columns < len(cards) else 0),
        )


def _layout_form_grid(
    form_grid: ctk.CTkFrame,
    input_label: ctk.CTkLabel,
    input_entry: ctk.CTkEntry,
    input_button: ctk.CTkButton,
    output_label: ctk.CTkLabel,
    output_entry: ctk.CTkEntry,
    output_button: ctk.CTkButton,
    width: int,
) -> None:
    widgets = [input_label, input_entry, input_button, output_label, output_entry, output_button]
    for widget in widgets:
        widget.grid_forget()

    for index in range(3):
        form_grid.grid_columnconfigure(index, weight=0)

    if width >= 1100:
        form_grid.grid_columnconfigure(1, weight=1)
        input_label.grid(row=0, column=0, sticky="w", padx=(0, 12), pady=(0, 8))
        input_entry.grid(row=0, column=1, sticky="ew", pady=(0, 8))
        input_button.grid(row=0, column=2, sticky="ew", padx=(12, 0), pady=(0, 8))
        output_label.grid(row=1, column=0, sticky="w", padx=(0, 12), pady=(10, 0))
        output_entry.grid(row=1, column=1, sticky="ew", pady=(10, 0))
        output_button.grid(row=1, column=2, sticky="ew", padx=(12, 0), pady=(10, 0))
        return

    form_grid.grid_columnconfigure(0, weight=1)
    form_grid.grid_columnconfigure(1, weight=0)
    input_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
    input_entry.grid(row=1, column=0, sticky="ew", pady=(0, 8))
    input_button.grid(row=1, column=1, sticky="ew", padx=(12, 0), pady=(0, 8))
    output_label.grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 8))
    output_entry.grid(row=3, column=0, sticky="ew")
    output_button.grid(row=3, column=1, sticky="ew", padx=(12, 0))


def _layout_action_row(
    action_row: ctk.CTkFrame,
    quick_run_button: ctk.CTkButton,
    pdf_button: ctk.CTkButton,
    width: int,
) -> None:
    quick_run_button.pack_forget()
    pdf_button.pack_forget()

    if width < 980:
        quick_run_button.pack(fill=tk.X, pady=(0, 10))
        pdf_button.pack(fill=tk.X)
        return

    pdf_button.pack(side=tk.RIGHT)
    quick_run_button.pack(side=tk.RIGHT, padx=(0, 10))


def _layout_execution_screen(
    execution_screen: ctk.CTkFrame,
    run_card: ctk.CTkFrame,
    right_stack: ctk.CTkFrame,
    width: int,
) -> None:
    run_card.grid_forget()
    right_stack.grid_forget()

    execution_screen.grid_columnconfigure(0, weight=0, uniform="")
    execution_screen.grid_columnconfigure(1, weight=0, uniform="")
    execution_screen.grid_rowconfigure(0, weight=0)
    execution_screen.grid_rowconfigure(1, weight=0)

    if width >= 1240:
        execution_screen.grid_columnconfigure(0, weight=7, uniform="execution")
        execution_screen.grid_columnconfigure(1, weight=5, uniform="execution")
        execution_screen.grid_rowconfigure(0, weight=1)
        run_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        right_stack.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        return

    execution_screen.grid_columnconfigure(0, weight=1)
    run_card.grid(row=0, column=0, sticky="nsew", pady=(0, 14))
    right_stack.grid(row=1, column=0, sticky="nsew")


def _layout_header_blocks(
    brand_block: ctk.CTkFrame,
    header_meta: ctk.CTkFrame,
    nav_left: ctk.CTkFrame,
    nav_right: ctk.CTkFrame,
    width: int,
) -> None:
    brand_block.pack_forget()
    header_meta.pack_forget()
    nav_left.pack_forget()
    nav_right.pack_forget()

    if width < 1180:
        brand_block.pack(fill=tk.X, anchor="w")
        header_meta.pack(fill=tk.X, anchor="w", pady=(12, 0))
        nav_left.pack(fill=tk.X, anchor="w", pady=(0, 10))
        nav_right.pack(fill=tk.X)
        return

    brand_block.pack(side=tk.LEFT)
    header_meta.pack(side=tk.RIGHT)
    nav_left.pack(side=tk.LEFT)
    nav_right.pack(side=tk.RIGHT)


def _clear_treeview(tree: ttk.Treeview) -> None:
    tree.delete(*tree.get_children())
    tree["columns"] = ()


def _find_state_column(columns: list[str]) -> str | None:
    for candidate in ("UF", "Estado", "estado", "estado_nome"):
        if candidate in columns:
            return candidate
    return None


def _populate_treeview(
    tree: ttk.Treeview,
    dataframe: pd.DataFrame,
    placeholder_label: ctk.CTkLabel,
) -> None:
    _clear_treeview(tree)

    if dataframe.empty:
        placeholder_label.configure(text="Execute a analise para carregar esta tela.")
        placeholder_label.place(relx=0.5, rely=0.5, anchor="center")
        return

    placeholder_label.place_forget()
    columns = list(dataframe.columns)
    tree["columns"] = columns
    tree["show"] = "headings"
    tree.tag_configure("state_band_0", background=TABLE_BAND_A, foreground=TEXT_PRIMARY)
    tree.tag_configure("state_band_1", background=TABLE_BAND_B, foreground=TEXT_PRIMARY)

    for column in columns:
        anchor = tk.W if any(
            key in column.lower() for key in ["estado", "grupo", "arquivo", "caminho"]
        ) else tk.CENTER
        width = 120
        if "estado" in column.lower():
            width = 170
        elif "arquivo" in column.lower() or "caminho" in column.lower():
            width = 320
        elif "salario" in column.lower() or "premio" in column.lower():
            width = 150

        tree.heading(column, text=column)
        tree.column(column, width=width, minwidth=90, stretch=True, anchor=anchor)

    state_column = _find_state_column(columns)
    state_index = columns.index(state_column) if state_column is not None else None
    current_state = None
    current_band = 1

    for row_index, row in enumerate(dataframe.itertuples(index=False, name=None)):
        values = ["" if pd.isna(value) else str(value) for value in row]
        if state_index is not None:
            state_value = values[state_index]
            if state_value != current_state:
                current_state = state_value
                current_band = 1 - current_band
            band_tag = f"state_band_{current_band}"
        else:
            band_tag = f"state_band_{row_index % 2}"

        tree.insert("", tk.END, values=values, tags=(band_tag,))


def _format_regressions_for_view(regressions_df: pd.DataFrame) -> pd.DataFrame:
    view = regressions_df[
        [
            "estado",
            "estado_nome",
            "salario_sem_superior_brl",
            "premio_superior_brl",
            "salario_com_superior_brl",
            "premio_superior_percentual",
            "r2",
            "p_valor_beta1",
        ]
    ].copy()
    view["salario_sem_superior_brl"] = view["salario_sem_superior_brl"].map(format_brl)
    view["premio_superior_brl"] = view["premio_superior_brl"].map(format_brl)
    view["salario_com_superior_brl"] = view["salario_com_superior_brl"].map(format_brl)
    view["premio_superior_percentual"] = view["premio_superior_percentual"].map(format_percent)
    view["r2"] = view["r2"].map(lambda value: f"{value:.4f}")
    view["p_valor_beta1"] = view["p_valor_beta1"].map(format_p_value)
    return view.rename(
        columns={
            "estado": "UF",
            "estado_nome": "Estado",
            "salario_sem_superior_brl": "Base sem superior",
            "premio_superior_brl": "Premio superior",
            "salario_com_superior_brl": "Previsto com superior",
            "premio_superior_percentual": "Premio %",
            "r2": "R2",
            "p_valor_beta1": "p-valor",
        }
    )


def _format_means_for_view(state_means_df: pd.DataFrame) -> pd.DataFrame:
    view = state_means_df[
        [
            "estado",
            "estado_nome",
            "escolaridade_label",
            "n_profissoes",
            "salario_medio_brl",
            "salario_mediano_brl",
            "salario_dp_brl",
        ]
    ].copy()
    view["salario_medio_brl"] = view["salario_medio_brl"].map(format_brl)
    view["salario_mediano_brl"] = view["salario_mediano_brl"].map(format_brl)
    view["salario_dp_brl"] = view["salario_dp_brl"].map(format_brl)
    return view.rename(
        columns={
            "estado": "UF",
            "estado_nome": "Estado",
            "escolaridade_label": "Grupo",
            "n_profissoes": "N",
            "salario_medio_brl": "Salario medio",
            "salario_mediano_brl": "Salario mediano",
            "salario_dp_brl": "Desvio padrao",
        }
    )


def _update_dashboard(plot_frame: ctk.CTkFrame, fig) -> None:
    if hasattr(plot_frame, "canvas") and plot_frame.canvas is not None:
        plot_frame.canvas.get_tk_widget().destroy()
        plot_frame.canvas = None

    for child in plot_frame.winfo_children():
        child.destroy()
    canvas = FigureCanvasTkAgg(fig, master=plot_frame)
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.configure(background=FIELD_BG, highlightthickness=0, borderwidth=0)
    canvas_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    canvas.draw()
    plot_frame.canvas = canvas


def _update_output_text(
    output_text: scrolledtext.ScrolledText,
    stats_text: str,
    generated_files: list[Path],
) -> None:
    output_text.configure(state="normal")
    output_text.delete("1.0", tk.END)
    output_text.insert(tk.END, stats_text)
    output_text.insert(tk.END, "\n\nArquivos gerados:\n")
    for path in generated_files:
        output_text.insert(tk.END, f"- {path}\n")
    output_text.configure(state="disabled")


def _refresh_file_cards(files_container: ctk.CTkScrollableFrame, generated_files: list[Path]) -> None:
    for child in files_container.winfo_children():
        child.destroy()

    if not generated_files:
        ctk.CTkLabel(
            files_container,
            text="Execute a analise para listar os arquivos gerados.",
            text_color=TEXT_MUTED,
            font=("Segoe UI", 12),
        ).pack(anchor="center", pady=40)
        return

    for path in generated_files:
        card = _create_surface(files_container)
        card.pack(fill=tk.X, pady=(0, 10))
        ctk.CTkLabel(
            card,
            text=path.name,
            text_color=TEXT_PRIMARY,
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w", padx=18, pady=(16, 4))
        ctk.CTkLabel(
            card,
            text=str(path),
            text_color=TEXT_MUTED,
            font=("Consolas", 10),
            justify="left",
            wraplength=760,
        ).pack(anchor="w", padx=18, pady=(0, 16))


def _update_execution_cards(
    execution_vars: dict[str, tk.StringVar],
    regressions_df: pd.DataFrame | None = None,
) -> None:
    if regressions_df is None or regressions_df.empty:
        execution_vars["status_value"].set("Aguardando")
        execution_vars["status_detail"].set("Sem execucao concluida nesta sessao.")
        execution_vars["premium_value"].set("R$ -,--")
        execution_vars["premium_detail"].set("Premio medio entre estados.")
        execution_vars["leader_value"].set("--")
        execution_vars["leader_detail"].set("Estado com maior premio salarial.")
        execution_vars["coverage_value"].set("15 UFs")
        execution_vars["coverage_detail"].set("Cobertura esperada apos rodar a base.")
        return

    top_state = regressions_df.iloc[0]
    execution_vars["status_value"].set("Concluida")
    execution_vars["status_detail"].set("A rodada mais recente gerou dashboard, tabelas e relatorio.")
    execution_vars["premium_value"].set(format_brl(float(regressions_df["premio_superior_brl"].mean())))
    execution_vars["premium_detail"].set(
        f"Premio medio | {format_percent(float(regressions_df['premio_superior_percentual'].mean()))}"
    )
    execution_vars["leader_value"].set(str(top_state["estado"]))
    execution_vars["leader_detail"].set(
        f"Maior premio: {format_brl(float(top_state['premio_superior_brl']))}"
    )
    execution_vars["coverage_value"].set(f"{len(regressions_df)} UFs")
    execution_vars["coverage_detail"].set("Todos os estados da base foram processados.")


def _update_dashboard_cards(
    dashboard_vars: dict[str, tk.StringVar],
    regressions_df: pd.DataFrame | None = None,
    analysis_df: pd.DataFrame | None = None,
) -> None:
    if regressions_df is None or regressions_df.empty:
        dashboard_vars["obs_value"].set("--")
        dashboard_vars["obs_detail"].set("Observacoes consolidadas por profissao e estado.")
        dashboard_vars["premium_value"].set("R$ -,--")
        dashboard_vars["premium_detail"].set("Diferencial medio entre grupos.")
        dashboard_vars["leader_value"].set("--")
        dashboard_vars["leader_detail"].set("UF com maior premio salarial.")
        dashboard_vars["floor_value"].set("--")
        dashboard_vars["floor_detail"].set("UF com menor premio salarial.")
        return

    top_state = regressions_df.iloc[0]
    bottom_state = regressions_df.iloc[-1]
    observations = len(analysis_df) if analysis_df is not None else int(regressions_df["n_obs"].sum())
    avg_premium = float(regressions_df["premio_superior_brl"].mean())
    avg_percent = float(regressions_df["premio_superior_percentual"].mean())

    dashboard_vars["obs_value"].set(f"{observations:,}".replace(",", "."))
    dashboard_vars["obs_detail"].set(f"{len(regressions_df)} UFs | base consolidada da rodada atual.")
    dashboard_vars["premium_value"].set(format_brl(avg_premium))
    dashboard_vars["premium_detail"].set(f"Diferencial medio | {format_percent(avg_percent)}")
    dashboard_vars["leader_value"].set(
        f"{top_state['estado']} | {format_brl_compact(float(top_state['premio_superior_brl']))}"
    )
    dashboard_vars["leader_detail"].set(str(top_state["estado_nome"]))
    dashboard_vars["floor_value"].set(
        f"{bottom_state['estado']} | {format_brl_compact(float(bottom_state['premio_superior_brl']))}"
    )
    dashboard_vars["floor_detail"].set(str(bottom_state["estado_nome"]))


def _execute_from_gui(
    input_entry: ctk.CTkEntry,
    output_entry: ctk.CTkEntry,
    status_var: tk.StringVar,
    top_status_var: tk.StringVar,
    output_text: scrolledtext.ScrolledText,
    plot_frame: ctk.CTkFrame,
    regressions_tree: ttk.Treeview,
    regressions_placeholder: ctk.CTkLabel,
    means_tree: ttk.Treeview,
    means_placeholder: ctk.CTkLabel,
    files_container: ctk.CTkScrollableFrame,
    screens: dict[str, ctk.CTkFrame],
    nav_buttons: dict[str, ctk.CTkButton],
    screen_title_var: tk.StringVar,
    screen_subtitle_var: tk.StringVar,
    report_state: dict,
    pdf_button: ctk.CTkButton,
    execution_vars: dict[str, tk.StringVar],
    dashboard_vars: dict[str, tk.StringVar],
) -> None:
    input_path_raw = input_entry.get().strip()
    output_dir_raw = output_entry.get().strip()

    if not input_path_raw:
        messagebox.showerror("Erro", "Selecione um arquivo JSON.")
        return

    if not output_dir_raw:
        messagebox.showerror("Erro", "Selecione uma pasta de saida.")
        return

    try:
        pdf_button.configure(state="disabled")
        status_var.set("Processando regressoes por estado...")
        top_status_var.set("Executando")
        output_text.update_idletasks()

        result = run_pipeline(Path(input_path_raw), Path(output_dir_raw))
        generated_files = [
            result.summary_path,
            result.flat_data_path,
            result.state_means_path,
            result.regressions_path,
            result.dashboard_path,
        ]

        report_state.clear()
        report_state.update(
            {
                "stats_text": result.stats_text,
                "figure": result.figure,
                "output_dir": result.output_dir,
                "generated_files": generated_files,
            }
        )

        _update_execution_cards(execution_vars, result.regressions_df)
        _update_dashboard_cards(dashboard_vars, result.regressions_df, result.analysis_frame)
        _update_output_text(output_text, result.stats_text, generated_files)
        _update_dashboard(plot_frame, result.figure)
        _populate_treeview(
            regressions_tree,
            _format_regressions_for_view(result.regressions_df),
            regressions_placeholder,
        )
        _populate_treeview(
            means_tree,
            _format_means_for_view(result.state_means_df),
            means_placeholder,
        )
        _refresh_file_cards(files_container, generated_files)

        status_var.set("Execucao concluida. Use o menu superior para navegar pelas telas.")
        top_status_var.set("Concluida")
        pdf_button.configure(state="normal")
        _show_screen("dashboard", screens, nav_buttons, screen_title_var, screen_subtitle_var)
        messagebox.showinfo("Sucesso", "A atividade 05 foi atualizada com a rodada atual.")
    except Exception as exc:
        status_var.set("Erro ao executar a analise.")
        top_status_var.set("Erro")
        print(f"Erro: {exc}", file=sys.stderr)
        messagebox.showerror("Erro", str(exc))


def _generate_pdf_from_gui(
    status_var: tk.StringVar,
    top_status_var: tk.StringVar,
    output_text: scrolledtext.ScrolledText,
    report_state: dict,
    files_container: ctk.CTkScrollableFrame,
) -> None:
    if not report_state.get("stats_text") or not report_state.get("figure"):
        messagebox.showwarning("Atencao", "Execute a analise antes de gerar o PDF.")
        return

    try:
        status_var.set("Gerando PDF...")
        top_status_var.set("Exportando PDF")
        output_text.update_idletasks()
        pdf_path = save_pdf_report(
            report_state["stats_text"],
            report_state["figure"],
            report_state["output_dir"],
        )
        generated_files = list(report_state["generated_files"])
        if pdf_path not in generated_files:
            generated_files.append(pdf_path)
        report_state["generated_files"] = generated_files
        _update_output_text(output_text, report_state["stats_text"], generated_files)
        _refresh_file_cards(files_container, generated_files)
        status_var.set("PDF gerado com sucesso.")
        top_status_var.set("PDF pronto")
        messagebox.showinfo("Sucesso", "PDF gerado com sucesso.")
    except Exception as exc:
        status_var.set("Erro ao gerar PDF.")
        top_status_var.set("Erro")
        print(f"Erro: {exc}", file=sys.stderr)
        messagebox.showerror("Erro", str(exc))


def _apply_responsive_layout(
    root: ctk.CTk,
    shell: ctk.CTkFrame,
    brand_block: ctk.CTkFrame,
    header_meta: ctk.CTkFrame,
    nav_left: ctk.CTkFrame,
    nav_right: ctk.CTkFrame,
    nav_buttons: dict[str, ctk.CTkButton],
    screen_subtitle_label: ctk.CTkLabel,
    execution_screen: ctk.CTkFrame,
    run_card: ctk.CTkFrame,
    run_card_description: ctk.CTkLabel,
    right_stack: ctk.CTkFrame,
    form_grid: ctk.CTkFrame,
    input_label: ctk.CTkLabel,
    input_entry: ctk.CTkEntry,
    input_button: ctk.CTkButton,
    output_label: ctk.CTkLabel,
    output_entry: ctk.CTkEntry,
    output_button: ctk.CTkButton,
    action_row: ctk.CTkFrame,
    quick_run_button: ctk.CTkButton,
    pdf_button: ctk.CTkButton,
    execution_cards: list[ctk.CTkFrame],
    help_panel: ctk.CTkFrame,
    dashboard_metrics_frame: ctk.CTkFrame,
    dashboard_cards: list[ctk.CTkFrame],
    plot_frame: ctk.CTkFrame,
) -> None:
    width = max(root.winfo_width(), root.winfo_reqwidth(), 960)

    shell.pack_configure(
        padx=18 if width < 1100 else 26 if width < 1320 else 34,
        pady=18 if width < 1100 else 22 if width < 1320 else 28,
    )
    _layout_header_blocks(brand_block, header_meta, nav_left, nav_right, width)
    _layout_nav_buttons(nav_right, nav_buttons, width)
    _layout_execution_screen(execution_screen, run_card, right_stack, width)
    _layout_form_grid(
        form_grid,
        input_label,
        input_entry,
        input_button,
        output_label,
        output_entry,
        output_button,
        width,
    )
    _layout_action_row(action_row, quick_run_button, pdf_button, width)
    _layout_dashboard_cards(dashboard_metrics_frame, dashboard_cards, width)

    screen_subtitle_label.configure(wraplength=max(320, min(720, width - 420)))
    run_card_description.configure(wraplength=max(320, min(560, width - 420)))
    for card in execution_cards:
        if hasattr(card, "detail_label"):
            card.detail_label.configure(wraplength=max(220, min(420, width - 760)))
    if hasattr(help_panel, "body_label"):
        help_panel.body_label.configure(wraplength=max(280, min(420, width - 760)))

    # Keep a taller aspect ratio because the dashboard stacks two dense charts.
    plot_height = max(620, min(920, int((width - 120) * 0.62)))
    plot_frame.configure(height=plot_height)


def _create_table_screen(
    parent: ctk.CTkFrame,
    title: str,
    description: str,
) -> tuple[ctk.CTkFrame, ttk.Treeview, ctk.CTkLabel]:
    screen = ctk.CTkFrame(parent, fg_color="transparent")
    card = _create_surface(screen)
    card.pack(fill=tk.BOTH, expand=True)

    ctk.CTkLabel(
        card,
        text=title,
        text_color=TEXT_PRIMARY,
        font=("Segoe UI", 15, "bold"),
    ).pack(anchor="w", padx=20, pady=(18, 6))
    ctk.CTkLabel(
        card,
        text=description,
        text_color=TEXT_MUTED,
        font=("Segoe UI", 11),
    ).pack(anchor="w", padx=20, pady=(0, 14))

    table_outer = ctk.CTkFrame(card, fg_color=FIELD_BG, corner_radius=14)
    table_outer.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 18))
    table_outer.grid_rowconfigure(0, weight=1)
    table_outer.grid_columnconfigure(0, weight=1)

    tree = ttk.Treeview(table_outer, style="Dashboard.Treeview", show="headings")
    y_scroll = ttk.Scrollbar(table_outer, orient="vertical", command=tree.yview)
    x_scroll = ttk.Scrollbar(table_outer, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
    tree.grid(row=0, column=0, sticky="nsew")
    y_scroll.grid(row=0, column=1, sticky="ns")
    x_scroll.grid(row=1, column=0, sticky="ew")

    placeholder = ctk.CTkLabel(
        table_outer,
        text="Execute a analise para carregar esta tela.",
        text_color=TEXT_MUTED,
        font=("Segoe UI", 12),
    )
    placeholder.place(relx=0.5, rely=0.5, anchor="center")
    return screen, tree, placeholder


def main() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    root = ctk.CTk()
    root.title("Salario x Escolaridade - Atividade 05")
    root.geometry("1460x920")
    root.minsize(960, 700)
    root.configure(fg_color=APP_BG)

    _configure_treeview_style(root)

    shell = ctk.CTkFrame(root, fg_color=SHELL_BG, corner_radius=28)
    shell.pack(fill=tk.BOTH, expand=True, padx=34, pady=28)

    top_status_var = tk.StringVar(value="Aguardando execucao")
    screen_title_var = tk.StringVar(value="Execucao")
    screen_subtitle_var = tk.StringVar(
        value="Configure a entrada, dispare a analise e acompanhe o status da rodada."
    )

    top_bar = ctk.CTkFrame(shell, fg_color="transparent")
    top_bar.pack(fill=tk.X, padx=26, pady=(22, 10))

    brand_block = ctk.CTkFrame(top_bar, fg_color="transparent")
    brand_block.pack(side=tk.LEFT)

    brand_line = ctk.CTkFrame(brand_block, fg_color="transparent")
    brand_line.pack(anchor="w")

    ctk.CTkLabel(
        brand_line,
        text="Salário por Escolaridade",
        text_color=TEXT_PRIMARY,
        font=("Segoe UI", 20, "bold"),
    ).pack(side=tk.LEFT)
    screen_subtitle_label = ctk.CTkLabel(
        brand_block,
        textvariable=screen_subtitle_var,
        text_color=TEXT_MUTED,
        font=("Segoe UI", 11),
        justify="left",
        wraplength=640,
    )
    screen_subtitle_label.pack(anchor="w", pady=(4, 0))

    header_meta = ctk.CTkFrame(top_bar, fg_color="transparent")
    header_meta.pack(side=tk.RIGHT)

    header_brand = ctk.CTkFrame(header_meta, fg_color="transparent")
    header_brand.pack(anchor="e")
    ctk.CTkLabel(
        header_brand,
        text="ezequielgean.com.br",
        text_color=TEXT_MUTED,
        font=("Segoe UI", 11),
    ).pack(side=tk.LEFT)

    logo_image = _load_logo_image()
    if logo_image is not None:
        header_logo_label = ctk.CTkLabel(header_brand, text="", image=logo_image)
        header_logo_label.pack(side=tk.LEFT, padx=(8, 0))
        _bind_responsive_logo(root, header_logo_label, logo_image)

    status_chip = ctk.CTkFrame(header_meta, fg_color=CARD_BG, corner_radius=16, border_width=1, border_color=BORDER_COLOR)
    status_chip.pack(anchor="e", pady=(8, 0))
    ctk.CTkLabel(
        status_chip,
        text="status",
        text_color=TEXT_SOFT,
        font=("Segoe UI", 10),
    ).pack(side=tk.LEFT, padx=(12, 6), pady=6)
    ctk.CTkLabel(
        status_chip,
        textvariable=top_status_var,
        text_color=SUCCESS,
        font=("Segoe UI", 10, "bold"),
    ).pack(side=tk.LEFT, padx=(0, 12), pady=6)

    nav_bar = ctk.CTkFrame(shell, fg_color="transparent")
    nav_bar.pack(fill=tk.X, padx=26, pady=(0, 14))

    nav_left = ctk.CTkFrame(nav_bar, fg_color="transparent")
    nav_left.pack(side=tk.LEFT)
    ctk.CTkLabel(
        nav_left,
        textvariable=screen_title_var,
        text_color=TEXT_PRIMARY,
        font=("Segoe UI", 15, "bold"),
    ).pack(anchor="w")

    nav_right = ctk.CTkFrame(nav_bar, fg_color="transparent")
    nav_right.pack(side=tk.RIGHT)

    content_container = ctk.CTkFrame(shell, fg_color="transparent")
    content_container.pack(fill=tk.BOTH, expand=True, padx=26, pady=(0, 26))

    screens: dict[str, ctk.CTkFrame] = {}
    nav_buttons: dict[str, ctk.CTkButton] = {}
    report_state: dict = {}

    execution_vars = {
        "status_value": tk.StringVar(),
        "status_detail": tk.StringVar(),
        "premium_value": tk.StringVar(),
        "premium_detail": tk.StringVar(),
        "leader_value": tk.StringVar(),
        "leader_detail": tk.StringVar(),
        "coverage_value": tk.StringVar(),
        "coverage_detail": tk.StringVar(),
    }
    _update_execution_cards(execution_vars)

    dashboard_vars = {
        "obs_value": tk.StringVar(),
        "obs_detail": tk.StringVar(),
        "premium_value": tk.StringVar(),
        "premium_detail": tk.StringVar(),
        "leader_value": tk.StringVar(),
        "leader_detail": tk.StringVar(),
        "floor_value": tk.StringVar(),
        "floor_detail": tk.StringVar(),
    }
    _update_dashboard_cards(dashboard_vars)

    execution_screen = ctk.CTkFrame(content_container, fg_color="transparent")
    execution_screen.grid_columnconfigure(0, weight=1)
    execution_screen.grid_columnconfigure(1, weight=1)
    execution_screen.grid_rowconfigure(0, weight=1)

    run_card = _create_surface(execution_screen)
    run_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
    ctk.CTkLabel(
        run_card,
        text="Executar a atividade",
        text_color=TEXT_PRIMARY,
        font=("Segoe UI", 16, "bold"),
    ).pack(anchor="w", padx=22, pady=(20, 6))
    run_card_description = ctk.CTkLabel(
        run_card,
        text="A tela de execucao concentra arquivo de entrada, pasta de saida e os comandos da rodada.",
        text_color=TEXT_MUTED,
        font=("Segoe UI", 11),
        justify="left",
        wraplength=480,
    )
    run_card_description.pack(anchor="w", padx=22, pady=(0, 16))

    form_grid = ctk.CTkFrame(run_card, fg_color="transparent")
    form_grid.pack(fill=tk.X, padx=22, pady=(0, 10))
    form_grid.grid_columnconfigure(1, weight=1)

    input_label = ctk.CTkLabel(
        form_grid,
        text="Arquivo JSON",
        text_color=TEXT_PRIMARY,
        font=("Segoe UI", 11, "bold"),
    )
    input_label.grid(row=0, column=0, sticky="w", padx=(0, 12), pady=(0, 8))
    input_entry = ctk.CTkEntry(
        form_grid,
        fg_color=FIELD_BG,
        text_color=TEXT_PRIMARY,
        border_color=BORDER_COLOR,
        corner_radius=12,
        height=40,
    )
    input_entry.insert(0, str(DEFAULT_INPUT))
    input_entry.grid(row=0, column=1, sticky="ew", pady=(0, 8))
    input_browse_button = ctk.CTkButton(
        form_grid,
        text="Buscar",
        fg_color=GHOST_BG,
        hover_color=GHOST_HOVER,
        text_color=TEXT_PRIMARY,
        corner_radius=12,
        border_width=1,
        border_color=BORDER_COLOR,
        width=110,
        command=lambda: _select_file(input_entry),
    )
    input_browse_button.grid(row=0, column=2, padx=(12, 0), pady=(0, 8))

    output_label = ctk.CTkLabel(
        form_grid,
        text="Pasta de saida",
        text_color=TEXT_PRIMARY,
        font=("Segoe UI", 11, "bold"),
    )
    output_label.grid(row=1, column=0, sticky="w", padx=(0, 12), pady=(10, 0))
    output_entry = ctk.CTkEntry(
        form_grid,
        fg_color=FIELD_BG,
        text_color=TEXT_PRIMARY,
        border_color=BORDER_COLOR,
        corner_radius=12,
        height=40,
    )
    output_entry.insert(0, str(DEFAULT_OUTPUT_DIR))
    output_entry.grid(row=1, column=1, sticky="ew", pady=(10, 0))
    output_browse_button = ctk.CTkButton(
        form_grid,
        text="Pasta",
        fg_color=GHOST_BG,
        hover_color=GHOST_HOVER,
        text_color=TEXT_PRIMARY,
        corner_radius=12,
        border_width=1,
        border_color=BORDER_COLOR,
        width=110,
        command=lambda: _select_folder(output_entry),
    )
    output_browse_button.grid(row=1, column=2, padx=(12, 0), pady=(10, 0))

    status_var = tk.StringVar(value="Pronto para executar.")
    status_panel = ctk.CTkFrame(run_card, fg_color=CARD_ALT, corner_radius=14)
    status_panel.pack(fill=tk.X, padx=22, pady=(14, 0))
    ctk.CTkLabel(
        status_panel,
        text="Fluxo",
        text_color=TEXT_SOFT,
        font=("Segoe UI", 10),
    ).pack(anchor="w", padx=16, pady=(12, 2))
    ctk.CTkLabel(
        status_panel,
        textvariable=status_var,
        text_color=TEXT_PRIMARY,
        font=("Segoe UI", 11, "bold"),
        justify="left",
        wraplength=480,
    ).pack(anchor="w", padx=16, pady=(0, 12))

    action_row = ctk.CTkFrame(run_card, fg_color="transparent")
    action_row.pack(fill=tk.X, padx=22, pady=(18, 22))

    pdf_button = ctk.CTkButton(
        action_row,
        text="Gerar PDF",
        fg_color=GHOST_BG,
        hover_color=GHOST_HOVER,
        text_color=TEXT_PRIMARY,
        border_width=1,
        border_color=BORDER_COLOR,
        corner_radius=14,
        width=140,
        state="disabled",
    )
    pdf_button.pack(side=tk.RIGHT)

    quick_run_button = ctk.CTkButton(
        action_row,
        text="Executar Analise",
        fg_color=ACCENT,
        hover_color=ACCENT_HOVER,
        text_color="#111111",
        corner_radius=14,
        width=170,
    )
    quick_run_button.pack(side=tk.RIGHT, padx=(0, 10))

    right_stack = ctk.CTkFrame(execution_screen, fg_color="transparent")
    right_stack.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
    right_stack.grid_columnconfigure(0, weight=1)

    card_status = _create_stat_card(
        right_stack,
        "Rodada",
        execution_vars["status_value"],
        execution_vars["status_detail"],
        SECONDARY,
    )
    card_status.pack(fill=tk.X, pady=(0, 12))

    card_premium = _create_stat_card(
        right_stack,
        "Premio medio",
        execution_vars["premium_value"],
        execution_vars["premium_detail"],
        ACCENT,
    )
    card_premium.pack(fill=tk.X, pady=(0, 12))

    card_leader = _create_stat_card(
        right_stack,
        "Estado lider",
        execution_vars["leader_value"],
        execution_vars["leader_detail"],
        SECONDARY,
    )
    card_leader.pack(fill=tk.X, pady=(0, 12))

    card_coverage = _create_stat_card(
        right_stack,
        "Cobertura",
        execution_vars["coverage_value"],
        execution_vars["coverage_detail"],
        ACCENT,
    )
    card_coverage.pack(fill=tk.X, pady=(0, 12))
    execution_cards = [card_status, card_premium, card_leader, card_coverage]

    help_panel = _create_info_panel(
        right_stack,
        "Como navegar",
        "1. Rode a analise em Execucao.\n2. Use Dashboard para a visao sintetica.\n3. Abra Resumo, Regressoes, Medias e Arquivos pelo menu superior.",
    )
    help_panel.pack(fill=tk.X)
    screens["execution"] = execution_screen

    dashboard_screen = ctk.CTkScrollableFrame(content_container, fg_color="transparent")
    dashboard_card = _create_surface(dashboard_screen)
    dashboard_card.pack(fill=tk.X, expand=True)
    ctk.CTkLabel(
        dashboard_card,
        text="Painel Analitico",
        text_color=TEXT_PRIMARY,
        font=("Segoe UI", 16, "bold"),
    ).pack(anchor="w", padx=20, pady=(18, 4))
    ctk.CTkLabel(
        dashboard_card,
        text="Os indicadores ficam fora do canvas para reduzir sobreposicao e melhorar a leitura em qualquer largura.",
        text_color=TEXT_MUTED,
        font=("Segoe UI", 11),
    ).pack(anchor="w", padx=20, pady=(0, 14))
    dashboard_metrics_frame = ctk.CTkFrame(dashboard_card, fg_color="transparent")
    dashboard_metrics_frame.pack(fill=tk.X, padx=18, pady=(0, 12))
    dashboard_cards = [
        _create_stat_card(
            dashboard_metrics_frame,
            "Observacoes",
            dashboard_vars["obs_value"],
            dashboard_vars["obs_detail"],
            SECONDARY,
        ),
        _create_stat_card(
            dashboard_metrics_frame,
            "Premio medio",
            dashboard_vars["premium_value"],
            dashboard_vars["premium_detail"],
            ACCENT,
        ),
        _create_stat_card(
            dashboard_metrics_frame,
            "Maior premio",
            dashboard_vars["leader_value"],
            dashboard_vars["leader_detail"],
            ACCENT,
        ),
        _create_stat_card(
            dashboard_metrics_frame,
            "Menor premio",
            dashboard_vars["floor_value"],
            dashboard_vars["floor_detail"],
            SECONDARY,
        ),
    ]
    plot_frame = ctk.CTkFrame(dashboard_card, fg_color=FIELD_BG, corner_radius=18)
    plot_frame.pack(fill=tk.X, padx=18, pady=(0, 18))
    plot_frame.pack_propagate(False)
    plot_frame.canvas = None
    ctk.CTkLabel(
        plot_frame,
        text="O dashboard aparecera aqui apos a execucao.",
        text_color=TEXT_MUTED,
        font=("Segoe UI", 12),
    ).pack(expand=True)
    screens["dashboard"] = dashboard_screen

    summary_screen = ctk.CTkFrame(content_container, fg_color="transparent")
    summary_card = _create_surface(summary_screen)
    summary_card.pack(fill=tk.BOTH, expand=True)
    ctk.CTkLabel(
        summary_card,
        text="Resumo da Execucao",
        text_color=TEXT_PRIMARY,
        font=("Segoe UI", 16, "bold"),
    ).pack(anchor="w", padx=20, pady=(18, 6))
    output_text = scrolledtext.ScrolledText(
        summary_card,
        wrap=tk.WORD,
        background=FIELD_BG,
        foreground=TEXT_PRIMARY,
        insertbackground=TEXT_PRIMARY,
        relief=tk.FLAT,
        font=("Consolas", 10),
    )
    output_text.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 18))
    output_text.insert(
        tk.END,
        "Execute a analise para preencher esta tela com o resumo economico e estatistico.\n",
    )
    output_text.configure(state="disabled")
    screens["summary"] = summary_screen

    regressions_screen, regressions_tree, regressions_placeholder = _create_table_screen(
        content_container,
        "Coeficientes por Estado",
        "Leitura direta do intercepto, premio salarial e percentuais associados ao ensino superior.",
    )
    screens["regressions"] = regressions_screen

    means_screen, means_tree, means_placeholder = _create_table_screen(
        content_container,
        "Medias por Grupo",
        "Tabela consolidada com medias, medianas e dispersao entre grupos de escolaridade.",
    )
    screens["means"] = means_screen

    files_screen = ctk.CTkFrame(content_container, fg_color="transparent")
    files_card = _create_surface(files_screen)
    files_card.pack(fill=tk.BOTH, expand=True)
    ctk.CTkLabel(
        files_card,
        text="Arquivos Gerados",
        text_color=TEXT_PRIMARY,
        font=("Segoe UI", 16, "bold"),
    ).pack(anchor="w", padx=20, pady=(18, 6))
    ctk.CTkLabel(
        files_card,
        text="Cada rodada atualiza a lista abaixo com os artefatos disponiveis para uso externo.",
        text_color=TEXT_MUTED,
        font=("Segoe UI", 11),
    ).pack(anchor="w", padx=20, pady=(0, 14))
    files_container = ctk.CTkScrollableFrame(files_card, fg_color=FIELD_BG, corner_radius=16)
    files_container.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 18))
    _refresh_file_cards(files_container, [])
    screens["files"] = files_screen

    for key, label in NAV_ITEMS:
        button = ctk.CTkButton(
            nav_right,
            text=label,
            fg_color="transparent",
            hover_color=GHOST_HOVER,
            text_color=TEXT_MUTED,
            border_width=1,
            border_color=BORDER_COLOR,
            corner_radius=18,
            width=112,
            height=36,
            command=lambda current=key: _show_screen(
                current,
                screens,
                nav_buttons,
                screen_title_var,
                screen_subtitle_var,
            ),
        )
        nav_buttons[key] = button

    quick_run_button.configure(
        command=lambda: _execute_from_gui(
            input_entry,
            output_entry,
            status_var,
            top_status_var,
            output_text,
            plot_frame,
            regressions_tree,
            regressions_placeholder,
            means_tree,
            means_placeholder,
            files_container,
            screens,
            nav_buttons,
            screen_title_var,
            screen_subtitle_var,
            report_state,
            pdf_button,
            execution_vars,
            dashboard_vars,
        )
    )

    pdf_button.configure(
        command=lambda: _generate_pdf_from_gui(
            status_var,
            top_status_var,
            output_text,
            report_state,
            files_container,
        )
    )

    def on_resize(event: tk.Event | None = None) -> None:
        if event is not None and event.widget is not root:
            return
        _apply_responsive_layout(
            root,
            shell,
            brand_block,
            header_meta,
            nav_left,
            nav_right,
            nav_buttons,
            screen_subtitle_label,
            execution_screen,
            run_card,
            run_card_description,
            right_stack,
            form_grid,
            input_label,
            input_entry,
            input_browse_button,
            output_label,
            output_entry,
            output_browse_button,
            action_row,
            quick_run_button,
            pdf_button,
            execution_cards,
            help_panel,
            dashboard_metrics_frame,
            dashboard_cards,
            plot_frame,
        )

    root.bind("<Configure>", on_resize, add="+")
    on_resize()

    _show_screen("execution", screens, nav_buttons, screen_title_var, screen_subtitle_var)
    root.mainloop()


if __name__ == "__main__":
    main()
