# 03_regressão_linear

**Idioma / Language:** [Português](#pt-br) | [English](#en)

---

## PT-BR

Aplicação em Python para **regressão linear simples** entre renda e despesas com alimentação, com interface gráfica, gráfico de dispersão com linha ajustada e relatório em PDF.

### Como funciona
1. Lê o CSV de entrada.
2. Valida as colunas obrigatórias.
3. Converte números com vírgula decimal para `float`.
4. Remove linhas inválidas.
5. Ajusta o modelo OLS com `statsmodels`.
6. Gera resumo estatístico, CSV com resíduos, PNG e PDF.

### Colunas obrigatórias
- `observações`
- `x - renda`
- `y - despesas com alimentação`

### Requisitos
- Python 3.10+
- Dependências instaladas a partir do `requirements.txt` da raiz

### Instalação
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
```

### Interface gráfica
```bash
cd 03_regressão_linear
python -m app
```

Fluxo da GUI:
- selecione o CSV
- clique em **Executar**
- revise o resumo e o gráfico
- use **Gerar PDF** se quiser exportar o relatório

### Saídas
Os arquivos são salvos na mesma pasta do CSV selecionado:
- `resultado_exe1_regressao.csv`
- `grafico_exe1_regressao.png`
- `relatorio_exe1_regressao.pdf`

O CSV de saída contém:
- observação original
- `x`
- `y`
- `y_estimado`
- `residuo`

### Uso programático
Não há um wrapper CLI dedicado. Para automação, use `app/regressao.py` via Python:
```python
from pathlib import Path
from app.regressao import run_pipeline

stats_text, df_out, fig, csv_path, png_path = run_pipeline(Path("dados.csv"))
```

### Estrutura relevante
- `app/gui.py`: GUI
- `app/regressao.py`: pipeline de limpeza, ajuste e exportação
- `dados.csv`: exemplo de entrada

### Observações
- Valores com vírgula decimal são convertidos automaticamente.
- Linhas inválidas são removidas antes do ajuste.
- No Linux, o Tkinter pode exigir `python3-tk`.

### Troubleshooting
- **Erro de colunas ausentes**: confirme os nomes exatos no CSV.
- **PDF não gerado**: execute a regressão antes de clicar em **Gerar PDF**.

---

## EN

Python app for **simple linear regression** between income and food expenses, with GUI, scatter plot plus fitted line, and PDF report.

### How it works
1. Reads the input CSV.
2. Validates required columns.
3. Converts comma-decimal numbers to `float`.
4. Drops invalid rows.
5. Fits an OLS model with `statsmodels`.
6. Generates the statistical summary, residual CSV, PNG, and PDF.

### Required columns
- `observações`
- `x - renda`
- `y - despesas com alimentação`

### Requirements
- Python 3.10+
- Dependencies installed from the repository root `requirements.txt`

### Installation
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
```

### GUI
```bash
cd 03_regressão_linear
python -m app
```

GUI flow:
- select the CSV
- click **Executar**
- review the summary and chart
- use **Gerar PDF** if you want the report export

### Outputs
Files are saved next to the selected CSV:
- `resultado_exe1_regressao.csv`
- `grafico_exe1_regressao.png`
- `relatorio_exe1_regressao.pdf`

The output CSV includes:
- original observation
- `x`
- `y`
- `y_estimado`
- `residuo`

### Programmatic usage
There is no dedicated CLI wrapper. For automation, call `app/regressao.py` from Python:
```python
from pathlib import Path
from app.regressao import run_pipeline

stats_text, df_out, fig, csv_path, png_path = run_pipeline(Path("dados.csv"))
```

### Relevant structure
- `app/gui.py`: GUI
- `app/regressao.py`: cleanup, fitting, and export pipeline
- `dados.csv`: sample input

### Notes
- Comma-decimal values are converted automatically.
- Invalid rows are dropped before fitting.
- On Linux, Tkinter may require `python3-tk`.

### Troubleshooting
- **Missing columns**: confirm the exact CSV column names.
- **PDF not generated**: run the regression before clicking **Gerar PDF**.
