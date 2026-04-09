# 05_salario_x_escolaridade

**Idioma / Language:** [Português](#pt-br) | [English](#en)

---

## PT-BR

Aplicação em Python para analisar salários por escolaridade com base em `profissoes_15_estados_salarios_estimados.json`, ajustando uma regressão OLS por estado e apresentando o resultado em uma interface executiva chamada **Salário por Escolaridade**.

### Contexto da base
O JSON reúne 200 profissões em 15 estados brasileiros, com salários médios estimados por UF. A base inclui:
- profissão
- grupo ocupacional
- indicação se a ocupação exige ensino superior
- salário médio estimado por estado

### Como a escolaridade foi modelada
A base não traz anos de estudo. Por isso, a escolaridade foi representada como uma proxy binária:
- `1`: profissão com exigência de ensino superior
- `0`: profissão sem exigência de ensino superior

Em cada UF, o modelo estimado é:
```text
salario = beta0 + beta1 * ensino_superior
```

Interpretação:
- `beta0`: salário médio estimado para ocupações sem exigência de ensino superior
- `beta1`: prêmio salarial associado ao grupo com exigência de ensino superior

### Como funciona
1. Carrega o JSON com `metadata` e `professions`.
2. Achata a base para o nível `profissão x estado`.
3. Constrói a variável binária de escolaridade.
4. Ajusta uma regressão OLS por UF.
5. Exporta base analítica, médias e coeficientes.
6. Gera dashboard PNG e PDF opcional.

### Requisitos
- Python 3.10+
- Dependências instaladas a partir do `requirements.txt` da raiz do repositório

### Instalação
```bash
cd 05_salario_x_escolaridade
python -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
```

### Interface gráfica
```bash
cd 05_salario_x_escolaridade
python -m app
```

Na GUI:
- use a tela `Execução` para selecionar o JSON e a pasta de saída
- rode a análise e acompanhe o status da rodada
- navegue pelo menu superior entre `Dashboard`, `Resumo`, `Regressões`, `Médias` e `Arquivos`
- use **Gerar PDF** após a execução, se quiser consolidar o relatório

Detalhes da interface atual:
- o dashboard é exibido em painel próprio, com cards fora do canvas para evitar sobreposição
- os gráficos foram reorganizados verticalmente para leitura por UF
- as tabelas de `Regressões` e `Médias` usam faixas alternadas por estado para facilitar a leitura

### Linha de comando
```bash
cd 05_salario_x_escolaridade
python salario_escolaridade.py --arquivo data/input/profissoes_15_estados_salarios_estimados.json --saida data/output --pdf
```

### Saídas
- `data/output/resumo_regressao_salario_escolaridade.txt`
- `data/output/base_profissoes_estado.csv`
- `data/output/medias_salariais_estado_escolaridade.csv`
- `data/output/regressoes_por_estado.csv`
- `data/output/dashboard_salario_escolaridade.png`
- `data/output/relatorio_salario_escolaridade.pdf`

### Estrutura relevante
- `app/gui.py`: interface gráfica, navegação entre telas e renderização do dashboard
- `app/analise.py`: leitura do JSON, regressões por estado e geração dos artefatos
- `data/input/profissoes_15_estados_salarios_estimados.json`: base padrão da atividade
- `data/output/`: diretório padrão de saída
- `salario_escolaridade.py`: ponto de entrada em CLI

### Observações
- A interpretação correta do modelo é associativa, não causal.
- O coeficiente da regressão equivale a uma diferença média entre grupos com e sem exigência de superior.
- O dashboard foi otimizado para leitura em telas menores, com espaçamento extra no cabeçalho e área rolável no painel.
- No Linux, o Tkinter pode exigir `python3-tk`.

### Conclusões da atividade
- O prêmio salarial associado ao ensino superior aparece em todas as UFs da base.
- Estados com maior renda média tendem a apresentar maiores prêmios absolutos.
- A análise é mais útil para comparar níveis e diferenças entre estados do que para inferir causalidade individual.

---

## EN

Python app to analyze salaries by schooling using `profissoes_15_estados_salarios_estimados.json`, fitting one OLS regression per state and presenting the result through an executive interface named **Salário por Escolaridade**.

### Dataset context
The JSON contains 200 professions across 15 Brazilian states, with estimated average salaries by state. The dataset includes:
- profession
- occupational group
- whether the occupation requires higher education
- estimated average salary by state

### How schooling was modeled
The dataset does not include years of study. Because of that, schooling is represented as a binary proxy:
- `1`: profession requires higher education
- `0`: profession does not require higher education

For each state, the estimated model is:
```text
salary = beta0 + beta1 * higher_education
```

Interpretation:
- `beta0`: estimated average salary for occupations without a higher-education requirement
- `beta1`: salary premium associated with occupations that require higher education

### How it works
1. Loads the JSON with `metadata` and `professions`.
2. Flattens the dataset to the `profession x state` level.
3. Builds the binary schooling variable.
4. Fits one OLS regression per state.
5. Exports the analytical base, averages, and coefficients.
6. Generates a PNG dashboard and an optional PDF.

### Requirements
- Python 3.10+
- Dependencies installed from the repository root `requirements.txt`

### Installation
```bash
cd 05_salario_x_escolaridade
python -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
```

### GUI
```bash
cd 05_salario_x_escolaridade
python -m app
```

Inside the GUI:
- use the `Execução` screen to select the JSON input and output folder
- run the analysis and monitor the current run status
- navigate through `Dashboard`, `Resumo`, `Regressões`, `Médias`, and `Arquivos`
- use **Gerar PDF** after execution if you want the consolidated report

Current UI notes:
- the dashboard keeps summary cards outside the matplotlib canvas to reduce overlap
- charts are stacked vertically for state-by-state reading
- `Regressões` and `Médias` tables use alternating state bands for easier scanning

### CLI usage
```bash
cd 05_salario_x_escolaridade
python salario_escolaridade.py --arquivo data/input/profissoes_15_estados_salarios_estimados.json --saida data/output --pdf
```

### Outputs
- `data/output/resumo_regressao_salario_escolaridade.txt`
- `data/output/base_profissoes_estado.csv`
- `data/output/medias_salariais_estado_escolaridade.csv`
- `data/output/regressoes_por_estado.csv`
- `data/output/dashboard_salario_escolaridade.png`
- `data/output/relatorio_salario_escolaridade.pdf`

### Relevant structure
- `app/gui.py`: GUI, screen navigation, and dashboard rendering
- `app/analise.py`: JSON loading, state regressions, and artifact generation
- `data/input/profissoes_15_estados_salarios_estimados.json`: default activity dataset
- `data/output/`: default output directory
- `salario_escolaridade.py`: CLI entry point

### Notes
- The correct interpretation is associative rather than causal.
- The regression coefficient works as a mean difference between occupations with and without a higher-education requirement.
- The dashboard was optimized for smaller screens, with extra header spacing and a scrollable panel.
- On Linux, Tkinter may require `python3-tk`.

### Activity conclusions
- The higher-education salary premium appears in every state in the dataset.
- States with higher average income tend to show larger absolute premiums.
- The analysis is more useful for comparing levels and gaps across states than for inferring individual causality.
