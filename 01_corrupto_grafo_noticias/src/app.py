from __future__ import annotations

"""CustomTkinter GUI for the project."""

import logging
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from .config import normalize_settings
from .main import run_pipeline
from .search import fetch_titles

logger = logging.getLogger(__name__)
TEXT_MUTED = "#9aa0a6"


def _load_logo_image() -> tk.PhotoImage | None:
    logo_path = Path(__file__).resolve().parents[2] / "src" / "logo2.png"
    if not logo_path.exists():
        return None
    try:
        return tk.PhotoImage(file=str(logo_path))
    except Exception:
        logger.warning("Nao foi possivel carregar o logo: %s", logo_path)
        return None


def _bind_responsive_logo(root: ctk.CTk, logo_label: ctk.CTkLabel, logo_image: tk.PhotoImage) -> None:
    def on_resize(event: tk.Event | None = None) -> None:
        width = root.winfo_width() or 900
        target_height = max(24, min(48, int(width * 0.06)))
        original_height = max(1, logo_image.height())
        scale = max(1, int(original_height / target_height))
        scaled = logo_image.subsample(scale, scale)
        logo_label.configure(image=scaled)
        logo_label.image = scaled

    root.bind("<Configure>", on_resize)
    on_resize()


def _run_task(state, update_output):
    """Run the pipeline in a background thread."""
    try:
        result = run_pipeline(
            state["query"],
            int(state["pages"]),
            int(state["top"]),
            state["project_id"],
            state["location"],
            state["engine_id"],
            state["credentials_path"],
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
        text="Vertex AI Search",
        font=("Segoe UI", 22, "bold"),
        text_color="#f7f7f7",
    ).pack(side=tk.LEFT, anchor="w")
    ctk.CTkLabel(
        header,
        text="Informe o projeto e o engine para gerar a rede de palavras.",
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

    project_entry = row("Project ID", row_idx=0)
    location_entry = row("Location", "global", row_idx=1, width=120)
    engine_entry = row("Engine ID", row_idx=2)
    credentials_entry = row("Credenciais JSON (opcional)", row_idx=3, width=300)
    query_entry = row("Consulta", "corrupcao", row_idx=4)
    pages_entry = row("Paginas", "2", row_idx=5, width=120)
    ctk.CTkLabel(form_grid, text="Top palavras", text_color="#eaeaea").grid(
        row=5, column=2, sticky="e", padx=(12, 8), pady=10
    )
    top_entry = row("", "30", row_idx=5, col=2, width=120)

    actions = ctk.CTkFrame(container, fg_color="transparent")
    actions.pack(fill=tk.X, pady=(0, 14))

    status_var = tk.StringVar(value="Pronto para executar.")
    ctk.CTkLabel(actions, textvariable=status_var, text_color="#9aa0a6").pack(side=tk.LEFT)

    def on_test_connection() -> None:
        project_id = project_entry.get().strip()
        engine_id = engine_entry.get().strip()
        if not project_id or not engine_id:
            messagebox.showerror("Erro", "Project ID e Engine ID sao obrigatorios.")
            return
        try:
            settings = normalize_settings(
                project_id,
                location_entry.get().strip(),
                engine_id,
                credentials_entry.get().strip(),
                query_entry.get().strip(),
                1,
                5,
            )
        except ValueError as exc:
            messagebox.showerror("Erro", str(exc))
            return

        status_var.set("Testando conexao... aguarde.")

        def run_in_thread():
            def update_status(text: str) -> None:
                status_var.set(text)

            try:
                titles = fetch_titles(
                    settings.query,
                    pages=1,
                    project_id=settings.project_id,
                    location=settings.location,
                    engine_id=settings.engine_id,
                    credentials_path=settings.credentials_path,
                )
            except Exception as exc:
                root.after(0, update_status, f"Falha na conexao: {exc}")
                return
            msg = f"Conexao OK. Titulos retornados: {len(titles)}"
            root.after(0, update_status, msg)

        threading.Thread(target=run_in_thread, daemon=True).start()

    def on_run() -> None:
        project_id = project_entry.get().strip()
        engine_id = engine_entry.get().strip()
        if not project_id or not engine_id:
            messagebox.showerror("Erro", "Project ID e Engine ID sao obrigatorios.")
            return
        try:
            settings = normalize_settings(
                project_id,
                location_entry.get().strip(),
                engine_id,
                credentials_entry.get().strip(),
                query_entry.get().strip(),
                pages_entry.get().strip(),
                top_entry.get().strip(),
            )
        except ValueError as exc:
            messagebox.showerror("Erro", str(exc))
            return
        state = {
            "project_id": settings.project_id,
            "location": settings.location,
            "engine_id": settings.engine_id,
            "credentials_path": settings.credentials_path,
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
        text="Testar conexao",
        fg_color="#2a2b2e",
        text_color="#e6e6e6",
        hover_color="#33353a",
        corner_radius=10,
        command=on_test_connection,
    ).pack(side=tk.RIGHT, padx=(0, 10))

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
