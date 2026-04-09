from __future__ import annotations

import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

import customtkinter as ctk

from .analise import DEFAULT_INPUT, DEFAULT_OUTPUT_DIR, run_pipeline, save_pdf_report


BACKGROUND = "#101418"
PANEL_BG = "#17212b"
FIELD_BG = "#12202a"
TEXT_PRIMARY = "#f5f7fa"
TEXT_MUTED = "#9fb0c0"
TEXT_BODY = "#e7edf3"
BUTTON_PRIMARY = "#dd6b20"
BUTTON_PRIMARY_HOVER = "#f08b3e"
BUTTON_SECONDARY = "#243647"
BUTTON_SECONDARY_HOVER = "#2d4459"


def _select_file(entry: ctk.CTkEntry) -> None:
    filename = filedialog.askopenfilename(
        title="Selecione o arquivo de entrada",
        filetypes=[("Dados", "*.csv *.xlsx *.xls"), ("Todos", "*")],
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


def _execute_from_gui(
    input_entry: ctk.CTkEntry,
    output_entry: ctk.CTkEntry,
    status_var: tk.StringVar,
    output_text: scrolledtext.ScrolledText,
    report_state: dict,
    pdf_button: ctk.CTkButton,
) -> None:
    input_path_raw = input_entry.get().strip()
    output_dir_raw = output_entry.get().strip()

    if not input_path_raw:
        messagebox.showerror("Erro", "Selecione um arquivo de entrada.")
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
            result.columns_path,
            result.preview_path,
            result.numeric_stats_path,
        ]

        report_state.clear()
        report_state.update(
            {
                "stats_text": result.stats_text,
                "output_dir": result.output_dir,
                "generated_files": generated_files,
            }
        )
        _update_output_text(output_text, result.stats_text, generated_files)
        pdf_button.configure(state="normal")
        status_var.set("Concluido.")
        messagebox.showinfo("Sucesso", "Execucao finalizada.")
    except Exception as exc:
        status_var.set("Erro.")
        print(f"Erro: {exc}", file=sys.stderr)
        messagebox.showerror("Erro", str(exc))


