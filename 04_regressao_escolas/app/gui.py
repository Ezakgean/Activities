from __future__ import annotations

import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from .regressao import DEFAULT_INPUT, DEFAULT_OUTPUT_DIR, run_pipeline, save_pdf_report


BACKGROUND = "#0f0f10"
PANEL_BG = "#141516"
FIELD_BG = "#17181a"
TEXT_PRIMARY = "#f7f7f7"
TEXT_MUTED = "#9aa0a6"
TEXT_BODY = "#eaeaea"
BUTTON_PRIMARY = "#f5821f"
BUTTON_PRIMARY_HOVER = "#ff8c33"
BUTTON_SECONDARY = "#2a2b2e"
BUTTON_SECONDARY_HOVER = "#33353a"


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
        width = root.winfo_width() or 980
        target_height = max(24, min(48, int(width * 0.06)))
        original_height = max(1, logo_image.height())
        scale = max(1, int(original_height / target_height))
        scaled = logo_image.subsample(scale, scale)
        logo_label.configure(image=scaled)
        logo_label.image = scaled

    root.bind("<Configure>", on_resize)
    on_resize()


def _select_file(entry: ctk.CTkEntry) -> None:
    filename = filedialog.askopenfilename(
        title="Selecione a planilha Excel",
        filetypes=[("Excel", "*.xlsx *.xls"), ("Todos", "*")],
    )
    if filename:
        entry.delete(0, tk.END)
        entry.insert(0, filename)


def _select_folder(entry: ctk.CTkEntry) -> None:
    folder = filedialog.askdirectory(title="Selecione a pasta de saida")
    if folder:
        entry.delete(0, tk.END)
        entry.insert(0, folder)


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


def _update_plot(plot_frame: ctk.CTkFrame, fig) -> None:
    if hasattr(plot_frame, "canvas") and plot_frame.canvas is not None:
        plot_frame.canvas.get_tk_widget().destroy()
        plot_frame.canvas = None
    canvas = FigureCanvasTkAgg(fig, master=plot_frame)
    canvas.draw()
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.pack(fill=tk.BOTH, expand=True)
    plot_frame.canvas = canvas


def _execute_from_gui(
    input_entry: ctk.CTkEntry,
    output_entry: ctk.CTkEntry,
    status_var: tk.StringVar,
    output_text: scrolledtext.ScrolledText,
    plot_frame: ctk.CTkFrame,
    report_state: dict,
    pdf_button: ctk.CTkButton,
) -> None:
    input_path_raw = input_entry.get().strip()
    output_dir_raw = output_entry.get().strip()

    if not input_path_raw:
        messagebox.showerror("Erro", "Selecione um arquivo Excel.")
        return

    if not output_dir_raw:
        messagebox.showerror("Erro", "Selecione uma pasta de saida.")
        return

    input_path = Path(input_path_raw)
    output_dir = Path(output_dir_raw)

    try:
        pdf_button.configure(state="disabled")
        status_var.set("Processando...")
        output_text.update_idletasks()

        result = run_pipeline(input_path, output_dir)
        generated_files = [
            result.summary_path,
            result.descriptives_path,
            result.ttests_path,
            result.coefficients_path,
            result.plot_path,
        ]
        report_state.clear()
        report_state.update(
            {
                "stats_text": result.stats_text,
                "fig": result.figure,
                "output_dir": result.output_dir,
                "generated_files": generated_files,
                "pdf_path": None,
            }
        )
        _update_output_text(output_text, result.stats_text, generated_files)
        _update_plot(plot_frame, result.figure)
        pdf_button.configure(state="normal")
        status_var.set("Concluido.")
        messagebox.showinfo("Sucesso", "Analise finalizada.")
    except Exception as exc:
        status_var.set("Erro.")
        print(f"Erro: {exc}", file=sys.stderr)
        messagebox.showerror("Erro", str(exc))


def _generate_pdf_from_gui(
    status_var: tk.StringVar,
    output_text: scrolledtext.ScrolledText,
    report_state: dict,
) -> None:
    if not report_state.get("stats_text") or not report_state.get("fig"):
        messagebox.showwarning("Atencao", "Execute a analise antes de gerar o PDF.")
        return

    try:
        status_var.set("Gerando PDF...")
        output_text.update_idletasks()
        pdf_path = save_pdf_report(
            report_state["stats_text"],
            report_state["fig"],
            report_state["output_dir"],
        )
        report_state["pdf_path"] = pdf_path
        generated_files = list(report_state["generated_files"]) + [pdf_path]
        _update_output_text(output_text, report_state["stats_text"], generated_files)
        status_var.set("PDF gerado.")
        messagebox.showinfo("Sucesso", "PDF gerado com sucesso.")
    except Exception as exc:
        status_var.set("Erro ao gerar PDF.")
        print(f"Erro: {exc}", file=sys.stderr)
        messagebox.showerror("Erro", str(exc))


