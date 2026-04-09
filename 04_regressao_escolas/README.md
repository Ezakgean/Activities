# 04_regressao_escolas

**Idioma / Language:** [Português](#pt-br) | [English](#en)

---

## PT-BR

Aplicação em Python para analisar a atividade 04 de regressão escolar, combinando estatísticas descritivas, testes t, regressão linear simples, regressão múltipla, interface gráfica e exportação de relatórios.

### Contexto do exercício
O exercício trabalha com um programa fictício voltado à melhora do desempenho escolar no ensino fundamental. A base disponível foi observada apenas após a implementação do programa, então a análise é observacional e não corresponde a um desenho experimental clássico.

A planilha contém:
- `nota`: desempenho no teste de proficiência
- `tratado`: participação no programa
- `mulher`: indicador binário para sexo feminino
- `cor`: indicador binário para aluno branco
- `estudo_mae`: anos de estudo da mãe

### Como funciona
1. Carrega a planilha Excel.
2. Valida as colunas obrigatórias.
3. Calcula estatísticas descritivas por grupo tratado.
4. Executa testes t para `nota` e `estudo_mae`.
5. Ajusta três modelos:
   - `nota ~ tratado`
   - `nota ~ estudo_mae`
   - `nota ~ tratado + mulher + cor + estudo_mae`
6. Gera resumo em texto, tabelas CSV, gráfico e PDF opcional.

### Requisitos
- Python 3.10+
- Dependências instaladas a partir do `requirements.txt` da raiz do repositório

### Instalação
```bash
cd 04_regressao_escolas
python -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
```

### Interface gráfica
```bash
cd 04_regressao_escolas
python -m app
```

Na GUI:
- selecione a planilha Excel
- escolha a pasta de saída
- clique em **Executar**
- gere o PDF depois da análise, se necessário

### Linha de comando
```bash
cd 04_regressao_escolas
python regressao_escolas.py --arquivo data/input/"EXE 2.xlsx" --saida data/output --pdf
```

### Saídas
- `data/output/resumo_regressao_escolas.txt`
- `data/output/estatisticas_descritivas.csv`
- `data/output/testes_t.csv`
- `data/output/coeficientes_regressoes.csv`
- `data/output/grafico_estudo_mae.png`
- `data/output/relatorio_regressao_escolas.pdf`

### Estrutura relevante
- `app/gui.py`: interface gráfica
- `app/regressao.py`: pipeline estatístico e exportação
- `data/input/EXE 2.xlsx`: base padrão da atividade
- `data/output/`: diretório padrão de saída
- `regressao_escolas.py`: ponto de entrada em CLI
- `Regressão.Rmd`: referência original em R

### Observações
- O carregamento do `.xlsx` possui fallback interno e segue funcionando mesmo sem `openpyxl`.
- A leitura correta dos resultados é associativa, especialmente no modelo múltiplo.
- No Linux, o Tkinter pode exigir `python3-tk`.

### Troubleshooting
- **Erro ao ler Excel**: confirme o caminho do arquivo e o formato da planilha.
- **PDF não gerado**: execute a análise antes de clicar em **Gerar PDF**.
- **Colunas ausentes**: valide os nomes exatos esperados pela atividade.

---

## EN

Python app for activity 04 school-regression analysis, combining descriptive statistics, t-tests, simple and multiple linear regression, GUI, and report export.

### Exercise context
The exercise uses a fictional program aimed at improving elementary-school performance. The available dataset was observed only after the program was implemented, so the analysis is observational rather than a classic experimental design.

The spreadsheet includes:
- `nota`: proficiency-test score
- `tratado`: program participation
- `mulher`: binary indicator for female student
- `cor`: binary indicator for white student
- `estudo_mae`: mother's years of schooling

### How it works
1. Loads the Excel spreadsheet.
2. Validates required columns.
3. Computes descriptive statistics by treatment group.
4. Runs t-tests for `nota` and `estudo_mae`.
5. Fits three models:
   - `nota ~ tratado`
   - `nota ~ estudo_mae`
   - `nota ~ tratado + mulher + cor + estudo_mae`
6. Generates a text summary, CSV tables, chart, and optional PDF.

### Requirements
- Python 3.10+
- Dependencies installed from the repository root `requirements.txt`

### Installation
```bash
cd 04_regressao_escolas
python -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
```

### GUI
```bash
cd 04_regressao_escolas
python -m app
```

Inside the GUI:
- select the Excel file
- choose the output folder
- click **Executar**
- generate the PDF after the analysis if needed

### CLI usage
```bash
cd 04_regressao_escolas
python regressao_escolas.py --arquivo data/input/"EXE 2.xlsx" --saida data/output --pdf
```

### Outputs
- `data/output/resumo_regressao_escolas.txt`
- `data/output/estatisticas_descritivas.csv`
- `data/output/testes_t.csv`
- `data/output/coeficientes_regressoes.csv`
- `data/output/grafico_estudo_mae.png`
- `data/output/relatorio_regressao_escolas.pdf`

### Relevant structure
- `app/gui.py`: GUI
- `app/regressao.py`: statistical pipeline and export logic
- `data/input/EXE 2.xlsx`: default dataset
- `data/output/`: default output directory
- `regressao_escolas.py`: CLI entry point
- `Regressão.Rmd`: original R reference

### Notes
- `.xlsx` loading has an internal fallback and continues to work even without `openpyxl`.
- The safest interpretation of results is associative, especially for the multiple-regression model.
- On Linux, Tkinter may require `python3-tk`.

### Troubleshooting
- **Excel read error**: confirm the file path and spreadsheet format.
- **PDF not generated**: run the analysis before clicking **Gerar PDF**.
- **Missing columns**: validate the exact column names expected by the activity.
