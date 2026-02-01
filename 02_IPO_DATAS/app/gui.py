from __future__ import annotations

import json
import threading
import tkinter as tk
from tkinter import filedialog
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from .scraping.sre_consulta import selecionar_e_extrair

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
        width = root.winfo_width() or 900
        target_height = max(24, min(48, int(width * 0.06)))
        original_height = max(1, logo_image.height())
        scale = max(1, int(original_height / target_height))
        scaled = logo_image.subsample(scale, scale)
        logo_label.configure(image=scaled)
        logo_label.image = scaled

    root.bind("<Configure>", on_resize)
    on_resize()

def _parse_years(text: str) -> list[int]:
    raw = (text or "").strip()
    if not raw:
        raise ValueError("Informe pelo menos um ano.")

    years: set[int] = set()
    parts = [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()]
    for part in parts:
        if "-" in part:
            start_str, end_str = [p.strip() for p in part.split("-", 1)]
            if not start_str or not end_str:
                raise ValueError(f"Intervalo invalido: '{part}'")
            try:
                start = int(start_str)
                end = int(end_str)
            except ValueError as exc:
                raise ValueError(f"Ano invalido no intervalo: '{part}'") from exc
            if start > end:
                start, end = end, start
            for year in range(start, end + 1):
                years.add(year)
        else:
            try:
                years.add(int(part))
            except ValueError as exc:
                raise ValueError(f"Ano invalido: '{part}'") from exc

    if not years:
        raise ValueError("Nenhum ano valido encontrado.")
    return sorted(years)


def _resolve_out_path(template: str, year: int, multiple: bool) -> Path:
    path_str = (template or "").strip()
    if not path_str:
        return Path()
    if "{ano}" in path_str:
        return Path(path_str.replace("{ano}", str(year)))
    if multiple:
        base = Path(path_str)
        suffix = base.suffix
        stem = base.stem
        return base.with_name(f"{stem}_{year}{suffix}")
    return Path(path_str)