def main() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    root = ctk.CTk()
    root.title("Regressao Escolar - Exercicio 2")
    root.geometry("1040x760")
    root.minsize(920, 680)
    root.configure(fg_color=BACKGROUND)

    container = ctk.CTkFrame(root, fg_color=BACKGROUND)
    container.pack(fill=tk.BOTH, expand=True, padx=24, pady=24)

    header = ctk.CTkFrame(container, fg_color="transparent")
    header.pack(fill=tk.X, pady=(0, 18))
    header_top = ctk.CTkFrame(header, fg_color="transparent")
    header_top.pack(fill=tk.X)

    logo_block = ctk.CTkFrame(header_top, fg_color="transparent")
    logo_block.pack(side=tk.RIGHT)

    logo_image = _load_logo_image()
    if logo_image is not None:
        logo_label = ctk.CTkLabel(logo_block, text="", image=logo_image)
        logo_label.pack(side=tk.LEFT, padx=(0, 8))
        _bind_responsive_logo(root, logo_label, logo_image)

    ctk.CTkLabel(
        logo_block,
        text="ezequielgean.com.br",
        font=("Segoe UI", 12),
        text_color=TEXT_MUTED,
    ).pack(side=tk.LEFT, padx=(0, 8))

    ctk.CTkLabel(
        header_top,
        text="Regressao Escolar",
        font=("Segoe UI", 22, "bold"),
        text_color=TEXT_PRIMARY,
    ).pack(side=tk.LEFT, anchor="w")
    ctk.CTkLabel(
        header,
        text="Selecione a planilha Excel para gerar tabelas, regressao, grafico e relatorio.",
        font=("Segoe UI", 12),
        text_color=TEXT_MUTED,
    ).pack(anchor="w", pady=(4, 0))

    form = ctk.CTkFrame(container, fg_color=PANEL_BG, corner_radius=12)
    form.pack(fill=tk.X, pady=(0, 14))

    form_grid = ctk.CTkFrame(form, fg_color="transparent")
    form_grid.pack(fill=tk.X, padx=16, pady=16)
    form_grid.grid_columnconfigure(1, weight=1)

    ctk.CTkLabel(form_grid, text="Arquivo Excel", text_color=TEXT_BODY).grid(
        row=0, column=0, sticky="w", padx=(0, 12), pady=10
    )
    input_entry = ctk.CTkEntry(
        form_grid,
        fg_color=FIELD_BG,
        text_color="#f0f0f0",
        border_color=BUTTON_SECONDARY,
    )
    input_entry.insert(0, str(DEFAULT_INPUT))
    input_entry.grid(row=0, column=1, sticky="ew", pady=10)

    ctk.CTkButton(
        form_grid,
        text="Buscar",
        fg_color=BUTTON_SECONDARY,
        text_color="#e6e6e6",
        hover_color=BUTTON_SECONDARY_HOVER,
        corner_radius=10,
        command=lambda: _select_file(input_entry),
        width=120,
    ).grid(row=0, column=2, padx=(12, 0), pady=10, sticky="w")

    ctk.CTkLabel(form_grid, text="Pasta de saida", text_color=TEXT_BODY).grid(
        row=1, column=0, sticky="w", padx=(0, 12), pady=10
    )
    output_entry = ctk.CTkEntry(
        form_grid,
        fg_color=FIELD_BG,
        text_color="#f0f0f0",
        border_color=BUTTON_SECONDARY,
    )
    output_entry.insert(0, str(DEFAULT_OUTPUT_DIR))
    output_entry.grid(row=1, column=1, sticky="ew", pady=10)

    ctk.CTkButton(
        form_grid,
        text="Pasta",
        fg_color=BUTTON_SECONDARY,
        text_color="#e6e6e6",
        hover_color=BUTTON_SECONDARY_HOVER,
        corner_radius=10,
        command=lambda: _select_folder(output_entry),
        width=120,
    ).grid(row=1, column=2, padx=(12, 0), pady=10, sticky="w")

    actions = ctk.CTkFrame(container, fg_color="transparent")
    actions.pack(fill=tk.X, pady=(0, 14))

    status_var = tk.StringVar(value="Pronto para executar.")
    report_state: dict = {}

    ctk.CTkLabel(actions, textvariable=status_var, text_color=TEXT_MUTED).pack(
        side=tk.LEFT
    )

    pdf_button = ctk.CTkButton(
        actions,
        text="Gerar PDF",
        fg_color=BUTTON_SECONDARY,
        hover_color=BUTTON_SECONDARY_HOVER,
        text_color="#e6e6e6",
        corner_radius=10,
        state="disabled",
        command=lambda: _generate_pdf_from_gui(status_var, output_text, report_state),
        width=140,
    )
    pdf_button.pack(side=tk.RIGHT, padx=(8, 0))

    ctk.CTkButton(
        actions,
        text="Executar",
        fg_color=BUTTON_PRIMARY,
        hover_color=BUTTON_PRIMARY_HOVER,
        text_color="#1b1b1b",
        corner_radius=10,
        command=lambda: _execute_from_gui(
            input_entry,
            output_entry,
            status_var,
            output_text,
            plot_frame,
            report_state,
            pdf_button,
        ),
        width=160,
    ).pack(side=tk.RIGHT)

    output_label = ctk.CTkLabel(
        container,
        text="Resultados",
        font=("Segoe UI", 12, "bold"),
        text_color=TEXT_BODY,
    )
    output_label.pack(anchor="w", pady=(4, 6))

    output_text = scrolledtext.ScrolledText(
        container,
        height=14,
        wrap=tk.WORD,
        background=FIELD_BG,
        foreground="#f0f0f0",
        insertbackground="#f0f0f0",
    )
    output_text.pack(fill=tk.BOTH, expand=False)
    output_text.configure(state="disabled")

    plot_label = ctk.CTkLabel(
        container,
        text="Grafico",
        font=("Segoe UI", 12, "bold"),
        text_color=TEXT_BODY,
    )
    plot_label.pack(anchor="w", pady=(16, 6))

    plot_frame = ctk.CTkFrame(container, fg_color=FIELD_BG, corner_radius=12)
    plot_frame.pack(fill=tk.BOTH, expand=True)
    plot_frame.canvas = None

    root.mainloop()


if __name__ == "__main__":
    main()
