# 05_salario_x_escolaridade

**Idioma / Language:** [Portugues](#pt-br) | [English](#en)

---

## PT-BR

Aplicacao em Python para analisar a relacao entre salario e escolaridade a partir da base `profissoes_15_estados_salarios_estimados.json`, ajustando uma regressao linear por estado e gerando um dashboard final com o mesmo branding visual dos modulos anteriores.

### Contexto da base
O JSON contem 200 profissoes em 15 estados brasileiros, com salarios medios estimados por UF. A base inclui:
- nome da profissao
- grupo ocupacional
- indicacao se a profissao exige ensino superior (`requires_higher_education`)
- salario medio estimado por estado

### Importante sobre a variavel de escolaridade
A base nao traz anos de estudo. Por isso, a escolaridade foi modelada como uma proxy binaria:
- `1`: profissao com exigencia de ensino superior
- `0`: profissao sem exigencia de ensino superior

Assim, a regressao em cada estado segue a forma:
```text
salario = beta0 + beta1 * ensino_superior
```

Nessa leitura:
- `beta0`: salario medio estimado para profissoes sem exigencia de ensino superior
- `beta1`: premio salarial associado a profissoes com exigencia de ensino superior

### Como funciona
1. Carrega o JSON com metadata e profissoes.
2. Achata a base para o nivel `profissao x estado`.
3. Construi a variavel binaria de escolaridade a partir de `requires_higher_education`.
4. Ajusta uma regressao OLS por UF.
5. Exporta tabelas consolidadas com base analitica, medias e coeficientes.
6. Gera um dashboard em PNG e um PDF opcional.

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
cd 05_salario_x_escolaridade
python -m app
```

Na GUI:
- use `Execucao` no menu superior para selecionar o arquivo JSON, definir a pasta de saida e rodar a analise
- navegue pelo menu superior entre `Execucao`, `Dashboard`, `Resumo`, `Regressoes`, `Medias` e `Arquivos`
- opcionalmente clique em **Gerar PDF**

### Uso em linha de comando
```bash
cd 05_salario_x_escolaridade
python salario_escolaridade.py --arquivo data/input/profissoes_15_estados_salarios_estimados.json --saida data/output --pdf
```

### Saidas
- `data/output/resumo_regressao_salario_escolaridade.txt`
- `data/output/base_profissoes_estado.csv`
- `data/output/medias_salariais_estado_escolaridade.csv`
- `data/output/regressoes_por_estado.csv`
- `data/output/dashboard_salario_escolaridade.png`
- `data/output/relatorio_salario_escolaridade.pdf` (opcional)

### Estrutura de pastas relevante
- `app/gui.py`: interface grafica com dashboard.
- `app/analise.py`: pipeline da leitura do JSON, regressao por UF e exportacao.
- `data/input/profissoes_15_estados_salarios_estimados.json`: base padrao da atividade.
- `data/output/`: destino padrao das saidas.
- `salario_escolaridade.py`: ponto de entrada em CLI.

### Observacoes
- O dashboard segue o padrao visual dos modulos `03_` e `04_`.
- A interface agora usa um shell visual com menu superior, inspirado em dashboard executivo, e a etapa de execucao virou uma tela propria.
- Como a escolaridade foi representada por um dummy binario, o coeficiente da regressao equivale a uma diferenca de medias entre os dois grupos.
- No Linux, o Tkinter pode exigir o pacote `python3-tk`.

### Conclusoes
- A base aponta uma associacao positiva e consistente entre exigencia de ensino superior e salarios estimados mais altos em todos os 15 estados.
- No agregado da base, a media salarial estimada das profissoes sem exigencia de ensino superior fica em torno de `R$ 2,2 mil`, enquanto a das profissoes com exigencia de ensino superior fica em torno de `R$ 6,2 mil`.
- O premio salarial aparece em todas as UFs e cresce em termos absolutos nos estados com maior nivel geral de renda, como `SP`, `RS`, `SC`, `RJ` e `PR`.
- Como os salarios do JSON sao estimados e a escolaridade foi modelada por um dummy binario, a leitura correta e associativa, nao causal.
- O uso mais defensavel do resultado e comparar o tamanho do premio salarial e o nivel previsto de salarios entre estados.

---

## EN

Python app to analyze the relationship between salary and schooling using `profissoes_15_estados_salarios_estimados.json`, fitting one linear regression per state and generating a final dashboard with the same visual branding used in the previous modules.

### Dataset context
The JSON contains 200 professions across 15 Brazilian states, with estimated average salaries by state. The dataset includes:
- profession name
- occupational group
- whether the profession requires higher education (`requires_higher_education`)
- estimated average salary by state

### Important note about the schooling variable
The dataset does not include years of schooling. Because of that, schooling is modeled as a binary proxy:
- `1`: profession requires higher education
- `0`: profession does not require higher education

Each state-level regression follows:
```text
salary = beta0 + beta1 * higher_education
```

Interpretation:
- `beta0`: estimated average salary for professions without a higher-education requirement
- `beta1`: salary premium associated with professions that require higher education

### How it works
1. Loads the JSON with metadata and professions.
2. Flattens the dataset to the `profession x state` level.
3. Builds the binary schooling variable from `requires_higher_education`.
4. Fits one OLS regression per state.
5. Exports consolidated analytical data, averages, and regression coefficients.
6. Generates a PNG dashboard and an optional PDF report.

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
cd 05_salario_x_escolaridade
python -m app
```

Inside the GUI, use `Execution` to run the analysis and the top menu to switch between `Execution`, `Dashboard`, `Summary`, `Regressions`, `Means`, and `Files`.

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
- `data/output/relatorio_salario_escolaridade.pdf` (optional)

### Relevant folder structure
- `app/gui.py`: GUI with dashboard output.
- `app/analise.py`: JSON-loading, state-regression, and export pipeline.
- `data/input/profissoes_15_estados_salarios_estimados.json`: default dataset.
- `data/output/`: default output directory.
- `salario_escolaridade.py`: CLI entry point.

### Conclusions
- The dataset indicates a positive and consistent association between higher-education requirements and higher estimated salaries across all 15 states.
- In the pooled data, estimated average salary is around `R$ 2.2k` for professions without a higher-education requirement and around `R$ 6.2k` for professions with that requirement.
- The salary premium appears in every state and is larger in absolute BRL terms in higher-income states such as `SP`, `RS`, `SC`, `RJ`, and `PR`.
- Because the salaries are estimated and schooling is represented by a binary proxy, the correct interpretation is associative rather than causal.
- The most defensible use of the results is to compare the size of the salary premium and the predicted salary levels across states.
