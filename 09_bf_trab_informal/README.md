# 09_bf_trab_informal

**Idioma / Language:** [Português](#pt-br) | [English](#en)

---

## PT-BR

Aplicação em Python para a atividade 09 de análise de trabalho informal e Bolsa Família, extraindo séries da planilha `DadosEconometria.xlsx`, consolidando os dados em JSON, calculando correlações e co-movimento, estimando modelos econométricos e gerando gráficos em `data/output/`.

### Documentação da atividade
Para uma documentação completa, autônoma e bilíngue sobre objetivo, base, método, resultados, interpretação e referências da atividade, veja [docs/objetivo_resultados.md](docs/objetivo_resultados.md).

### Contexto do exercício
O exercício combina séries mensais e trimestrais para investigar a relação entre beneficiários do Bolsa Família e indicadores do mercado de trabalho, com foco em informalidade, ocupação e desocupação.

As séries lidas da planilha incluem:
- `bolsa_familia`: pessoas beneficiárias no PBF em frequência mensal
- `taxa_informalidade`: taxa de informalidade das pessoas ocupadas
- `pessoas_informais_mil`: pessoas ocupadas em situação de informalidade
- `pessoas_ocupadas_mil`: pessoas ocupadas
- `pessoas_desocupadas_mil`: pessoas desocupadas
- `taxa_desocupacao`: taxa de desocupação
- `forca_trabalho_mil`: pessoas na força de trabalho
- `fora_forca_trabalho_mil`: pessoas fora da força de trabalho

### Como funciona
1. Lê a planilha Excel e extrai séries específicas de abas pré-definidas.
2. Normaliza datas, converte trimestres e limpa valores numéricos.
3. Agrega a série mensal do Bolsa Família em média trimestral.
4. Monta bases pareadas por trimestre para correlação e co-movimento.
5. Calcula correlações em nível e em variação para informalidade e quantidade de informais.
6. Estima cinco modelos OLS com erros-padrão HAC via `statsmodels`.
7. Exporta um JSON consolidado e gráficos de séries, correlação, co-movimento, ajuste dos modelos e testes t/F.

### Requisitos
- Python 3.10+
- Dependências instaladas a partir do `requirements.txt` da raiz do repositório
- Arquivo `data/input/DadosEconometria.xlsx` disponível

### Instalação
```bash
cd 09_bf_trab_informal
python -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
```

Se quiser instalar apenas o necessário para esta activity:
```bash
pip install pandas numpy matplotlib statsmodels scipy openpyxl
```

### Linha de comando
Execução pelo script principal:
```bash
cd 09_bf_trab_informal
python bf_trab_informal.py
```

Execução pelo módulo:
```bash
cd 09_bf_trab_informal
python -m app
```

Com caminhos customizados:
```bash
cd 09_bf_trab_informal
python bf_trab_informal.py --arquivo data/input/DadosEconometria.xlsx --saida data/output
```

### Saídas
- `data/output/series_extraidas.json`
- `data/output/graficos_series/`
- `data/output/graficos_correlacoes/`
- `data/output/graficos_comovimento/`
- `data/output/graficos_econometria/`

Arquivos normalmente gerados:
- `data/output/graficos_series/*.png`: séries extraídas e formatadas
- `data/output/graficos_correlacoes/*.png`: séries padronizadas, dispersões em nível e dispersões em variação
- `data/output/graficos_comovimento/*.png`: comparação por z-score e índice base 100
- `data/output/graficos_econometria/*_ajuste.png`: observado versus ajustado por modelo
- `data/output/graficos_econometria/*_teste_t.png`: significância individual dos coeficientes ligados ao Bolsa Família
- `data/output/graficos_econometria/*_teste_f.png`: significância conjunta dos coeficientes do Bolsa Família
- `data/output/graficos_econometria/resumo_testes_bolsa_familia_modelos.png`: quadro consolidado dos testes

### Modelos econométricos
Os modelos estimados são:
- `modelo_simples_nivel_logaritmico`: `ln_informal ~ ln_bf`
- `modelo_principal_variacoes_logaritmicas`: `d_ln_informal ~ d_ln_bf + d_ln_bf_lag1 + d_ln_ocupados + d_taxa_desocupacao + pos_2023 + dummies trimestrais`
- `modelo_principal_variacoes_logaritmicas_sem_dummies`: mesma especificação principal sem dummies sazonais
- `modelo_secundario_nivel_logaritmico`: `ln_informal ~ ln_bf + ln_ocupados + taxa_desocupacao + tendencia + pos_2023 + dummies trimestrais`
- `modelo_secundario_nivel_logaritmico_sem_dummies`: mesma especificação em nível sem dummies sazonais

Todos os modelos usam:
- estimação por OLS
- erros-padrão HAC de Newey-West com `maxlags=1`
- testes t para coeficientes individuais
- testes F para hipóteses associadas aos coeficientes do Bolsa Família

### Estrutura relevante
- `app/analise.py`: pipeline completa de extração, agregação, correlação, econometria e exportação
- `app/__main__.py`: entrada para `python -m app`
- `bf_trab_informal.py`: ponto de entrada em CLI
- `data/input/DadosEconometria.xlsx`: base padrão da atividade
- `data/output/`: diretório padrão de saída

### Observações
- A atividade não possui interface gráfica; o fluxo é totalmente por linha de comando.
- O código define `MPLCONFIGDIR=/tmp/matplotlib` para evitar problemas de cache do Matplotlib em ambientes restritos.
- A agregação trimestral do Bolsa Família marca quais trimestres têm três meses observados e a base econométrica usa apenas trimestres completos.
- As variações trimestrais são consideradas apenas quando há trimestres consecutivos disponíveis.

### Troubleshooting
- **Arquivo de entrada não encontrado**: confirme a existência de `data/input/DadosEconometria.xlsx` ou informe `--arquivo` com o caminho correto.
- **Erro ao ler Excel**: valide nomes de abas, estrutura da planilha e disponibilidade de `openpyxl`.
- **Gráficos não gerados**: verifique se a pasta de saída tem permissão de escrita e se houve dados válidos após a limpeza.
- **Resultados econométricos com poucas observações**: confira se a série mensal do Bolsa Família tem meses suficientes para formar trimestres completos.

---

## EN

Python app for activity 09 on informal labor and Bolsa Familia analysis, extracting series from `DadosEconometria.xlsx`, consolidating the data into JSON, computing correlations and co-movement, estimating econometric models, and generating charts in `data/output/`.

### Activity documentation
For a complete, self-contained, bilingual explanation of the activity objective, dataset, method, results, interpretation, and references, see [docs/objetivo_resultados.md](docs/objetivo_resultados.md).

### Exercise context
The exercise combines monthly and quarterly series to investigate the relationship between Bolsa Familia beneficiaries and labor-market indicators, focusing on informality, employment, and unemployment.

The spreadsheet series include:
- `bolsa_familia`: Bolsa Familia beneficiaries at monthly frequency
- `taxa_informalidade`: informality rate among employed people
- `pessoas_informais_mil`: employed people in informal work
- `pessoas_ocupadas_mil`: employed people
- `pessoas_desocupadas_mil`: unemployed people
- `taxa_desocupacao`: unemployment rate
- `forca_trabalho_mil`: labor force
- `fora_forca_trabalho_mil`: people outside the labor force

### How it works
1. Reads the Excel spreadsheet and extracts specific series from predefined sheets.
2. Normalizes dates, converts quarters, and cleans numeric values.
3. Aggregates the monthly Bolsa Familia series into quarterly averages.
4. Builds quarter-matched datasets for correlation and co-movement analysis.
5. Computes level and change correlations for informality rate and number of informal workers.
6. Estimates five OLS models with HAC standard errors via `statsmodels`.
7. Exports a consolidated JSON file and charts for series, correlation, co-movement, model fit, and t/F tests.

### Requirements
- Python 3.10+
- Dependencies installed from the repository root `requirements.txt`
- `data/input/DadosEconometria.xlsx` available

### Installation
```bash
cd 09_bf_trab_informal
python -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
```

If you want only the packages used by this activity:
```bash
pip install pandas numpy matplotlib statsmodels scipy openpyxl
```

### CLI usage
Run through the main script:
```bash
cd 09_bf_trab_informal
python bf_trab_informal.py
```

Run through the module:
```bash
cd 09_bf_trab_informal
python -m app
```

With custom paths:
```bash
cd 09_bf_trab_informal
python bf_trab_informal.py --arquivo data/input/DadosEconometria.xlsx --saida data/output
```

### Outputs
- `data/output/series_extraidas.json`
- `data/output/graficos_series/`
- `data/output/graficos_correlacoes/`
- `data/output/graficos_comovimento/`
- `data/output/graficos_econometria/`

Common generated files:
- `data/output/graficos_series/*.png`: extracted and formatted time series
- `data/output/graficos_correlacoes/*.png`: standardized series, level scatter plots, and change scatter plots
- `data/output/graficos_comovimento/*.png`: z-score and base-100 comparisons
- `data/output/graficos_econometria/*_ajuste.png`: observed versus fitted values by model
- `data/output/graficos_econometria/*_teste_t.png`: individual significance of Bolsa Familia coefficients
- `data/output/graficos_econometria/*_teste_f.png`: joint significance of Bolsa Familia coefficients
- `data/output/graficos_econometria/resumo_testes_bolsa_familia_modelos.png`: consolidated test summary

### Econometric models
The estimated models are:
- `modelo_simples_nivel_logaritmico`: `ln_informal ~ ln_bf`
- `modelo_principal_variacoes_logaritmicas`: `d_ln_informal ~ d_ln_bf + d_ln_bf_lag1 + d_ln_ocupados + d_taxa_desocupacao + pos_2023 + quarterly dummies`
- `modelo_principal_variacoes_logaritmicas_sem_dummies`: same main specification without seasonal dummies
- `modelo_secundario_nivel_logaritmico`: `ln_informal ~ ln_bf + ln_ocupados + taxa_desocupacao + tendencia + pos_2023 + quarterly dummies`
- `modelo_secundario_nivel_logaritmico_sem_dummies`: same level specification without seasonal dummies

All models use:
- OLS estimation
- HAC Newey-West standard errors with `maxlags=1`
- t-tests for individual coefficients
- F-tests for hypotheses tied to Bolsa Familia coefficients

### Relevant structure
- `app/analise.py`: full extraction, aggregation, correlation, econometrics, and export pipeline
- `app/__main__.py`: entry point for `python -m app`
- `bf_trab_informal.py`: CLI entry point
- `data/input/DadosEconometria.xlsx`: default activity dataset
- `data/output/`: default output directory

### Notes
- This activity does not include a GUI; the workflow is entirely command-line based.
- The code sets `MPLCONFIGDIR=/tmp/matplotlib` to avoid Matplotlib cache issues in restricted environments.
- The quarterly Bolsa Familia aggregation marks which quarters contain all three observed months, and the econometric base keeps only complete quarters.
- Quarterly changes are only computed when consecutive quarters are available.

### Troubleshooting
- **Input file not found**: confirm that `data/input/DadosEconometria.xlsx` exists or pass the correct path with `--arquivo`.
- **Excel read error**: validate sheet names, spreadsheet structure, and `openpyxl` availability.
- **Charts not generated**: verify write permission in the output folder and confirm that valid data remained after cleaning.
- **Econometric results with too few observations**: check whether the monthly Bolsa Familia series contains enough months to build complete quarters.