def main() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    root = ctk.CTk()
    root.title("SRE Consulta - IPOs")
    root.geometry("900x640")
    root.minsize(860, 600)
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
        text="Consulta CVM (SRE)",
        font=("Segoe UI", 22, "bold"),
        text_color=TEXT_PRIMARY,
    ).pack(side=tk.LEFT, anchor="w")
    ctk.CTkLabel(
        header,
        text="Selecione tipo e anos para coletar IPOs.",
        font=("Segoe UI", 12),
        text_color=TEXT_MUTED,
    ).pack(anchor="w", pady=(4, 0))

    form = ctk.CTkFrame(container, fg_color=PANEL_BG, corner_radius=12)
    form.pack(fill=tk.X, pady=(0, 14))

    form_grid = ctk.CTkFrame(form, fg_color="transparent")
    form_grid.pack(fill=tk.X, padx=16, pady=16)
    form_grid.grid_columnconfigure(1, weight=1)
    form_grid.grid_columnconfigure(3, weight=1)

    def row(
        label_text: str,
        default: str = "",
        show: bool = False,
        row_idx: int = 0,
        col: int = 0,
        width: int = 300,
    ) -> ctk.CTkEntry:
        ctk.CTkLabel(form_grid, text=label_text, text_color=TEXT_BODY).grid(
            row=row_idx, column=col, sticky="w", padx=(0, 12), pady=10
        )
        entry = ctk.CTkEntry(
            form_grid,
            width=width,
            show="•" if show else None,
            fg_color=FIELD_BG,
            text_color="#f0f0f0",
            border_color=BUTTON_SECONDARY,
        )
        entry.insert(0, default)
        entry.grid(row=row_idx, column=col + 1, sticky="ew", pady=10)
        return entry

    tipo_entry = row("TipoEmis", "ACOES", row_idx=0, width=160)
    anos_entry = row("Anos (ex.: 2005,2008-2010)", "2005", row_idx=1, width=300)
    json_entry = row("JSON out", "data/output/sre_consulta.json", row_idx=2)
    csv_entry = row("CSV out (opcional)", "", row_idx=3)
    max_entry = row("Max registros (opcional)", "", row_idx=4, width=160)

    def apply_folder(entry: ctk.CTkEntry, default_name: str) -> None:
        folder = filedialog.askdirectory()
        if not folder:
            return
        current = (entry.get() or "").strip()
        current_name = Path(current).name if current else default_name
        entry.delete(0, tk.END)
        entry.insert(0, str(Path(folder) / current_name))

    ctk.CTkButton(
        form_grid,
        text="Pasta JSON",
        fg_color=BUTTON_SECONDARY,
        text_color="#e6e6e6",
        hover_color=BUTTON_SECONDARY_HOVER,
        corner_radius=10,
        command=lambda: apply_folder(json_entry, "sre_consulta.json"),
        width=120,
    ).grid(row=2, column=2, padx=(12, 0), pady=10, sticky="w")

    ctk.CTkButton(
        form_grid,
        text="Pasta CSV",
        fg_color=BUTTON_SECONDARY,
        text_color="#e6e6e6",
        hover_color=BUTTON_SECONDARY_HOVER,
        corner_radius=10,
        command=lambda: apply_folder(csv_entry, "sre_consulta.csv"),
        width=120,
    ).grid(row=3, column=2, padx=(12, 0), pady=10, sticky="w")

    headed_var = tk.BooleanVar(value=True)
    headed_chk = ctk.CTkCheckBox(
        form_grid,
        text="Navegador visivel (headed)",
        variable=headed_var,
        text_color=TEXT_BODY,
    )
    headed_chk.grid(row=4, column=2, columnspan=2, sticky="w", padx=(12, 0), pady=10)

    actions = ctk.CTkFrame(container, fg_color="transparent")
    actions.pack(fill=tk.X, pady=(0, 14))

    status_var = tk.StringVar(value="Pronto para executar.")
    ctk.CTkLabel(actions, textvariable=status_var, text_color=TEXT_MUTED).pack(side=tk.LEFT)

    output_frame = ctk.CTkFrame(container, fg_color=PANEL_BG, corner_radius=12)
    output_frame.pack(fill=tk.BOTH, expand=True)

    ctk.CTkLabel(
        output_frame, text="Resultado", text_color=TEXT_BODY, font=("Segoe UI", 12, "bold")
    ).pack(anchor="w", padx=14, pady=(12, 0))

    output = ctk.CTkTextbox(
        output_frame,
        height=240,
        fg_color=FIELD_BG,
        text_color="#f0f0f0",
        border_color=BUTTON_SECONDARY,
        border_width=1,
    )
    output.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
    output.configure(state="disabled")

    last_json_text_merged = ""
    last_json_text_run = ""

    def append_output(text: str) -> None:
        output.configure(state="normal")
        output.insert(tk.END, text + "\n")
        output.see(tk.END)
        output.configure(state="disabled")

    def on_run() -> None:
        nonlocal last_json_text_merged
        nonlocal last_json_text_run
        tipo = tipo_entry.get().strip()
        anos_raw = anos_entry.get().strip()
        json_template = json_entry.get().strip()
        csv_template = csv_entry.get().strip()
        max_raw = max_entry.get().strip()

        if not tipo:
            messagebox.showerror("Erro", "TipoEmis e obrigatorio.")
            return
        if not json_template:
            messagebox.showerror("Erro", "JSON out e obrigatorio.")
            return
        try:
            years = _parse_years(anos_raw)
        except ValueError as exc:
            messagebox.showerror("Erro", str(exc))
            return

        max_registros = None
        if max_raw:
            try:
                max_registros = int(max_raw)
            except ValueError:
                messagebox.showerror("Erro", "Max registros deve ser inteiro.")
                return

        output.configure(state="normal")
        output.delete("1.0", tk.END)
        output.configure(state="disabled")
        status_var.set("Rodando... aguarde.")
        last_json_text_merged = ""
        last_json_text_run = ""

        def run_in_thread() -> None:
            total_rows = 0
            total_json = 0
            multiple = len(years) > 1
            combined_rows: list[dict] = []
            combined_rows_run: list[dict] = []

            for year in years:
                json_out = _resolve_out_path(json_template, year, multiple)
                csv_out = _resolve_out_path(csv_template, year, multiple) if csv_template else Path()

                def log(msg: str) -> None:
                    root.after(0, append_output, msg)

                log(f"[ANO {year}] Iniciando...")
                try:
                    rows_run, total_json_now, rows_payload = selecionar_e_extrair(
                        tipo=tipo,
                        ano=year,
                        json_out=json_out,
                        headless=not headed_var.get(),
                        csv_out=csv_out if csv_template else None,
                        max_registros=max_registros,
                    )
                except Exception as exc:
                    log(f"[ANO {year}] ERRO: {exc}")
                    continue

                total_rows += rows_run
                total_json = total_json_now
                if rows_payload:
                    combined_rows_run.extend(rows_payload)
                log(f"[ANO {year}] OK: {rows_run} linhas extraidas.")
                log(f"[ANO {year}] JSON: {json_out}")
                if csv_template:
                    log(f"[ANO {year}] CSV: {csv_out}")

                try:
                    if json_out.exists():
                        data = json.loads(json_out.read_text(encoding="utf-8"))
                        if isinstance(data, list):
                            combined_rows.extend(data)
                except Exception:
                    log(f"[ANO {year}] Aviso: nao foi possivel ler o JSON para copiar.")

            def finalize() -> None:
                nonlocal last_json_text_merged
                nonlocal last_json_text_run
                status_var.set("Concluido.")
                append_output(f"Total extraido no run: {total_rows}")
                if total_json:
                    append_output(f"Total no JSON apos merge: {total_json}")
                if combined_rows:
                    last_json_text_merged = json.dumps(
                        combined_rows, ensure_ascii=False, indent=2
                    )
                if combined_rows_run:
                    last_json_text_run = json.dumps(
                        combined_rows_run, ensure_ascii=False, indent=2
                    )

            root.after(0, finalize)

        threading.Thread(target=run_in_thread, daemon=True).start()

    def on_copy_json_merged() -> None:
        if not last_json_text_merged:
            messagebox.showinfo("Info", "Nenhum resultado para copiar ainda.")
            return
        root.clipboard_clear()
        root.clipboard_append(last_json_text_merged)
        status_var.set("JSON (merge) copiado para a area de transferencia.")

    def on_copy_json_run() -> None:
        if not last_json_text_run:
            messagebox.showinfo("Info", "Nenhum resultado para copiar ainda.")
            return
        root.clipboard_clear()
        root.clipboard_append(last_json_text_run)
        status_var.set("JSON (sem merge) copiado para a area de transferencia.")

    ctk.CTkButton(
        actions,
        text="Copiar JSON (merge)",
        fg_color=BUTTON_SECONDARY,
        text_color="#e6e6e6",
        hover_color=BUTTON_SECONDARY_HOVER,
        corner_radius=10,
        command=on_copy_json_merged,
    ).pack(side=tk.RIGHT, padx=(0, 10))

    ctk.CTkButton(
        actions,
        text="Copiar JSON (sem merge)",
        fg_color=BUTTON_SECONDARY,
        text_color="#e6e6e6",
        hover_color=BUTTON_SECONDARY_HOVER,
        corner_radius=10,
        command=on_copy_json_run,
    ).pack(side=tk.RIGHT, padx=(0, 10))

    ctk.CTkButton(
        actions,
        text="Rodar",
        fg_color=BUTTON_PRIMARY,
        text_color="#121212",
        hover_color=BUTTON_PRIMARY_HOVER,
        corner_radius=10,
        command=on_run,
    ).pack(side=tk.RIGHT, padx=(0, 8))

    root.mainloop()


if __name__ == "__main__":
    main()
