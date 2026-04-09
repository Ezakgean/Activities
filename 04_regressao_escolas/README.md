# 04_regressao_escolas

**Idioma / Language:** [Portugues](#pt-br) | [English](#en)

---

## PT-BR

Aplicacao em Python para analisar o exercicio de regressao escolar da atividade 04, com interface grafica, regressao linear simples e multipla, exportacao de tabelas e geracao de PDF.

### Contexto do exercicio
O programa ficticio visa melhorar o desempenho escolar dos alunos do ensino fundamental. Ele foi desenvolvido com 245 alunos de uma Escola Estadual, que possui 745 alunos ao todo.

O desenho original do programa nao contemplava uma avaliacao de impacto. Essa avaliacao foi implementada apenas apos um ano de funcionamento do programa, de modo que so foi possivel observar os dados em um unico momento no tempo, depois da implementacao.

O banco de dados apresenta informacoes sobre a nota no exame de proficiencia, a participacao no programa, o sexo do aluno (`mulher = 1`, `0` caso contrario), a cor (`branco = 1`, `0` caso contrario) e os anos de estudo da mae.

### Como funciona
1. Carrega a planilha Excel com os dados da atividade.
2. Valida as colunas obrigatorias.
3. Calcula estatisticas descritivas por grupo tratado.
4. Executa testes t para `nota` e `estudo_mae`.
5. Ajusta tres modelos de regressao:
   - `nota ~ tratado`
   - `nota ~ estudo_mae`
   - `nota ~ tratado + mulher + cor + estudo_mae`
6. Gera grafico, arquivos CSV, resumo em texto e PDF opcional.

### Colunas obrigatorias no Excel
- `nota`
- `tratado`: participacao no programa
- `mulher`: indicador binario para sexo feminino
- `cor`: indicador binario para aluno branco
- `estudo_mae`: anos de estudo da mae

### Requisitos
- Python 3.10+
- Dependencias instaladas a partir do `requirements.txt` da raiz do repositorio

### Instalacao
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
```

### Interface grafica (recomendado)
```bash
cd 04_regressao_escolas
python -m app
```

Na GUI:
- escolha a planilha Excel
- escolha a pasta de saida
- clique em **Executar**
- opcionalmente clique em **Gerar PDF**

### Uso em linha de comando
```bash
cd 04_regressao_escolas
python regressao_escolas.py --arquivo data/input/"EXE 2.xlsx" --saida data/output --pdf
```

### Saidas
- `data/output/resumo_regressao_escolas.txt`
- `data/output/estatisticas_descritivas.csv`
- `data/output/testes_t.csv`
- `data/output/coeficientes_regressoes.csv`
- `data/output/grafico_estudo_mae.png`
- `data/output/relatorio_regressao_escolas.pdf` (opcional)

### Estrutura de pastas relevante
- `app/gui.py`: interface grafica.
- `app/regressao.py`: pipeline da analise e exportacao de arquivos.
- `data/input/EXE 2.xlsx`: planilha padrao da atividade.
- `data/output/`: destino padrao das saidas.
- `Regressão.Rmd`: referencia original em R.

### Observacoes
- O carregamento do `.xlsx` tem fallback interno e continua funcionando mesmo sem `openpyxl`.
- No Linux, o Tkinter pode exigir o pacote `python3-tk`.

---

## EN

Python app for the school-regression exercise in activity 04, with GUI, simple and multiple linear regression, table exports, and optional PDF output.

### Exercise context
The fictional program aims to improve the school performance of elementary school students. It was developed with 245 students from a state school that has 745 students in total.

The original program design did not include an impact evaluation. That evaluation was implemented only after one year of operation, so the available data were collected at a single point in time after the program had already been implemented.

The dataset includes information on proficiency test scores, program participation, sex (`mulher = 1`, `0` otherwise), race/color (`branco = 1`, `0` otherwise), and the mother's years of schooling.

### How it works
1. Loads the Excel spreadsheet for the exercise.
2. Validates required columns.
3. Computes descriptive statistics by treatment group.
4. Runs t-tests for `nota` and `estudo_mae`.
5. Fits three regression models:
   - `nota ~ tratado`
   - `nota ~ estudo_mae`
   - `nota ~ tratado + mulher + cor + estudo_mae`
6. Generates a plot, CSV outputs, text summary, and optional PDF.

### Required Excel columns
- `nota`
- `tratado`: program participation
- `mulher`: binary indicator for female student
- `cor`: binary indicator for white student
- `estudo_mae`: mother's years of schooling

### Requirements
- Python 3.10+
- Dependencies installed from the repository root `requirements.txt`

### Installation
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
```

### GUI (recommended)
```bash
cd 04_regressao_escolas
python -m app
```

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
- `data/output/relatorio_regressao_escolas.pdf` (optional)

### Relevant folder structure
- `app/gui.py`: GUI layer.
- `app/regressao.py`: analysis pipeline and file export logic.
- `data/input/EXE 2.xlsx`: default input spreadsheet.
- `data/output/`: default output directory.
- `Regressão.Rmd`: original R reference.
