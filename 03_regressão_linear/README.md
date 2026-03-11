# 03_regressao_linear

**Idioma / Language:** [Português](#pt-br) | [English](#en)

---

## PT-BR

Aplicacao em Python para **regressao linear simples** (OLS) entre renda e despesas com alimentacao, com interface grafica, grafico e relatorio em PDF.

### Como funciona
1. Carrega o CSV e valida as colunas obrigatorias.
2. Converte valores com virgula decimal para float.
3. Remove linhas invalidas.
4. Ajusta regressao linear (OLS) com `statsmodels`.
5. Gera resultados, grafico, CSV de saida e PDF.

### Colunas obrigatorias no CSV
- `observações`
- `x - renda`
- `y - despesas com alimentação`

### Requisitos
- Python 3.10+
- Dependencias em `requirements.txt`

### Instalacao
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Interface grafica (recomendado)
```bash
cd 03_regressão_linear
python -m app
```
Selecione o CSV e clique em **Executar**. Depois, use **Gerar PDF** para criar o relatorio.

### Saidas
- `resultado_exe1_regressao.csv`: dados com `y_estimado` e `residuo`.
- `grafico_exe1_regressao.png`: grafico com pontos e linha de regressao.
- `relatorio_exe1_regressao.pdf`: formulas, resumo estatistico e grafico.

### Estrutura de pastas relevante
- `app/gui.py`: interface grafica.
- `app/regressao.py`: pipeline de regressao e geracao de arquivos.
- `dados.csv`: exemplo de entrada.

### Observacoes
- Valores com virgula decimal sao convertidos automaticamente.
- Linhas invalidas sao removidas antes do ajuste.
- No Linux, o Tkinter pode exigir o pacote `python3-tk`.

### Troubleshooting
- **Erro de colunas ausentes**: confirme os nomes exatos das colunas.
- **PDF nao gerado**: execute a regressao antes de clicar em **Gerar PDF**.

---

## EN

Python app for **simple linear regression** (OLS) between income and food expenses, with GUI, plot, and PDF report.

### How it works
1. Loads the CSV and validates required columns.
2. Converts comma-decimal values to float.
3. Drops invalid rows.
4. Fits linear regression (OLS) with `statsmodels`.
5. Generates results, plot, output CSV, and PDF.

### Required CSV columns
- `observações`
- `x - renda`
- `y - despesas com alimentação`

### Requirements
- Python 3.10+
- Dependencies in `requirements.txt`

### Installation
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### GUI (recommended)
```bash
cd 03_regressão_linear
python -m app
```
Select the CSV and click **Executar**. Then use **Gerar PDF** to create the report.

### Outputs
- `resultado_exe1_regressao.csv`: data with `y_estimado` and `residuo`.
- `grafico_exe1_regressao.png`: plot with points and regression line.
- `relatorio_exe1_regressao.pdf`: formulas, statistical summary, and plot.

### Relevant folder structure
- `app/gui.py`: GUI.
- `app/regressao.py`: regression pipeline and file outputs.
- `dados.csv`: sample input.

### Notes
- Comma-decimal values are converted automatically.
- Invalid rows are removed before fitting.
- On Linux, Tkinter may require the `python3-tk` package.

### Troubleshooting
- **Missing columns**: confirm exact column names.
- **PDF not generated**: run the regression before clicking **Gerar PDF**.
