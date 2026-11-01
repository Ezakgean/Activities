from __future__ import annotations

import json
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk
import webbrowser

import customtkinter as ctk
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from .gastos_publicos import OUTPUT, SOURCE, collect
from .painel_graficos import INK, PAPER, PANEL, TEAL, MUTED


def load_data(output: Path = OUTPUT) -> pd.DataFrame:
    files = sorted(output.glob('gastos_????_categorias.csv'))
    if not files:
        return pd.DataFrame()
    data = pd.concat([pd.read_csv(file, dtype=str, keep_default_na=False) for file in files], ignore_index=True)
    data['valor_pago_brl'] = pd.to_numeric(data['valor_pago_brl'], errors='raise')
    data['ano'] = data['periodo'].str[:4]
    return data


def grouped_data(data: pd.DataFrame, year: str, period: str, dimension: str, investments: bool,
                 primary: bool = False) -> pd.DataFrame:
    selected = data.loc[data['ano'].eq(year)]
    if period != 'Acumulado disponível':
        selected = selected.loc[selected['periodo'].eq(period)]
    if investments:
        selected = selected.loc[selected['grupo_codigo'].eq('4')]
    if primary:
        selected = selected.loc[selected['natureza'].str.casefold().eq('primária')]
    # Agrupa códigos junto dos nomes: órgãos diferentes podem ter nomes iguais.
    result = selected.groupby([f'{dimension}_codigo', dimension], dropna=False)['valor_pago_brl'].sum().reset_index()
    result[dimension] = result[dimension].replace('', 'Não informado')
    return result.sort_values('valor_pago_brl', ascending=False)


