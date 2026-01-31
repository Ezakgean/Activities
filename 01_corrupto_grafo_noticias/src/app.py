from __future__ import annotations

"""CustomTkinter GUI for the project."""

import logging
import threading
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from .config import normalize_settings
from .main import run_pipeline

logger = logging.getLogger(__name__)


def _run_task(state, update_output):
    """Run the pipeline in a background thread."""
    try:
        result = run_pipeline(
            state["query"],
            int(state["pages"]),
            int(state["top"]),
            state["api_key"],
            state["cx"],
        )
    except Exception as exc:
        logger.exception("Erro ao executar pipeline")
        update_output(f"Erro: {exc}")
        return

    titles = result["titles"]
    counts = result["counts"]
    output_dir = result["output_dir"]

    if not titles:
        update_output(result["message"])
        return

    lines = [
        f"Titulos coletados: {len(titles)}",
        "Top palavras:",
    ]
    for word, count in counts.most_common(10):
        lines.append(f"- {word}: {count}")
    lines.append(f"Arquivo: {output_dir / 'titles.txt'}")
    lines.append(f"Arquivo: {output_dir / 'words.csv'}")
    lines.append(f"Grafo: {output_dir / 'graph.html'}")
    update_output("\n".join(lines))


def main() -> None:
    """Launch the GUI."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    root = ctk.CTk()
    root.title("Vinculos Corrupcao")
    root.geometry("900x600")
    root.minsize(860, 560)

    root.configure(fg_color="#0f0f10")

    container = ctk.CTkFrame(root, fg_color="#0f0f10")
    container.pack(fill=tk.BOTH, expand=True, padx=24, pady=24)

    header = ctk.CTkFrame(container, fg_color="transparent")
    header.pack(fill=tk.X, pady=(0, 18))
    ctk.CTkLabel(
        header,
        text="Google Custom Search",
        font=("Segoe UI", 22, "bold"),
        text_color="#f7f7f7",
    ).pack(anchor="w")
    ctk.CTkLabel(
        header,
        text="Insira as credenciais e gere a rede de palavras com base nos titulos.",
        font=("Segoe UI", 12),
        text_color="#9aa0a6",
    ).pack(anchor="w", pady=(4, 0))

    form = ctk.CTkFrame(container, fg_color="#141516", corner_radius=12)
    form.pack(fill=tk.X, pady=(0, 14))

    form_grid = ctk.CTkFrame(form, fg_color="transparent")
    form_grid.pack(fill=tk.X, padx=16, pady=16)
    form_grid.grid_columnconfigure(1, weight=1)
    form_grid.grid_columnconfigure(3, weight=1)

    def row(label_text, default="", show=False, row_idx=0, col=0, width=300):
        ctk.CTkLabel(form_grid, text=label_text, text_color="#eaeaea").grid(
            row=row_idx, column=col, sticky="w", padx=(0, 12), pady=10
        )
        entry = ctk.CTkEntry(
            form_grid,
            width=width,
            show="•" if show else None,
            fg_color="#17181a",
            text_color="#f0f0f0",
            border_color="#2a2b2e",
        )
        entry.insert(0, default)
        entry.grid(row=row_idx, column=col + 1, sticky="ew", pady=10)
        return entry

    api_key_entry = row("API Key", show=True, row_idx=0)
    cx_entry = row("CSE ID (cx)", show=True, row_idx=1)
    query_entry = row("Consulta", "corrupcao", row_idx=2)
    pages_entry = row("Paginas", "2", row_idx=3, width=120)
    ctk.CTkLabel(form_grid, text="Top palavras", text_color="#eaeaea").grid(
        row=3, column=2, sticky="e", padx=(12, 8), pady=10
    )
    top_entry = row("", "30", row_idx=3, col=2, width=120)

    actions = ctk.CTkFrame(container, fg_color="transparent")
    actions.pack(fill=tk.X, pady=(0, 14))

    def toggle_keys_visibility() -> None:
        show = "•" if hide_keys_var.get() else ""
        api_key_entry.configure(show=show)
        cx_entry.configure(show=show)

    hide_keys_var = tk.BooleanVar(value=True)
    switch = ctk.CTkSwitch(
        actions,
        text="Ocultar chaves",
        variable=hide_keys_var,
        onvalue=True,
        offvalue=False,
        text_color="#9aa0a6",
        command=toggle_keys_visibility,
    )
    switch.pack(side=tk.LEFT)
    toggle_keys_visibility()

    status_var = tk.StringVar(value="Pronto para executar.")
    ctk.CTkLabel(actions, textvariable=status_var, text_color="#9aa0a6").pack(
        side=tk.LEFT, padx=(16, 0)
    )

    def on_run() -> None:
        api_key = api_key_entry.get().strip()
        cx = cx_entry.get().strip()
        if not api_key or not cx:
            messagebox.showerror("Erro", "API Key e CSE ID sao obrigatorios.")
            return
        try:
            settings = normalize_settings(
                api_key,
                cx,
                query_entry.get().strip(),
                pages_entry.get().strip(),
                top_entry.get().strip(),
            )
        except ValueError as exc:
            messagebox.showerror("Erro", str(exc))
            return
        state = {
            "api_key": settings.api_key,
            "cx": settings.cx,
            "query": settings.query,
            "pages": settings.pages,
            "top": settings.top,
        }

        status_var.set("Rodando... aguarde.")

        def run_in_thread():
            def update_output(text: str) -> None:
                output.configure(state="normal")
                output.delete("1.0", tk.END)
                output.insert(tk.END, text)
                output.configure(state="disabled")
                status_var.set("Concluido.")

            _run_task(state, lambda t: root.after(0, update_output, t))

        threading.Thread(target=run_in_thread, daemon=True).start()

    ctk.CTkButton(
        actions,
        text="Rodar",
        fg_color="#f5821f",
        text_color="#121212",
        hover_color="#ff8c33",
        corner_radius=10,
        command=on_run,
    ).pack(side=tk.RIGHT)

    output_frame = ctk.CTkFrame(container, fg_color="#141516", corner_radius=12)
    output_frame.pack(fill=tk.BOTH, expand=True)

    output_label = ctk.CTkLabel(
        output_frame, text="Resultado", text_color="#eaeaea", font=("Segoe UI", 12, "bold")
    )
    output_label.pack(anchor="w", padx=14, pady=(12, 0))

    output = ctk.CTkTextbox(
        output_frame,
        height=220,
        fg_color="#17181a",
        text_color="#f0f0f0",
        border_color="#2a2b2e",
        border_width=1,
    )
    output.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
    output.configure(state="disabled")

    root.mainloop()


if __name__ == "__main__":
    main()
