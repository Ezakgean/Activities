from __future__ import annotations

import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd

from .analise import DEFAULT_INPUT, DEFAULT_OUTPUT_DIR, format_percent, run_pipeline, save_pdf_report


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
SECONDARY = "#2a6f97"
SECONDARY_HOVER = "#3182bd"
GHOST_BG = "#2a2b2e"
GHOST_HOVER = "#33353a"
SUCCESS = "#f5821f"
TABLE_BAND_A = "#17181a"
TABLE_BAND_B = "#1b1d20"

NAV_ITEMS = [
    ("execution", "Execucao"),
    ("dashboard", "Dashboard"),
    ("summary", "Resumo"),
    ("predictions", "Previsoes"),
    ("confusion", "Matriz"),
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
    state = {"last_scale": None}

    def on_resize(event: tk.Event | None = None) -> None:
        width = root.winfo_width() or 1360
        target_height = max(32, min(52, int(width * 0.034)))
        original_height = max(1, logo_image.height())
        scale = max(1, int(original_height / target_height))
        if scale == state["last_scale"]:
            return
        state["last_scale"] = scale
        scaled = logo_image.subsample(scale, scale)
        logo_label.configure(image=scaled)
        logo_label.image = scaled

    root.bind("<Configure>", on_resize, add="+")
    on_resize()


def _bind_debounced_layout(root: ctk.CTk, apply_layout) -> None:
    state = {"pending": None, "last_width": None}

    def flush() -> None:
        state["pending"] = None
        width = max(root.winfo_width(), root.winfo_reqwidth(), 960)
        if width == state["last_width"]:
            return
        state["last_width"] = width
        apply_layout()

    def on_resize(event: tk.Event | None = None) -> None:
        if state["pending"] is not None:
            root.after_cancel(state["pending"])
        state["pending"] = root.after(16, flush)

    root.bind("<Configure>", on_resize, add="+")
    on_resize()


def _select_file(entry: ctk.CTkEntry) -> None:
    filename = filedialog.askopenfilename(
        title="Selecione o arquivo de frases",
        filetypes=[("Texto e CSV", "*.txt *.csv"), ("Todos", "*")],
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
            "Selecione o arquivo de frases, rode a classificacao e acompanhe o status da rodada.",
        ),
        "dashboard": (
            "Dashboard",
            "Painel sintetico com distribuicao de classes, matriz de confusao e recall por emocao.",
        ),
        "summary": (
            "Resumo",
            "Leitura textual consolidada com metrica de teste, distribuicao prevista e sinais por classe.",
        ),
        "predictions": (
            "Previsoes",
            "Tabela com frase original, emocao prevista, confianca e tokens normalizados.",
        ),
        "confusion": (
            "Matriz",
            "Tabela da matriz de confusao do conjunto de teste, no padrao esperado x previsto.",
        ),
        "files": (
            "Arquivos",
            "Inventario dos artefatos exportados pela rodada atual.",
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
    tree.tag_configure("band_0", background=TABLE_BAND_A, foreground=TEXT_PRIMARY)
    tree.tag_configure("band_1", background=TABLE_BAND_B, foreground=TEXT_PRIMARY)

    for column in columns:
        lowered = column.lower()
        anchor = tk.W if any(
            key in lowered for key in ["frase", "token", "arquivo", "caminho", "esperado", "previsto"]
        ) else tk.CENTER
        width = 120
        if "frase" in lowered:
            width = 360
        elif "token" in lowered:
            width = 320
        elif "arquivo" in lowered or "caminho" in lowered:
            width = 320
        elif "confianca" in lowered:
            width = 130

        tree.heading(column, text=column)
        tree.column(column, width=width, minwidth=90, stretch=True, anchor=anchor)

    for row_index, row in enumerate(dataframe.itertuples(index=False, name=None)):
        values = ["" if pd.isna(value) else str(value) for value in row]
        tree.insert("", tk.END, values=values, tags=(f"band_{row_index % 2}",))


def _format_predictions_for_view(predictions_df: pd.DataFrame) -> pd.DataFrame:
    if predictions_df.empty:
        return predictions_df

    view = predictions_df.copy()
    view["confianca"] = view["confianca"].map(lambda value: format_percent(float(value)))
    view["confianca_secundaria"] = view["confianca_secundaria"].map(
        lambda value: format_percent(float(value))
    )
    return view.rename(
        columns={
            "frase": "Frase",
            "emocao_prevista": "Prevista",
            "confianca": "Confianca",
            "emocao_secundaria": "Secundaria",
            "confianca_secundaria": "Conf. secundaria",
            "tokens_normalizados": "Tokens",
        }
    )


def _format_confusion_for_view(confusion_df: pd.DataFrame) -> pd.DataFrame:
    if confusion_df.empty:
        return confusion_df

    view = confusion_df.copy().reset_index()
    view = view.rename(columns={"index": "Esperado"})
    return view.rename(
        columns={
            "alegria": "Prev. alegria",
            "desgosto": "Prev. desgosto",
            "medo": "Prev. medo",
            "tristeza": "Prev. tristeza",
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


def _update_output_text(output_text: scrolledtext.ScrolledText, stats_text: str) -> None:
    output_text.configure(state="normal")
    output_text.delete("1.0", tk.END)
    output_text.insert(tk.END, stats_text)
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
    result=None,
) -> None:
    if result is None:
        execution_vars["status_value"].set("Aguardando")
        execution_vars["status_detail"].set("Sem execucao concluida nesta sessao.")
        execution_vars["accuracy_value"].set("--")
        execution_vars["accuracy_detail"].set("Acuracia de teste e baseline aparecem apos a rodada.")
        execution_vars["leader_value"].set("--")
        execution_vars["leader_detail"].set("Classe dominante nas previsoes do arquivo.")
        execution_vars["coverage_value"].set("0 frases")
        execution_vars["coverage_detail"].set("Volume classificado na rodada atual.")
        return

    prediction_counts = result.predictions_df["emocao_prevista"].value_counts()
    leader_label = prediction_counts.index[0] if not prediction_counts.empty else "--"
    leader_count = int(prediction_counts.iloc[0]) if not prediction_counts.empty else 0

    execution_vars["status_value"].set("Concluida")
    execution_vars["status_detail"].set("A rodada gerou dashboard, tabelas CSV, resumo e matriz de confusao.")
    execution_vars["accuracy_value"].set(format_percent(result.accuracy))
    execution_vars["accuracy_detail"].set(f"Baseline majoritaria: {format_percent(result.baseline_accuracy)}")
    execution_vars["leader_value"].set(leader_label.capitalize())
    execution_vars["leader_detail"].set(f"{leader_count} frases com maior volume previsto.")
    execution_vars["coverage_value"].set(f"{result.input_count} frases")
    execution_vars["coverage_detail"].set(f"{len(result.labels)} classes modeladas na atividade.")


def _update_dashboard_cards(
    dashboard_vars: dict[str, tk.StringVar],
    result=None,
) -> None:
    if result is None:
        dashboard_vars["training_value"].set("--")
        dashboard_vars["training_detail"].set("Base de treinamento consolidada.")
        dashboard_vars["accuracy_value"].set("--")
        dashboard_vars["accuracy_detail"].set("Desempenho do conjunto de teste.")
        dashboard_vars["leader_value"].set("--")
        dashboard_vars["leader_detail"].set("Classe dominante na rodada.")
        dashboard_vars["confidence_value"].set("--")
        dashboard_vars["confidence_detail"].set("Menor confianca observada nas previsoes.")
        return

    metrics = result.metrics_df.iloc[0]
    prediction_counts = result.predictions_df["emocao_prevista"].value_counts()
    leader_label = prediction_counts.index[0] if not prediction_counts.empty else "--"
    leader_count = int(prediction_counts.iloc[0]) if not prediction_counts.empty else 0
    lowest_confidence = float(result.predictions_df["confianca"].min()) if not result.predictions_df.empty else 0.0

    dashboard_vars["training_value"].set(f"{int(metrics['frases_treinamento'])} frases")
    dashboard_vars["training_detail"].set(
        f"Teste: {int(metrics['frases_teste'])} | Vocabulario: {int(metrics['tamanho_vocabulario'])}"
    )
    dashboard_vars["accuracy_value"].set(format_percent(result.accuracy))
    dashboard_vars["accuracy_detail"].set(f"Baseline: {format_percent(result.baseline_accuracy)}")
    dashboard_vars["leader_value"].set(f"{leader_label.capitalize()} | {leader_count}")
    dashboard_vars["leader_detail"].set("Classe com maior volume previsto no arquivo.")
    dashboard_vars["confidence_value"].set(format_percent(lowest_confidence))
    dashboard_vars["confidence_detail"].set("Menor confianca entre todas as frases classificadas.")


def _execute_from_gui(
    input_entry: ctk.CTkEntry,
    output_entry: ctk.CTkEntry,
    status_var: tk.StringVar,
    top_status_var: tk.StringVar,
    output_text: scrolledtext.ScrolledText,
    plot_frame: ctk.CTkFrame,
    predictions_tree: ttk.Treeview,
    predictions_placeholder: ctk.CTkLabel,
    confusion_tree: ttk.Treeview,
    confusion_placeholder: ctk.CTkLabel,
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
        messagebox.showerror("Erro", "Selecione um arquivo TXT ou CSV.")
        return

    if not output_dir_raw:
        messagebox.showerror("Erro", "Selecione uma pasta de saida.")
        return

    try:
        pdf_button.configure(state="disabled")
        status_var.set("Classificando frases e montando artefatos...")
        top_status_var.set("Executando")
        output_text.update_idletasks()

        result = run_pipeline(Path(input_path_raw), Path(output_dir_raw))
        generated_files = [
            result.summary_path,
            result.predictions_path,
            result.confusion_path,
            result.errors_path,
            result.metrics_path,
            result.dashboard_path,
        ]

        report_state.clear()
        report_state.update(
            {
                "summary_text": result.summary_text,
                "figure": result.figure,
                "output_dir": result.output_dir,
                "generated_files": generated_files,
            }
        )

        _update_execution_cards(execution_vars, result)
        _update_dashboard_cards(dashboard_vars, result)
        _update_output_text(output_text, result.summary_text)
        _update_dashboard(plot_frame, result.figure)
        _populate_treeview(
            predictions_tree,
            _format_predictions_for_view(result.predictions_df),
            predictions_placeholder,
        )
        _populate_treeview(
            confusion_tree,
            _format_confusion_for_view(result.confusion_df),
            confusion_placeholder,
        )
        _refresh_file_cards(files_container, generated_files)

        status_var.set("Execucao concluida. Use o menu superior para navegar pelas telas.")
        top_status_var.set("Concluida")
        pdf_button.configure(state="normal")
        _show_screen("dashboard", screens, nav_buttons, screen_title_var, screen_subtitle_var)
        messagebox.showinfo("Sucesso", "A atividade 07 foi executada com sucesso.")
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
    if not report_state.get("summary_text") or not report_state.get("figure"):
        messagebox.showwarning("Atencao", "Execute a analise antes de gerar o PDF.")
        return

    try:
        status_var.set("Gerando PDF...")
        top_status_var.set("Exportando PDF")
        output_text.update_idletasks()
        pdf_path = save_pdf_report(
            report_state["summary_text"],
            report_state["figure"],
            report_state["output_dir"],
        )
        generated_files = list(report_state["generated_files"])
        if pdf_path not in generated_files:
            generated_files.append(pdf_path)
        report_state["generated_files"] = generated_files
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
    root.title("Mineracao de Emocao - Atividade 07")
    root.geometry("1460x920")
    root.minsize(960, 700)
    root.configure(fg_color=APP_BG)

    _configure_treeview_style(root)

    shell = ctk.CTkFrame(root, fg_color=SHELL_BG, corner_radius=28)
    shell.pack(fill=tk.BOTH, expand=True, padx=34, pady=28)

    top_status_var = tk.StringVar(value="Aguardando execucao")
    screen_title_var = tk.StringVar(value="Execucao")
    screen_subtitle_var = tk.StringVar(
        value="Selecione o arquivo de frases, rode a classificacao e acompanhe o status da rodada."
    )

    top_bar = ctk.CTkFrame(shell, fg_color="transparent")
    top_bar.pack(fill=tk.X, padx=26, pady=(22, 10))

    brand_block = ctk.CTkFrame(top_bar, fg_color="transparent")
    brand_block.pack(side=tk.LEFT)

    brand_line = ctk.CTkFrame(brand_block, fg_color="transparent")
    brand_line.pack(anchor="w")

    ctk.CTkLabel(
        brand_line,
        text="Mineracao de Emocao",
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

    status_chip = ctk.CTkFrame(
        header_meta,
        fg_color=CARD_BG,
        corner_radius=16,
        border_width=1,
        border_color=BORDER_COLOR,
    )
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
        "accuracy_value": tk.StringVar(),
        "accuracy_detail": tk.StringVar(),
        "leader_value": tk.StringVar(),
        "leader_detail": tk.StringVar(),
        "coverage_value": tk.StringVar(),
        "coverage_detail": tk.StringVar(),
    }
    _update_execution_cards(execution_vars)

    dashboard_vars = {
        "training_value": tk.StringVar(),
        "training_detail": tk.StringVar(),
        "accuracy_value": tk.StringVar(),
        "accuracy_detail": tk.StringVar(),
        "leader_value": tk.StringVar(),
        "leader_detail": tk.StringVar(),
        "confidence_value": tk.StringVar(),
        "confidence_detail": tk.StringVar(),
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
        text="A execucao concentra arquivo de entrada, pasta de saida e os comandos da rodada.",
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
        text="Arquivo TXT ou CSV",
        text_color=TEXT_PRIMARY,
        font=("Segoe UI", 11, "bold"),
    )
    input_entry = ctk.CTkEntry(
        form_grid,
        fg_color=FIELD_BG,
        text_color=TEXT_PRIMARY,
        border_color=BORDER_COLOR,
        corner_radius=12,
        height=40,
    )
    input_entry.insert(0, str(DEFAULT_INPUT))
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

    output_label = ctk.CTkLabel(
        form_grid,
        text="Pasta de saida",
        text_color=TEXT_PRIMARY,
        font=("Segoe UI", 11, "bold"),
    )
    output_entry = ctk.CTkEntry(
        form_grid,
        fg_color=FIELD_BG,
        text_color=TEXT_PRIMARY,
        border_color=BORDER_COLOR,
        corner_radius=12,
        height=40,
    )
    output_entry.insert(0, str(DEFAULT_OUTPUT_DIR))
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

    spec_panel = ctk.CTkFrame(run_card, fg_color=CARD_ALT, corner_radius=14)
    spec_panel.pack(fill=tk.X, padx=22, pady=(14, 0))
    ctk.CTkLabel(
        spec_panel,
        text="Formato esperado",
        text_color=TEXT_PRIMARY,
        font=("Segoe UI", 11, "bold"),
    ).pack(anchor="w", padx=16, pady=(12, 2))
    ctk.CTkLabel(
        spec_panel,
        text="TXT: uma frase por linha. CSV: use a coluna 'frase' ou deixe a frase na primeira coluna.",
        text_color=TEXT_MUTED,
        font=("Segoe UI", 10),
        justify="left",
        wraplength=500,
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

    quick_run_button = ctk.CTkButton(
        action_row,
        text="Executar Analise",
        fg_color=ACCENT,
        hover_color=ACCENT_HOVER,
        text_color="#111111",
        corner_radius=14,
        width=170,
    )

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

    card_accuracy = _create_stat_card(
        right_stack,
        "Acuracia",
        execution_vars["accuracy_value"],
        execution_vars["accuracy_detail"],
        ACCENT,
    )
    card_accuracy.pack(fill=tk.X, pady=(0, 12))

    card_leader = _create_stat_card(
        right_stack,
        "Classe dominante",
        execution_vars["leader_value"],
        execution_vars["leader_detail"],
        SECONDARY,
    )
    card_leader.pack(fill=tk.X, pady=(0, 12))

    card_coverage = _create_stat_card(
        right_stack,
        "Volume",
        execution_vars["coverage_value"],
        execution_vars["coverage_detail"],
        ACCENT,
    )
    card_coverage.pack(fill=tk.X, pady=(0, 12))
    execution_cards = [card_status, card_accuracy, card_leader, card_coverage]

    help_panel = _create_info_panel(
        right_stack,
        "Como navegar",
        "1. Rode a classificacao em Execucao.\n2. Use Dashboard para a visao sintetica.\n3. Abra Resumo, Previsoes, Matriz e Arquivos pelo menu superior.",
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
        text="Os indicadores ficam fora do canvas para manter a leitura limpa em qualquer largura.",
        text_color=TEXT_MUTED,
        font=("Segoe UI", 11),
    ).pack(anchor="w", padx=20, pady=(0, 14))
    dashboard_metrics_frame = ctk.CTkFrame(dashboard_card, fg_color="transparent")
    dashboard_metrics_frame.pack(fill=tk.X, padx=18, pady=(0, 12))
    dashboard_cards = [
        _create_stat_card(
            dashboard_metrics_frame,
            "Treinamento",
            dashboard_vars["training_value"],
            dashboard_vars["training_detail"],
            SECONDARY,
        ),
        _create_stat_card(
            dashboard_metrics_frame,
            "Acuracia",
            dashboard_vars["accuracy_value"],
            dashboard_vars["accuracy_detail"],
            ACCENT,
        ),
        _create_stat_card(
            dashboard_metrics_frame,
            "Classe dominante",
            dashboard_vars["leader_value"],
            dashboard_vars["leader_detail"],
            SECONDARY,
        ),
        _create_stat_card(
            dashboard_metrics_frame,
            "Menor confianca",
            dashboard_vars["confidence_value"],
            dashboard_vars["confidence_detail"],
            ACCENT,
        ),
    ]
    _layout_dashboard_cards(dashboard_metrics_frame, dashboard_cards, 1460)

    plot_frame = ctk.CTkFrame(dashboard_card, fg_color=FIELD_BG, corner_radius=18, height=680)
    plot_frame.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 18))
    plot_frame.pack_propagate(False)
    plot_frame.canvas = None
    screens["dashboard"] = dashboard_screen

    summary_screen = ctk.CTkFrame(content_container, fg_color="transparent")
    summary_card = _create_surface(summary_screen)
    summary_card.pack(fill=tk.BOTH, expand=True)
    ctk.CTkLabel(
        summary_card,
        text="Resumo Interpretativo",
        text_color=TEXT_PRIMARY,
        font=("Segoe UI", 15, "bold"),
    ).pack(anchor="w", padx=20, pady=(18, 6))
    ctk.CTkLabel(
        summary_card,
        text="O resumo consolida metricas, sinais por classe e a matriz de confusao textual.",
        text_color=TEXT_MUTED,
        font=("Segoe UI", 11),
    ).pack(anchor="w", padx=20, pady=(0, 14))
    output_text = scrolledtext.ScrolledText(
        summary_card,
        wrap=tk.WORD,
        background=FIELD_BG,
        foreground=TEXT_PRIMARY,
        insertbackground=TEXT_PRIMARY,
        relief="flat",
        bd=0,
        font=("Consolas", 10),
    )
    output_text.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 18))
    output_text.configure(state="disabled")
    screens["summary"] = summary_screen

    predictions_screen, predictions_tree, predictions_placeholder = _create_table_screen(
        content_container,
        "Tabela de Previsoes",
        "Cada linha mostra a frase original, a emocao prevista, a confianca e os tokens normalizados.",
    )
    screens["predictions"] = predictions_screen

    confusion_screen, confusion_tree, confusion_placeholder = _create_table_screen(
        content_container,
        "Matriz de Confusao",
        "Linhas representam a emocao esperada no conjunto de teste e colunas representam a emocao prevista.",
    )
    screens["confusion"] = confusion_screen

    files_screen = ctk.CTkFrame(content_container, fg_color="transparent")
    files_card = _create_surface(files_screen)
    files_card.pack(fill=tk.BOTH, expand=True)
    ctk.CTkLabel(
        files_card,
        text="Arquivos Gerados",
        text_color=TEXT_PRIMARY,
        font=("Segoe UI", 15, "bold"),
    ).pack(anchor="w", padx=20, pady=(18, 6))
    ctk.CTkLabel(
        files_card,
        text="A rodada exporta resumo, previsoes, matriz, erros, metricas, dashboard e PDF opcional.",
        text_color=TEXT_MUTED,
        font=("Segoe UI", 11),
    ).pack(anchor="w", padx=20, pady=(0, 14))
    files_container = ctk.CTkScrollableFrame(files_card, fg_color="transparent")
    files_container.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 18))
    _refresh_file_cards(files_container, [])
    screens["files"] = files_screen

    for key, label in NAV_ITEMS:
        nav_buttons[key] = ctk.CTkButton(
            nav_right,
            text=label,
            fg_color="transparent",
            hover_color=GHOST_HOVER,
            text_color=TEXT_MUTED,
            border_width=1,
            border_color=BORDER_COLOR,
            corner_radius=14,
            command=lambda screen_name=key: _show_screen(
                screen_name,
                screens,
                nav_buttons,
                screen_title_var,
                screen_subtitle_var,
            ),
        )

    quick_run_button.configure(
        command=lambda: _execute_from_gui(
            input_entry,
            output_entry,
            status_var,
            top_status_var,
            output_text,
            plot_frame,
            predictions_tree,
            predictions_placeholder,
            confusion_tree,
            confusion_placeholder,
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

    def _on_resize() -> None:
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

    _show_screen("execution", screens, nav_buttons, screen_title_var, screen_subtitle_var)
    _bind_debounced_layout(root, _on_resize)
    root.mainloop()


if __name__ == "__main__":
    main()