def brl(value: float) -> str:
    return 'R$ ' + f'{value:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def open_spending_dashboard(parent: tk.Misc, output: Path = OUTPUT) -> None:
    window = ctk.CTkToplevel(parent)
    window.title('Gastos públicos da União | Tesouro Transparente')
    window.geometry('1300x850')
    window.minsize(1050, 700)
    window.configure(fg_color=PAPER)
    window.grid_columnconfigure(0, weight=1)
    window.grid_rowconfigure(4, weight=1)
    data = pd.DataFrame()
    messages = queue.Queue()
    busy = False

    heading = ctk.CTkFrame(window, fg_color='transparent')
    heading.grid(row=0, column=0, sticky='ew', padx=24, pady=(20, 10))
    ctk.CTkLabel(heading, text='Onde a União aplica seus recursos', font=('Georgia', 27, 'bold'), text_color=INK).pack(anchor='w')
    ctk.CTkLabel(heading, text='Pagamentos em reais correntes, incluindo restos a pagar, transferências e despesas financeiras.\n'
                 'Investimentos: apenas o grupo de natureza de despesa 4. Cobertura: União.',
                 text_color=MUTED, justify='left').pack(anchor='w', pady=5)
    controls = ctk.CTkFrame(window, fg_color=PANEL)
    controls.grid(row=1, column=0, sticky='ew', padx=24, pady=5)
    year = tk.StringVar()
    period = tk.StringVar(value='Acumulado disponível')
    dimension = tk.StringVar(value='Área de atuação (função)')
    mode = tk.StringVar(value='Todos os pagamentos')
    dimensions = {'Área de atuação (função)': 'funcao', 'Subfunção': 'subfuncao', 'Órgão': 'orgao', 'Natureza do gasto': 'grupo'}
    menus = []
    for index, (label, variable, options) in enumerate([
        ('Ano', year, ['Sem dados']), ('Período', period, ['Acumulado disponível']),
        ('Agrupar por', dimension, list(dimensions)), ('Valores', mode, ['Todos os pagamentos', 'Despesas primárias', 'Investimentos (GND 4)']),
    ]):
        cell = ctk.CTkFrame(controls, fg_color='transparent')
        cell.grid(row=0, column=index, padx=10, pady=10, sticky='ew')
        controls.grid_columnconfigure(index, weight=1)
        ctk.CTkLabel(cell, text=label, text_color=MUTED).pack(anchor='w')
        menu = ctk.CTkOptionMenu(cell, variable=variable, values=options, width=180,
                                command=lambda _, i=index: changed(i), fg_color=TEAL)
        menu.pack(fill='x')
        menus.append(menu)
    total = tk.StringVar()
    ctk.CTkLabel(window, textvariable=total, font=('Georgia', 21, 'bold'), text_color=INK).grid(row=2, column=0, sticky='w', padx=24, pady=10)
    coverage = tk.StringVar()
    ctk.CTkLabel(window, textvariable=coverage, text_color=MUTED).grid(row=3, column=0, sticky='w', padx=24)

    body = ctk.CTkFrame(window, fg_color=PANEL)
    body.grid(row=4, column=0, sticky='nsew', padx=24, pady=12)
    body.grid_columnconfigure(0, weight=1)
    body.grid_columnconfigure(1, weight=1)
    body.grid_rowconfigure(0, weight=1)
    chart = ctk.CTkFrame(body, fg_color=PANEL)
    chart.grid(row=0, column=0, sticky='nsew')
    table_frame = ctk.CTkFrame(body, fg_color='transparent')
    table_frame.grid(row=0, column=1, sticky='nsew', padx=10, pady=10)
    table_frame.grid_columnconfigure(0, weight=1)
    table_frame.grid_rowconfigure(0, weight=1)
    tree = ttk.Treeview(table_frame, columns=('categoria', 'valor'), show='headings')
    tree.heading('categoria', text='Categoria')
    tree.heading('valor', text='Valor pago')
    tree.column('categoria', width=280)
    tree.column('valor', width=175, anchor='e')
    tree.grid(row=0, column=0, sticky='nsew')
    scroll = ttk.Scrollbar(table_frame, orient='vertical', command=tree.yview)
    scroll.grid(row=0, column=1, sticky='ns')
    tree.configure(yscrollcommand=scroll.set)
    status = tk.StringVar()
    ctk.CTkLabel(window, textvariable=status, text_color=MUTED, wraplength=1200).grid(row=5, column=0, sticky='w', padx=24)
    footer = ctk.CTkFrame(window, fg_color='transparent')
    footer.grid(row=6, column=0, sticky='ew', padx=24, pady=15)

    def render():
        for child in chart.winfo_children():
            child.destroy()
        tree.delete(*tree.get_children())
        if data.empty:
            total.set('Nenhuma base de gastos carregada')
            coverage.set('Clique em “Coletar último ano” para obter a base do Tesouro.')
            return
        key = dimensions[dimension.get()]
        values = grouped_data(data, year.get(), period.get(), key, mode.get() == 'Investimentos (GND 4)',
                              mode.get() == 'Despesas primárias')
        total.set(f'{mode.get()}: {brl(values.valor_pago_brl.sum())}')
        months = sorted(data.loc[data.ano.eq(year.get()), 'periodo'].unique())
        coverage.set(f'Base disponível: {months[0]} a {months[-1]} • {len(months)} meses • {len(values)} categorias no filtro')
        for _, row in values.iterrows():
            tree.insert('', 'end', values=(f'{row[key+"_codigo"]} — {row[key]}', brl(row.valor_pago_brl)))
        figure = Figure(figsize=(6.5, 4.5), dpi=100, facecolor=PANEL)
        axis = figure.add_subplot(111)
        axis.set_facecolor(PANEL)
        top = values.head(12).iloc[::-1]
        if top.empty:
            axis.text(.5, .5, 'Sem pagamentos informados para este filtro', transform=axis.transAxes, ha='center')
            axis.set_axis_off()
        else:
            labels = [name.title() if len(name) < 35 else name[:32].title() + '…' for name in top[key]]
            axis.barh(range(len(top)), top.valor_pago_brl / 1e9, color=TEAL)
            axis.set_yticks(range(len(top)), labels, fontsize=9)
            axis.set_xlabel('R$ bilhões')
            axis.set_title('12 maiores categorias por valor pago', loc='left', fontsize=12)
            axis.grid(axis='x', alpha=.2)
        figure.tight_layout()
        canvas = FigureCanvasTkAgg(figure, master=chart)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)

    def changed(index):
        if index == 0 and not data.empty:
            menus[1].configure(values=['Acumulado disponível', *sorted(data.loc[data.ano.eq(year.get()), 'periodo'].unique())])
            period.set('Acumulado disponível')
        render()
        if not data.empty:
            summary = output / f'gastos_{year.get()}_resumo.json'
            if summary.exists():
                metadata = json.loads(summary.read_text(encoding='utf-8'))
                count = len(metadata['validacao'].get('divergencias_componentes', []))
                note = f' • {count} divergências entre total e componentes na fonte; total publicado preservado.' if count else ''
                status.set(f'{year.get()} • Extração: {metadata["coletado_em"][:10]} • Fonte: Tesouro Transparente (valor pago).{note}')

    def reload_data():
        nonlocal data
        try:
            data = load_data(output)
            if not data.empty:
                years = sorted(data.ano.unique())
                menus[0].configure(values=years)
                year.set(years[-1])
                changed(0)
            else:
                render()
        except Exception as exc:
            status.set(f'Não foi possível carregar a base: {exc}')

    def start_collection(all_years=False):
        nonlocal busy
        if busy:
            return
        busy = True
        update.configure(state='disabled')
        historical.configure(state='disabled')
        status.set('Consultando o catálogo oficial...')
        def worker():
            try:
                collect(output=output, all_years=all_years, log=lambda text: messages.put(('status', text)))
                messages.put(('done', 'Coleta concluída. Valores atualizados.'))
            except Exception as exc:
                messages.put(('error', f'Falha na coleta: {exc}'))
        threading.Thread(target=worker, daemon=True).start()
        window.after(150, poll)

    def poll():
        nonlocal busy
        while not messages.empty():
            kind, message = messages.get_nowait()
            status.set(message)
            if kind in ('done', 'error'):
                busy = False
                update.configure(state='normal')
                historical.configure(state='normal')
                reload_data()
                status.set(message)
        if busy:
            window.after(150, poll)

    update = ctk.CTkButton(footer, text='Coletar último ano', command=start_collection, fg_color=TEAL)
    update.pack(side='left', padx=(0, 10))
    historical = ctk.CTkButton(footer, text='Coletar todo o histórico', command=lambda: start_collection(True), fg_color=TEAL)
    historical.pack(side='left', padx=(0, 10))
    ctk.CTkButton(footer, text='Recarregar arquivos', command=reload_data, fg_color=TEAL).pack(side='left')
    ctk.CTkButton(footer, text='Fonte: Tesouro Transparente', command=lambda: webbrowser.open(SOURCE), fg_color=INK).pack(side='right')
    reload_data()
    window.focus_set()