def _generate_pdf_from_gui(
    status_var: tk.StringVar,
    output_text: scrolledtext.ScrolledText,
    report_state: dict,
) -> None:
    if not report_state.get("stats_text"):
        messagebox.showwarning("Atencao", "Execute a analise antes de gerar o PDF.")
        return

    try:
        status_var.set("Gerando PDF...")
        output_text.update_idletasks()
        pdf_path = save_pdf_report(report_state["stats_text"], report_state["output_dir"])
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
    root.title("Modulo 05 - Base para Novo Programa")
    root.geometry("980x720")
    root.minsize(860, 620)
    root.configure(fg_color=BACKGROUND)

    container = ctk.CTkFrame(root, fg_color=BACKGROUND)
    container.pack(fill=tk.BOTH, expand=True, padx=24, pady=24)

    ctk.CTkLabel(
        container,
        text="Salario x Escolaridade",
        font=("Segoe UI", 24, "bold"),
        text_color=TEXT_PRIMARY,
    ).pack(anchor="w")
    ctk.CTkLabel(
        container,
        text="Base inicial para um novo programa, com a mesma organizacao dos demais modulos.",
        font=("Segoe UI", 12),
        text_color=TEXT_MUTED,
    ).pack(anchor="w", pady=(4, 18))

    form = ctk.CTkFrame(container, fg_color=PANEL_BG, corner_radius=12)
    form.pack(fill=tk.X, pady=(0, 14))

    form_grid = ctk.CTkFrame(form, fg_color="transparent")
    form_grid.pack(fill=tk.X, padx=16, pady=16)
    form_grid.grid_columnconfigure(1, weight=1)

    ctk.CTkLabel(form_grid, text="Arquivo", text_color=TEXT_BODY).grid(
        row=0, column=0, sticky="w", padx=(0, 12), pady=10
    )
    input_entry = ctk.CTkEntry(
        form_grid,
        fg_color=FIELD_BG,
        text_color=TEXT_PRIMARY,
        border_color=BUTTON_SECONDARY,
    )
    input_entry.insert(0, str(DEFAULT_INPUT))
    input_entry.grid(row=0, column=1, sticky="ew", pady=10)

    ctk.CTkButton(
        form_grid,
        text="Buscar",
        fg_color=BUTTON_SECONDARY,
        text_color=TEXT_BODY,
        hover_color=BUTTON_SECONDARY_HOVER,
        corner_radius=10,
        command=lambda: _select_file(input_entry),
        width=120,
    ).grid(row=0, column=2, padx=(12, 0), pady=10, sticky="w")

    ctk.CTkLabel(form_grid, text="Saida", text_color=TEXT_BODY).grid(
        row=1, column=0, sticky="w", padx=(0, 12), pady=10
    )
    output_entry = ctk.CTkEntry(
        form_grid,
        fg_color=FIELD_BG,
        text_color=TEXT_PRIMARY,
        border_color=BUTTON_SECONDARY,
    )
    output_entry.insert(0, str(DEFAULT_OUTPUT_DIR))
    output_entry.grid(row=1, column=1, sticky="ew", pady=10)

    ctk.CTkButton(
        form_grid,
        text="Escolher",
        fg_color=BUTTON_SECONDARY,
        text_color=TEXT_BODY,
        hover_color=BUTTON_SECONDARY_HOVER,
        corner_radius=10,
        command=lambda: _select_folder(output_entry),
        width=120,
    ).grid(row=1, column=2, padx=(12, 0), pady=10, sticky="w")

    actions = ctk.CTkFrame(container, fg_color="transparent")
    actions.pack(fill=tk.X, pady=(0, 14))

    status_var = tk.StringVar(value="Pronto.")
    report_state: dict = {}

    ctk.CTkButton(
        actions,
        text="Executar",
        fg_color=BUTTON_PRIMARY,
        hover_color=BUTTON_PRIMARY_HOVER,
        text_color="#111111",
        corner_radius=10,
        width=140,
        command=lambda: _execute_from_gui(
            input_entry,
            output_entry,
            status_var,
            output_text,
            report_state,
            pdf_button,
        ),
    ).pack(side=tk.LEFT)

    pdf_button = ctk.CTkButton(
        actions,
        text="Gerar PDF",
        fg_color=BUTTON_SECONDARY,
        hover_color=BUTTON_SECONDARY_HOVER,
        text_color=TEXT_BODY,
        corner_radius=10,
        width=140,
        state="disabled",
        command=lambda: _generate_pdf_from_gui(status_var, output_text, report_state),
    )
    pdf_button.pack(side=tk.LEFT, padx=(12, 0))

    ctk.CTkLabel(
        actions,
        textvariable=status_var,
        text_color=TEXT_MUTED,
        font=("Segoe UI", 12),
    ).pack(side=tk.RIGHT)

    results = ctk.CTkFrame(container, fg_color=PANEL_BG, corner_radius=12)
    results.pack(fill=tk.BOTH, expand=True)

    ctk.CTkLabel(
        results,
        text="Resumo da execucao",
        font=("Segoe UI", 14, "bold"),
        text_color=TEXT_PRIMARY,
    ).pack(anchor="w", padx=16, pady=(16, 8))

    output_text = scrolledtext.ScrolledText(
        results,
        wrap=tk.WORD,
        bg="#0e1720",
        fg="#ecf2f8",
        insertbackground="#ecf2f8",
        relief=tk.FLAT,
        font=("Consolas", 10),
    )
    output_text.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 16))
    output_text.insert(
        tk.END,
        "Selecione um arquivo de entrada e execute a base do modulo 05.\n",
    )
    output_text.configure(state="disabled")

    root.mainloop()
