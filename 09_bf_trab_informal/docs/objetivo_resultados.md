# Activity 09 Documentation

**Idioma / Language:** [Português](#pt-br) | [English](#en)

---

## PT-BR

### Visão geral

Esta documentação registra, de forma autônoma, o problema investigado, a base de dados utilizada, as transformações aplicadas nas séries, os modelos estimados, os resultados principais e a interpretação final do exercício.

A implementação da atividade está no arquivo [`../app/analise.py`](../app/analise.py). O programa lê a planilha `DadosEconometria.xlsx`, consolida as séries em JSON, gera gráficos descritivos e estima modelos econométricos com `statsmodels`.

### Objetivo da atividade

A atividade investiga a relação entre o Programa Bolsa Família e o trabalho informal no Brasil. A pergunta central é:

> O aumento no número de beneficiários do Bolsa Família está associado ao aumento da informalidade no mercado de trabalho brasileiro?

O exercício não tenta afirmar causalidade forte. A proposta é verificar se existe associação estatisticamente robusta entre as séries, primeiro em análises descritivas e depois em especificações econométricas com controles para variáveis relevantes do mercado de trabalho.

### Motivação

O tema é relevante porque há um debate recorrente sobre o possível efeito de programas de transferência de renda sobre decisões de trabalho. Em particular, uma hipótese frequentemente levantada é a de que um benefício de grande escala poderia incentivar parte dos beneficiários a permanecer em ocupações informais para reduzir o risco de perda do auxílio.

Ao mesmo tempo, a informalidade no Brasil também responde a fatores estruturais e cíclicos, como:

- nível de ocupação;
- desocupação;
- tendência temporal;
- sazonalidade do mercado de trabalho;
- recuperação econômica no pós-pandemia.

Por isso, a atividade compara um modelo simples, sem controles, com modelos mais completos, capazes de separar melhor associação espúria de evidência estatística mais consistente.

### Fontes de dados

As séries utilizadas foram organizadas a partir de duas fontes públicas principais:

- `SIDRA/IBGE`, tabela 4093, para indicadores trimestrais do mercado de trabalho.
- `Vis Data 3`, do Ministério do Desenvolvimento e Assistência Social, para a série de beneficiários do Bolsa Família.

Referências diretas:

- SIDRA/IBGE, tabela 4093: <https://sidra.ibge.gov.br/tabela/4093>
- Vis Data 3: <https://aplicacoes.cidadania.gov.br/vis/data3/v.php?q%5B%5D=g9ysl9LerqO4gGVrrGyEymipycqv16Km2ffJsKw%3D>

### Séries utilizadas

A atividade trabalha com as seguintes séries:

- `pessoas_beneficiarias_pbf`: número de beneficiários do Bolsa Família, originalmente em frequência mensal;
- `taxa_informalidade`: taxa de informalidade das pessoas ocupadas;
- `pessoas_informais_mil`: número de pessoas ocupadas em situação de informalidade;
- `pessoas_ocupadas_mil`: total de pessoas ocupadas;
- `pessoas_desocupadas_mil`: total de pessoas desocupadas;
- `taxa_desocupacao`: taxa de desocupação;
- `forca_trabalho_mil`: pessoas na força de trabalho;
- `fora_forca_trabalho_mil`: pessoas fora da força de trabalho.

### Preparação da base

O pipeline da atividade faz as seguintes etapas:

1. Lê planilhas específicas do arquivo `data/input/DadosEconometria.xlsx`.
2. Limpa valores numéricos e converte datas e trimestres.
3. Agrega a série mensal de beneficiários do Bolsa Família para média trimestral.
4. Monta bases trimestrais pareadas para análises de correlação.
5. Constrói uma base econométrica única com as variáveis centrais.
6. Mantém apenas trimestres completos para a série do Bolsa Família.
7. Gera transformações em logaritmo, diferenças logarítmicas e variáveis sazonais.

Essa preparação é importante porque o Bolsa Família está originalmente em frequência mensal, enquanto a maior parte dos indicadores de mercado de trabalho está em frequência trimestral.

### Estratégia analítica

O exercício foi dividido em três camadas:

#### 1. Análise descritiva

Geração de gráficos das séries ao longo do tempo para observar tendência, nível e co-movimento.

#### 2. Correlações

Foram calculadas correlações de Pearson:

- em nível;
- em variação trimestral.

As correlações foram avaliadas para dois alvos:

- taxa de informalidade;
- quantidade de pessoas informais.

#### 3. Modelos econométricos

Foram estimados cinco modelos por MQO com erros-padrão robustos HAC de Newey-West com `maxlags=1`, usando `statsmodels`.

Referências metodológicas:

- OLS em `statsmodels`: <https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.OLS.html>
- Covariância robusta HAC em `statsmodels`: <https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.RegressionResults.get_robustcov_results.html>

Os modelos estimados foram:

#### Modelo 1. Simples em nível logarítmico

`ln_informal ~ ln_bf`

Objetivo:
avaliar a associação bruta entre Bolsa Família e quantidade de trabalhadores informais, sem controles.

#### Modelo 2. Principal em variações logarítmicas com dummies sazonais

`d_ln_informal ~ d_ln_bf + d_ln_bf_lag1 + d_ln_ocupados + d_taxa_desocupacao + pos_2023 + dummies trimestrais`

Objetivo:
avaliar se mudanças trimestrais no Bolsa Família explicam mudanças trimestrais na informalidade, controlando por dinâmica do mercado de trabalho e sazonalidade.

#### Modelo 3. Principal em variações logarítmicas sem dummies sazonais

Mesma estrutura do modelo principal, mas sem dummies trimestrais.

Objetivo:
testar a sensibilidade da associação quando o componente sazonal é removido.

#### Modelo 4. Nível logarítmico com controles e dummies sazonais

`ln_informal ~ ln_bf + ln_ocupados + taxa_desocupacao + tendencia + pos_2023 + dummies trimestrais`

Objetivo:
avaliar a relação em nível entre Bolsa Família e informalidade com controles estruturais mais completos.

#### Modelo 5. Nível logarítmico com controles e sem dummies sazonais

Mesma estrutura do modelo anterior, mas sem dummies trimestrais.

Objetivo:
verificar a robustez da associação em nível quando a sazonalidade não é explicitamente modelada.

### Tamanho da amostra

Com base na série consolidada exportada em `data/output/series_extraidas.json`, os modelos usam:

- `36` observações nos modelos em nível;
- `32` observações nos modelos em variações logarítmicas.

A redução nas observações dos modelos em variação ocorre porque:

- diferenças exigem trimestres consecutivos;
- a defasagem de `d_ln_bf` elimina observações adicionais;
- a série do Bolsa Família precisa ter trimestre completo para entrar na base econométrica.

### Resultados descritivos

#### Correlação entre Bolsa Família e taxa de informalidade

- Correlação em nível: `-0,4907`
- Correlação em variação: `-0,3195`

Interpretação:
quando a informalidade é medida como taxa, a associação observada é negativa. Em termos descritivos, períodos com mais beneficiários do programa não coincidem com aumento proporcional da taxa de informalidade.

#### Correlação entre Bolsa Família e número de pessoas informais

- Correlação em nível: `0,5176`
- Correlação em variação: `-0,3447`

Interpretação:
quando a informalidade é medida em quantidade absoluta, a associação em nível é positiva. Ainda assim, essa relação perde força e muda de sinal quando se observam variações trimestrais. Isso sugere que a correlação positiva em nível pode estar refletindo tendência comum ou crescimento simultâneo do mercado de trabalho, e não necessariamente um efeito direto do programa.

### Resultados econométricos

#### Modelo 1. Simples em nível logarítmico

Principais números:

- Observações: `36`
- Coeficiente de `ln_bf`: `0,3308`
- `p-valor` de `ln_bf`: `0,0006`
- `R²`: `0,2664`
- Teste F para `ln_bf = 0`: `p = 0,0016`

Leitura:
o modelo simples mostra associação positiva e estatisticamente significativa entre Bolsa Família e número de trabalhadores informais. No entanto, o poder explicativo é baixo e a especificação não controla por outras forças do mercado de trabalho.

#### Modelo 2. Principal em variações logarítmicas com dummies sazonais

Principais números:

- Observações: `32`
- Coeficiente de `d_ln_bf`: `-0,0126`
- `p-valor` de `d_ln_bf`: `0,7476`
- Coeficiente de `d_ln_bf_lag1`: `0,0880`
- `p-valor` de `d_ln_bf_lag1`: `0,1422`
- Teste F conjunto: `p = 0,3559`
- `R²`: `0,9840`

Leitura:
nem a variação contemporânea nem a variação defasada do Bolsa Família se mostraram estatisticamente significativas. O modelo tem alto `R²`, mas esse poder explicativo vem principalmente dos controles e da sazonalidade, não da variável de Bolsa Família.

#### Modelo 3. Principal em variações logarítmicas sem dummies sazonais

Principais números:

- Observações: `32`
- Coeficiente de `d_ln_bf`: `-0,0302`
- `p-valor` de `d_ln_bf`: `0,5483`
- Coeficiente de `d_ln_bf_lag1`: `0,1836`
- `p-valor` de `d_ln_bf_lag1`: `0,0765`
- Teste F conjunto: `p = 0,1637`
- `R²`: `0,9702`

Leitura:
há apenas evidência fraca para a variável defasada, significativa a 10%, mas a hipótese conjunta para as variáveis do Bolsa Família não é rejeitada. O resultado não é robusto.

#### Modelo 4. Nível logarítmico com controles e dummies sazonais

Principais números:

- Observações: `36`
- Coeficiente de `ln_bf`: `0,0866`
- `p-valor` de `ln_bf`: `0,1363`
- Teste F para `ln_bf = 0`: `p = 0,1479`
- `R²`: `0,9798`

Leitura:
quando se adicionam ocupação, taxa de desocupação, tendência, período pós-2023 e sazonalidade, o Bolsa Família deixa de apresentar significância estatística nos níveis usuais.

#### Modelo 5. Nível logarítmico com controles e sem dummies sazonais

Principais números:

- Observações: `36`
- Coeficiente de `ln_bf`: `0,1299`
- `p-valor` de `ln_bf`: `0,0767`
- Teste F para `ln_bf = 0`: `p = 0,0869`
- `R²`: `0,9637`

Leitura:
sem o controle sazonal, aparece uma evidência apenas fraca a 10%. Ainda assim, o resultado não alcança robustez estatística ao nível de 5% e deve ser interpretado com cautela.

### O que permanece relevante nos modelos completos

Nos modelos com controles, as variáveis que aparecem com maior consistência estatística são:

- `ln_ocupados` ou `d_ln_ocupados`;
- `taxa_desocupacao` ou `d_taxa_desocupacao`;
- dummies sazonais, quando incluídas.

Isso sugere que a informalidade observada na base está mais ligada à dinâmica geral do mercado de trabalho do que ao comportamento isolado do número de beneficiários do Bolsa Família.

### Interpretação substantiva

A principal mensagem da atividade é a seguinte:

- existe uma associação positiva no modelo simples;
- essa associação enfraquece ou desaparece quando a especificação passa a controlar melhor o mercado de trabalho;
- portanto, a evidência não sustenta a ideia de que o Bolsa Família, por si só, explique de forma robusta o aumento do trabalho informal no período analisado.

Em outras palavras, o modelo mais ingênuo sugere relação positiva, mas os modelos mais informativos indicam que esse resultado provavelmente reflete tendência comum, omissão de variáveis relevantes ou composição do mercado de trabalho.

### Limitações da atividade

Apesar de a atividade produzir evidência útil, ela tem limitações importantes:

- a análise é agregada e não usa microdados individuais;
- não há estratégia causal de identificação, como diferenças-em-diferenças, pareamento ou efeitos fixos individuais;
- a série do Bolsa Família precisa ser agregada de mensal para trimestral, o que reduz granularidade;
- informalidade pode responder a fatores não observados que não entram diretamente nas especificações;
- a interpretação depende da medida escolhida para informalidade, taxa ou quantidade absoluta.

Esses pontos significam que o exercício deve ser lido como uma análise econométrica aplicada de associação com controles, e não como demonstração causal definitiva.

### Conclusão final

A conclusão central desta atividade é:

> Não há evidência econométrica robusta de que o aumento do número de beneficiários do Bolsa Família tenha explicado diretamente o aumento do trabalho informal no Brasil no período analisado.

O resultado estatisticamente forte aparece apenas no modelo simples, sem controles. Quando a análise incorpora ocupação, desocupação, tendência temporal e sazonalidade, o efeito do Bolsa Família perde robustez. A leitura mais consistente, portanto, é que a informalidade responde mais intensamente às condições gerais do mercado de trabalho do que à expansão do programa.

### Arquivos relacionados

- Código principal da análise: [`../app/analise.py`](../app/analise.py)
- Entrada CLI: [`../bf_trab_informal.py`](../bf_trab_informal.py)
- Saída consolidada: [`../data/output/series_extraidas.json`](../data/output/series_extraidas.json)
- Gráficos gerados: [`../data/output/`](../data/output/)

### Referências

- IBGE. SIDRA, tabela 4093: indicadores do mercado de trabalho. Disponível em: <https://sidra.ibge.gov.br/tabela/4093>
- Ministério do Desenvolvimento e Assistência Social, Família e Combate à Fome. Vis Data 3: beneficiários do Bolsa Família. Disponível em: <https://aplicacoes.cidadania.gov.br/vis/data3/v.php?q%5B%5D=g9ysl9LerqO4gGVrrGyEymipycqv16Km2ffJsKw%3D>
- statsmodels. `OLS` documentation. Disponível em: <https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.OLS.html>
- statsmodels. Robust covariance results (`HAC`). Disponível em: <https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.RegressionResults.get_robustcov_results.html>

---

## EN

### Overview

This documentation provides a self-contained record of the research question, the dataset, the transformations applied to the time series, the estimated models, the main findings, and the final interpretation of the exercise.

The implementation of the activity is in [`../app/analise.py`](../app/analise.py). The program reads `DadosEconometria.xlsx`, consolidates the series into JSON, generates descriptive charts, and estimates econometric models with `statsmodels`.

### Objective

This activity investigates the relationship between Bolsa Familia and informal labor in Brazil. The central question is:

> Is an increase in the number of Bolsa Familia beneficiaries associated with an increase in labor informality in Brazil?

The exercise does not claim strong causality. Its goal is to test whether there is a statistically robust association between the series, first through descriptive analysis and then through econometric specifications with labor-market controls.

### Motivation

The topic matters because there is a recurring debate about the possible effect of income-transfer programs on labor decisions. A common hypothesis is that a large-scale transfer program could encourage some beneficiaries to remain in informal jobs in order to reduce the risk of losing the benefit.

At the same time, informality in Brazil also responds to structural and cyclical forces such as:

- the employment level;
- unemployment;
- time trend;
- labor-market seasonality;
- the post-pandemic recovery.

For that reason, the activity compares a simple uncontrolled model with richer models that are better able to distinguish spurious association from more informative statistical evidence.

### Data sources

The dataset was organized from two main public sources:

- `SIDRA/IBGE`, table 4093, for quarterly labor-market indicators.
- `Vis Data 3`, from the Ministry of Development and Social Assistance, for Bolsa Familia beneficiary counts.

Direct references:

- SIDRA/IBGE, table 4093: <https://sidra.ibge.gov.br/tabela/4093>
- Vis Data 3: <https://aplicacoes.cidadania.gov.br/vis/data3/v.php?q%5B%5D=g9ysl9LerqO4gGVrrGyEymipycqv16Km2ffJsKw%3D>

### Series used

The activity uses the following series:

- `pessoas_beneficiarias_pbf`: number of Bolsa Familia beneficiaries, originally monthly;
- `taxa_informalidade`: informality rate among employed workers;
- `pessoas_informais_mil`: number of workers in informal employment;
- `pessoas_ocupadas_mil`: total employed workers;
- `pessoas_desocupadas_mil`: total unemployed workers;
- `taxa_desocupacao`: unemployment rate;
- `forca_trabalho_mil`: labor force;
- `fora_forca_trabalho_mil`: people outside the labor force.

### Data preparation

The activity pipeline performs the following steps:

1. Reads specific sheets from `data/input/DadosEconometria.xlsx`.
2. Cleans numeric values and converts dates and quarter labels.
3. Aggregates the monthly Bolsa Familia series into a quarterly average.
4. Builds matched quarterly datasets for correlation analysis.
5. Creates a unified econometric base with the core variables.
6. Keeps only complete quarters for the Bolsa Familia series.
7. Generates log transformations, log differences, and seasonal variables.

This preparation matters because Bolsa Familia is originally monthly, while the labor-market indicators are mostly quarterly.

### Analytical strategy

The exercise is organized into three layers:

#### 1. Descriptive analysis

Charts of the series over time to inspect levels, trends, and co-movement.

#### 2. Correlations

Pearson correlations were computed:

- in levels;
- in quarterly changes.

The correlations were evaluated for two targets:

- the informality rate;
- the number of informal workers.

#### 3. Econometric models

Five OLS models were estimated with HAC Newey-West standard errors using `maxlags=1` in `statsmodels`.

Method references:

- OLS in `statsmodels`: <https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.OLS.html>
- HAC robust covariance in `statsmodels`: <https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.RegressionResults.get_robustcov_results.html>

The estimated models were:

#### Model 1. Simple log-level model

`ln_informal ~ ln_bf`

Purpose:
measure the raw association between Bolsa Familia and the number of informal workers, without controls.

#### Model 2. Main log-difference model with seasonal dummies

`d_ln_informal ~ d_ln_bf + d_ln_bf_lag1 + d_ln_ocupados + d_taxa_desocupacao + pos_2023 + quarterly dummies`

Purpose:
test whether quarterly changes in Bolsa Familia explain quarterly changes in informality after controlling for labor-market dynamics and seasonality.

#### Model 3. Main log-difference model without seasonal dummies

Same structure as the main model, but without quarterly dummies.

Purpose:
test the sensitivity of the association when the seasonal component is removed.

#### Model 4. Log-level model with controls and seasonal dummies

`ln_informal ~ ln_bf + ln_ocupados + taxa_desocupacao + tendencia + pos_2023 + quarterly dummies`

Purpose:
evaluate the level relationship between Bolsa Familia and informality with a more complete control structure.

#### Model 5. Log-level model with controls and no seasonal dummies

Same structure as the previous model, but without quarterly dummies.

Purpose:
check the robustness of the level relationship when seasonality is not explicitly modeled.

### Sample size

Based on the consolidated series exported in `data/output/series_extraidas.json`, the models use:

- `36` observations in level models;
- `32` observations in log-difference models.

The smaller sample in change models comes from:

- the need for consecutive quarters to compute differences;
- the lagged `d_ln_bf` term, which removes additional observations;
- the requirement that Bolsa Familia quarters be complete before entering the econometric base.

### Descriptive results

#### Correlation between Bolsa Familia and the informality rate

- Level correlation: `-0.4907`
- Change correlation: `-0.3195`

Interpretation:
when informality is measured as a rate, the observed association is negative. Descriptively, periods with more program beneficiaries do not coincide with a proportional increase in the informality rate.

#### Correlation between Bolsa Familia and the number of informal workers

- Level correlation: `0.5176`
- Change correlation: `-0.3447`

Interpretation:
when informality is measured in absolute numbers, the level association is positive. Even so, that relationship weakens and changes sign when quarterly changes are analyzed. This suggests that the positive level correlation may reflect a common trend or simultaneous expansion of the labor market rather than a direct program effect.

### Econometric results

#### Model 1. Simple log-level model

Main figures:

- Observations: `36`
- Coefficient on `ln_bf`: `0.3308`
- `p-value` for `ln_bf`: `0.0006`
- `R²`: `0.2664`
- F-test for `ln_bf = 0`: `p = 0.0016`

Reading:
the simple model shows a positive and statistically significant association between Bolsa Familia and the number of informal workers. However, explanatory power is limited and the specification does not control for other labor-market forces.

#### Model 2. Main log-difference model with seasonal dummies

Main figures:

- Observations: `32`
- Coefficient on `d_ln_bf`: `-0.0126`
- `p-value` for `d_ln_bf`: `0.7476`
- Coefficient on `d_ln_bf_lag1`: `0.0880`
- `p-value` for `d_ln_bf_lag1`: `0.1422`
- Joint F-test: `p = 0.3559`
- `R²`: `0.9840`

Reading:
neither the contemporaneous nor the lagged Bolsa Familia change is statistically significant. The model has very high `R²`, but that explanatory power is driven mainly by the controls and seasonality, not by Bolsa Familia.

#### Model 3. Main log-difference model without seasonal dummies

Main figures:

- Observations: `32`
- Coefficient on `d_ln_bf`: `-0.0302`
- `p-value` for `d_ln_bf`: `0.5483`
- Coefficient on `d_ln_bf_lag1`: `0.1836`
- `p-value` for `d_ln_bf_lag1`: `0.0765`
- Joint F-test: `p = 0.1637`
- `R²`: `0.9702`

Reading:
there is only weak evidence for the lagged term at the 10% level, but the joint hypothesis for the Bolsa Familia variables is not rejected. The result is not robust.

#### Model 4. Log-level model with controls and seasonal dummies

Main figures:

- Observations: `36`
- Coefficient on `ln_bf`: `0.0866`
- `p-value` for `ln_bf`: `0.1363`
- F-test for `ln_bf = 0`: `p = 0.1479`
- `R²`: `0.9798`

Reading:
once employment, unemployment, time trend, the post-2023 period, and seasonality are included, Bolsa Familia is no longer statistically significant at conventional levels.

#### Model 5. Log-level model with controls and no seasonal dummies

Main figures:

- Observations: `36`
- Coefficient on `ln_bf`: `0.1299`
- `p-value` for `ln_bf`: `0.0767`
- F-test for `ln_bf = 0`: `p = 0.0869`
- `R²`: `0.9637`

Reading:
without seasonal controls, only weak 10% significance appears. Even so, the result is not robust at the 5% level and should be interpreted cautiously.

### What remains important in the full models

In the controlled specifications, the variables that appear most consistently significant are:

- `ln_ocupados` or `d_ln_ocupados`;
- `taxa_desocupacao` or `d_taxa_desocupacao`;
- seasonal dummies, when included.

This suggests that informality in this dataset is more closely connected to general labor-market dynamics than to the isolated behavior of the number of Bolsa Familia beneficiaries.

### Substantive interpretation

The main message of the activity is:

- there is a positive association in the simple model;
- that association weakens or disappears once labor-market controls are included;
- therefore, the evidence does not support the claim that Bolsa Familia, by itself, robustly explains the increase in informal labor over the analyzed period.

In other words, the more naive model suggests a positive relationship, but the more informative models indicate that this result likely reflects common trends, omitted variables, or labor-market composition effects.

### Limitations

Although the activity produces useful evidence, it has important limitations:

- the analysis is aggregate and does not use individual microdata;
- there is no causal identification strategy such as difference-in-differences, matching, or individual fixed effects;
- the Bolsa Familia series must be aggregated from monthly to quarterly frequency, which reduces granularity;
- informality may respond to unobserved factors not directly included in the models;
- interpretation depends on the chosen measure of informality, rate or absolute number.

These points mean the exercise should be read as an applied econometric association analysis with controls, not as a definitive causal demonstration.

### Final conclusion

The central conclusion of this activity is:

> There is no robust econometric evidence that the increase in the number of Bolsa Familia beneficiaries directly explained the increase in informal labor in Brazil over the analyzed period.

The statistically stronger result appears only in the simple uncontrolled model. Once the analysis incorporates employment, unemployment, time trend, and seasonality, the Bolsa Familia effect loses robustness. The most consistent reading is therefore that informality responds much more strongly to overall labor-market conditions than to the expansion of the program.

### Related files

- Main analysis code: [`../app/analise.py`](../app/analise.py)
- CLI entry point: [`../bf_trab_informal.py`](../bf_trab_informal.py)
- Consolidated output: [`../data/output/series_extraidas.json`](../data/output/series_extraidas.json)
- Generated charts: [`../data/output/`](../data/output/)

### References

- IBGE. SIDRA, table 4093: labor-market indicators. Available at: <https://sidra.ibge.gov.br/tabela/4093>
- Ministry of Development and Social Assistance, Family and Fight Against Hunger. Vis Data 3: Bolsa Familia beneficiaries. Available at: <https://aplicacoes.cidadania.gov.br/vis/data3/v.php?q%5B%5D=g9ysl9LerqO4gGVrrGyEymipycqv16Km2ffJsKw%3D>
- statsmodels. `OLS` documentation. Available at: <https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.OLS.html>
- statsmodels. Robust covariance results (`HAC`). Available at: <https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.RegressionResults.get_robustcov_results.html>
