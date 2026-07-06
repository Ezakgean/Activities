# Activity 09 Documentation

**Idioma / Language:** [Português](#pt-br) | [English](#en)

---

## PT-BR

### Objetivo

Esta atividade documenta a análise da relação entre o Programa Bolsa Família e o trabalho informal no Brasil com dados trimestrais. O foco do exercício é verificar se a evolução do número de beneficiários do programa está associada ao comportamento da informalidade, tanto pela taxa de informalidade quanto pela quantidade absoluta de pessoas ocupadas em situação informal.

A implementação em [`app/analise.py`](/home/ezequieldev/Documentos/Activities/09_bf_trab_informal/app/analise.py) consolida as séries da planilha `DadosEconometria.xlsx`, agrega o Bolsa Família para frequência trimestral, calcula correlações e estima modelos econométricos por MQO com erros-padrão HAC.

### Base e método

- Período analisado: 2016 a 2025 para a base econométrica trimestral.
- Fontes principais: PNAD Contínua/SIDRA para mercado de trabalho e Vis Data 3 para beneficiários do Bolsa Família.
- Variáveis centrais: beneficiários do Bolsa Família, taxa de informalidade, pessoas informais, pessoas ocupadas e taxa de desocupação.
- Estratégia empírica: correlações em nível e em variação, além de cinco modelos OLS em log-nível e log-diferenças.

Os modelos foram organizados para separar associação simples de associação com controles. Isso permite comparar um modelo bivariado com especificações que incorporam ocupação, desocupação, tendência temporal, período pós-2023 e sazonalidade trimestral.

### Principais resultados

#### 1. Correlações descritivas

- Bolsa Família x taxa de informalidade: correlação em nível de `-0,491` e em variação de `-0,319`.
- Bolsa Família x pessoas informais: correlação em nível de `0,518` e em variação de `-0,345`.

Esses resultados mostram que a leitura muda conforme a medida de informalidade. Em taxa, a associação observada é negativa. Em quantidade absoluta, a associação em nível é positiva, mas deixa de apontar para aumento conjunto quando se observam variações trimestrais.

#### 2. Modelo simples

No modelo bivariado em nível logarítmico, o coeficiente de `ln_bf` foi `0,3308`, com `p = 0,0006` e `R² = 0,2664`. Esse resultado sugere associação positiva entre Bolsa Família e quantidade de trabalhadores informais quando não há controles adicionais.

#### 3. Modelos com controles

Nos modelos com controles de mercado de trabalho, o Bolsa Família perde robustez estatística:

- Modelo principal em variações com dummies sazonais: `d_ln_bf` e `d_ln_bf_lag1` não foram significativos, com teste F conjunto `p = 0,3559` e `R² = 0,9840`.
- Modelo principal em variações sem dummies: evidência fraca apenas para a defasagem, mas teste F conjunto não significativo (`p = 0,1637`; `R² = 0,9702`).
- Modelo em nível com controles e dummies sazonais: `ln_bf` com `p = 0,1363`, sem significância estatística usual, e `R² = 0,9798`.
- Modelo em nível com controles e sem dummies: `ln_bf` com `p = 0,0767`, significância apenas fraca a 10%, e `R² = 0,9637`.

Em contraste, as variáveis ligadas ao mercado de trabalho, especialmente `ln_ocupados` e `taxa_desocupacao`, aparecem de forma mais consistente como determinantes da informalidade nas especificações completas.

### Conclusão da atividade

A atividade reproduz a conclusão central do relatório: não há evidência econométrica robusta de que o crescimento do número de beneficiários do Bolsa Família explique diretamente o crescimento do trabalho informal no Brasil no período analisado.

O resultado positivo do modelo simples parece refletir associação agregada sem controle suficiente. Quando a análise incorpora dinâmica do mercado de trabalho, tendência e sazonalidade, o efeito do Bolsa Família deixa de ser estatisticamente robusto. Assim, os resultados apontam que a informalidade está mais relacionada às condições gerais do mercado de trabalho do que à expansão do programa.

---

## EN

### Objective

This activity documents the analysis of the relationship between Bolsa Familia and informal labor in Brazil using quarterly data. The goal is to assess whether changes in the number of program beneficiaries are associated with informality, both through the informality rate and through the absolute number of workers in informal jobs.

The implementation in [`app/analise.py`](/home/ezequieldev/Documentos/Activities/09_bf_trab_informal/app/analise.py) consolidates the series from `DadosEconometria.xlsx`, aggregates Bolsa Familia to quarterly frequency, computes correlations, and estimates econometric models using OLS with HAC standard errors.

### Data and method

- Analysis period: 2016 to 2025 for the quarterly econometric base.
- Main sources: PNAD Contínua/SIDRA for labor-market data and Vis Data 3 for Bolsa Familia beneficiaries.
- Core variables: Bolsa Familia beneficiaries, informality rate, informal workers, employed workers, and unemployment rate.
- Empirical strategy: level and change correlations, plus five OLS models in log-level and log-difference form.

The models were designed to separate simple association from association with controls. This makes it possible to compare a bivariate model with specifications that include employment, unemployment, time trend, post-2023 period, and quarterly seasonality.

### Main results

#### 1. Descriptive correlations

- Bolsa Familia x informality rate: level correlation of `-0.491` and change correlation of `-0.319`.
- Bolsa Familia x informal workers: level correlation of `0.518` and change correlation of `-0.345`.

These results show that the interpretation changes depending on how informality is measured. In rate terms, the observed association is negative. In absolute terms, the level association is positive, but quarterly changes do not indicate a joint increase.

#### 2. Simple model

In the bivariate log-level model, the coefficient on `ln_bf` was `0.3308`, with `p = 0.0006` and `R² = 0.2664`. This suggests a positive association between Bolsa Familia and the number of informal workers when no additional controls are included.

#### 3. Models with controls

In the models with labor-market controls, Bolsa Familia loses statistical robustness:

- Main change model with seasonal dummies: `d_ln_bf` and `d_ln_bf_lag1` were not significant, with joint F-test `p = 0.3559` and `R² = 0.9840`.
- Main change model without dummies: weak evidence only for the lagged term, but the joint F-test was not significant (`p = 0.1637`; `R² = 0.9702`).
- Level model with controls and seasonal dummies: `ln_bf` had `p = 0.1363`, not statistically significant at usual levels, and `R² = 0.9798`.
- Level model with controls and no dummies: `ln_bf` had `p = 0.0767`, showing only weak 10% significance, and `R² = 0.9637`.

By contrast, labor-market variables, especially `ln_ocupados` and `taxa_desocupacao`, appear much more consistently as drivers of informality in the full specifications.

### Activity conclusion

This activity reproduces the report's main conclusion: there is no robust econometric evidence that growth in the number of Bolsa Familia beneficiaries directly explains the growth of informal labor in Brazil over the analyzed period.

The positive result from the simple model appears to reflect aggregate association without sufficient controls. Once the analysis incorporates labor-market dynamics, trend, and seasonality, the Bolsa Familia effect is no longer statistically robust. The results therefore indicate that informality is more closely related to general labor-market conditions than to the expansion of the program.
