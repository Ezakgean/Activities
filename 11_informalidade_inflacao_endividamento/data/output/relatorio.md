# Atividade 11 — Inflação, endividamento e informalidade no Brasil

## Objetivo e problema de pesquisa

Investigar se o aumento da inflação e do endividamento das famílias está associado ao aumento da taxa de informalidade no Brasil, entre 2016T1 e 2025T4. A hipótese econômica é que a pressão sobre os orçamentos familiares pode estimular ocupações informais. A direção e a intensidade são questões empíricas; este desenho não identifica causalidade.

## Base, medidas e conferência

Amostra: 40 trimestres civis consecutivos. Sem interpolação, imputação ou coleta adicional. O arquivo original foi preservado em data/input. A consistência interna foi conferida por trimestre, recompondo o IPCA mensal e a média do endividamento. Erros máximos: IPCA 7.11e-15 e endividamento 0.00e+00. Isso não certifica a exatidão das séries frente às fontes oficiais; a origem e a versão da série de informalidade ainda precisam ser auditadas para publicação.

- I: informalidade em % dos ocupados, conforme a planilha; não é quantidade de trabalhadores informais.
- π: IPCA acumulado no trimestre em %, calculado por 100 × [∏(1 + IPCA_m/100) − 1].
- E: endividamento em %, média dos três meses. Segundo os metadados, é dívida com o SFN em relação à renda acumulada em 12 meses (SGS 29037); não é percentual de famílias endividadas nem inadimplência.
- D: 1 de 2020T1 a 2021T4 e 0 nos demais trimestres. São 8 observações com D=1. É uma janela analítica adotada, não uma afirmação de encerramento sanitário ou legal da pandemia.

O IPCA mede a variação dos preços. Sem renda nominal ou real, não se observa diretamente a perda de poder de compra. Para renda nominal fixa, a perda percentual no trimestre seria 100 × [1 − 1/(1 + π/100)], uma transformação da inflação, que não acrescenta informação independente. Não incluir essa transformação junto com o IPCA como se fossem dois canais distintos. Para testar o mecanismo de renda, obter rendimento real e justificar seu papel como variável explicativa ou mediadora.

## Os quatro modelos solicitados

Estimação por mínimos quadrados ordinários com intercepto:

1. M1: I_t = α + βπ π_t + u_t.
2. M2: I_t = α + βE E_t + u_t.
3. M3: I_t = α + βπ π_t + βE E_t + u_t.
4. M4: I_t = α + βπ π_t + βE E_t + δ D_t + u_t.

Espera-se βπ > 0 e βE > 0 segundo a hipótese proposta. Os modelos simples estimam associações brutas; M3 e M4 estimam associações parciais. Em M4, δ é um deslocamento médio do intercepto na janela definida, mantendo IPCA e endividamento constantes. A dummy não estima mudança de inclinação nem isola o efeito causal da pandemia.

Todas as variáveis originais estão em escala percentual (38,3 significa 38,3%, não 0,383). Cada β expressa a diferença em pontos percentuais da informalidade associada a +1 ponto percentual na explicativa. Esse coeficiente não é elasticidade. Os erros u_t capturam fatores omitidos.

## Inferência e hipóteses

Erros-padrão HAC de Newey–West, kernel Bartlett, 4 defasagens, correção de amostra finita e referência t com graus de liberdade residuais. A janela principal de quatro defasagens cobre até um ano; sensibilidade com uma defasagem está em sensibilidade_hac.csv. HAC modifica a inferência, não os coeficientes, e não corrige regressão espúria, endogeneidade ou a equação da média.

A tabela principal usa H0: β=0 contra H1: β≠0, IC95% e significância de 5%. O arquivo de coeficientes também apresenta o teste direcional pré-especificado H0: β≤0 contra H1: β>0; para coeficiente negativo, o p unilateral positivo é grande. Não escolher a cauda após observar os resultados. O teste F robusto de M3/M4 avalia H0: βπ=βE=0; rejeitá-lo não implica que ambos sejam positivos ou individualmente significativos. A dummy fica fora dessa restrição conjunta. A amostra pequena exige cautela mesmo com HAC.

## Resultados dos quatro modelos em nível

| modelo | termo | coeficiente | ep_hac | p_bilateral | ic95_inferior | ic95_superior |
| --- | --- | --- | --- | --- | --- | --- |
| M1 | ipca | 0.1822 | 0.1871 | 0.3362 | -0.1965 | 0.5609 |
| M2 | endividamento | -0.0635 | 0.0550 | 0.2556 | -0.1748 | 0.0479 |
| M3 | ipca | 0.2424 | 0.1952 | 0.2221 | -0.1531 | 0.6378 |
| M3 | endividamento | -0.0714 | 0.0535 | 0.1897 | -0.1798 | 0.0369 |
| M4 | ipca | 0.2866 | 0.2289 | 0.2185 | -0.1776 | 0.7507 |
| M4 | endividamento | -0.0749 | 0.0556 | 0.1863 | -0.1878 | 0.0379 |
| M4 | pandemia | -0.3608 | 0.7125 | 0.6157 | -1.8057 | 1.0842 |

| modelo | n | r2 | r2_ajustado | p_f_hac_explicativas |
| --- | --- | --- | --- | --- |
| M1 | 40 | 0.0266 | 0.0010 | 0.3362 |
| M2 | 40 | 0.0832 | 0.0591 | 0.2556 |
| M3 | 40 | 0.1291 | 0.0820 | 0.2029 |
| M4 | 40 | 0.1461 | 0.0749 | 0.2453 |

M1, ipca: coeficiente 0.1822; p bilateral 0.3362; IC95% [-0.1965; 0.5609]. Há evidência insuficiente de associação diferente de zero a 5% no teste bilateral.
M2, endividamento: coeficiente -0.0635; p bilateral 0.2556; IC95% [-0.1748; 0.0479]. Há evidência insuficiente de associação diferente de zero a 5% no teste bilateral.
M3, ipca: coeficiente 0.2424; p bilateral 0.2221; IC95% [-0.1531; 0.6378]. Há evidência insuficiente de associação diferente de zero a 5% no teste bilateral.
M3, endividamento: coeficiente -0.0714; p bilateral 0.1897; IC95% [-0.1798; 0.0369]. Há evidência insuficiente de associação diferente de zero a 5% no teste bilateral.
M4, ipca: coeficiente 0.2866; p bilateral 0.2185; IC95% [-0.1776; 0.7507]. Há evidência insuficiente de associação diferente de zero a 5% no teste bilateral.
M4, endividamento: coeficiente -0.0749; p bilateral 0.1863; IC95% [-0.1878; 0.0379]. Há evidência insuficiente de associação diferente de zero a 5% no teste bilateral.
M4, pandemia: coeficiente -0.3608; p bilateral 0.6157; IC95% [-1.8057; 1.0842]. Há evidência insuficiente de associação diferente de zero a 5% no teste bilateral.

A interpretação adequada é condicional aos modelos e à qualidade das séries. Ausência de significância não demonstra ausência de associação. Um sinal negativo não significativo tampouco permite afirmar que a dívida reduz a informalidade.

## Gráficos individuais dos quatro modelos

Cada modelo tem um arquivo PNG e um PDF. Os painéis exibem relações estimadas e o ajuste da informalidade ao longo do tempo. M3 e M4 apresentam também contrastes para aumentos individuais e simultâneos de 1 p.p. no IPCA e no endividamento, com intervalos calculados usando a covariância HAC completa. Nos painéis condicionais, a outra explicativa econômica fica na média e os pontos observados são ajustados para esse mesmo valor. Em M4, as curvas distinguem D=0 e D=1; o contraste da dummy compara os grupos com IPCA e endividamento fixos. São associações estimadas, não efeitos causais. As faixas representam a incerteza da média estimada, não a dispersão dos dados individuais.

- [Modelo 1 — IPCA](modelo_1_ipca.png).
- [Modelo 2 — Endividamento](modelo_2_endividamento.png).
- [Modelo 3 — IPCA e endividamento](modelo_3_ipca_endividamento.png).
- [Modelo 4 — IPCA, endividamento e pandemia](modelo_4_pandemia.png).

## Séries temporais e verificações de robustez

Os quatro modelos em nível são referências descritivas. A pergunta sobre aumentos requer examinar também mudanças no tempo:

- D1–D4 usam ΔI como dependente e Δπ e/ou ΔE como explicativas. Em D4, a dummy é ΔD, pois se diferencia a equação M4: representa entrada e saída da janela. Δπ é aceleração/desaceleração da inflação trimestral, não o IPCA trimestral em si; ΔE é a mudança do indicador de dívida, não o crescimento percentual do estoque de dívida.
- R1: ΔI_t = α + ρΔI_(t−1) + θπ π_(t−1) + θE ΔE_(t−1) + δD_t + sazonalidade + u_t. Examina se inflação anterior e aumento anterior do indicador de dívida se associam à mudança atual da informalidade. A dummy em nível neste modelo permite uma mudança média na variação da informalidade durante a janela. É uma especificação diferente de D4. As duas primeiras observações são perdidas (N=38). Defasagens não eliminam endogeneidade.
- R2 acrescenta tendência linear e dummies sazonais a M4 (T1 como referência).
- R3 usa janela 2020T2–2021T4; R4 usa 2020T1–2023T2. As janelas são sensibilidades analíticas, não datas oficiais de uma mesma definição de pandemia.

| modelo | termo | coeficiente | p_bilateral | ic95_inferior | ic95_superior |
| --- | --- | --- | --- | --- | --- |
| D4 | d_ipca | 0.1026 | 0.4133 | -0.1490 | 0.3541 |
| D4 | d_endividamento | 0.2366 | 0.1056 | -0.0526 | 0.5258 |
| R1 | ipca_lag1 | 0.1527 | 0.3832 | -0.1997 | 0.5052 |
| R1 | d_endividamento_lag1 | -0.2487 | 0.0727 | -0.5217 | 0.0243 |
| R2 | ipca | 0.2420 | 0.1284 | -0.0738 | 0.5578 |
| R2 | endividamento | 0.0333 | 0.8036 | -0.2374 | 0.3041 |
| R3 | ipca | 0.3088 | 0.2275 | -0.2013 | 0.8189 |
| R3 | endividamento | -0.0753 | 0.1846 | -0.1881 | 0.0376 |
| R4 | ipca | 0.2314 | 0.3082 | -0.2226 | 0.6855 |
| R4 | endividamento | -0.0740 | 0.2098 | -0.1915 | 0.0435 |

D4, d_ipca: coeficiente 0.1026; p bilateral 0.4133; IC95% [-0.1490; 0.3541]. Há evidência insuficiente de associação diferente de zero a 5% no teste bilateral. D4, d_endividamento: coeficiente 0.2366; p bilateral 0.1056; IC95% [-0.0526; 0.5258]. Há evidência insuficiente de associação diferente de zero a 5% no teste bilateral.

R1, ipca_lag1: coeficiente 0.1527; p bilateral 0.3832; IC95% [-0.1997; 0.5052]. Há evidência insuficiente de associação diferente de zero a 5% no teste bilateral. R1, d_endividamento_lag1: coeficiente -0.2487; p bilateral 0.0727; IC95% [-0.5217; 0.0243]. Há evidência insuficiente de associação diferente de zero a 5% no teste bilateral.

Não selecionar a especificação pelo menor p-valor. As especificações respondem a perguntas distintas. O R² de modelos com dependentes diferentes não deve ser comparado; AIC/BIC só devem orientar comparações com a mesma dependente e a mesma amostra.

## Diagnósticos

ADF: H0 de raiz unitária; KPSS: H0 de estacionariedade em torno de constante (c) ou tendência (ct). ADF seleciona até quatro defasagens por AIC; KPSS usa quatro. Os p-valores KPSS são tabelados e os avisos de limites estão preservados em estacionariedade.csv. Com 40 observações, quebras e pandemia reduzem o poder desses testes. Não rejeitar ADF não prova raiz unitária; resultados conflitantes não justificam conclusões automáticas. Os testes c e ct são sensibilidades à parte determinística.

| variavel | adf_p | adf_lags | kpss_p_tabelado |
| --- | --- | --- | --- |
| informalidade | 0.2048 | 1 | 0.1000 |
| ipca | 0.1269 | 2 | 0.1000 |
| endividamento | 0.8726 | 4 | 0.0100 |
| d_informalidade | 0.0000 | 0 | 0.1000 |
| d_ipca | 0.0000 | 1 | 0.1000 |
| d_endividamento | 0.0157 | 3 | 0.1000 |

Na configuração com constante, o ADF não rejeita raiz unitária nas três séries em nível a 5%. O KPSS rejeita estacionariedade do endividamento; para as outras duas séries, os testes não são conclusivos em conjunto. Nas primeiras diferenças, o ADF com constante rejeita raiz unitária nas três séries e o KPSS não rejeita estacionariedade. A sensibilidade com tendência, especialmente para a mudança do endividamento, recomenda cautela. Esses resultados favorecem examinar variações, sem certificar automaticamente uma especificação.

Breusch–Godfrey (quatro defasagens) testa H0 de ausência de autocorrelação residual; Breusch–Pagan testa H0 de homocedasticidade. Seus p-valores usuais são diagnósticos aproximados nesta amostra; BP é particularmente sensível à dependência temporal. VIF avalia colinearidade entre os regressores; o intercepto não é reportado.

| modelo | bg_lm_p_4 | bp_lm_p |
| --- | --- | --- |
| M1 | 0.0001 | 0.0639 |
| M2 | 0.0001 | 0.6244 |
| M3 | 0.0002 | 0.3212 |
| M4 | 0.0003 | 0.1460 |

Nos quatro modelos em nível, Breusch–Godfrey rejeita ausência de autocorrelação a 5%; há dependência temporal residual relevante. Os VIFs das explicativas de M4 são próximos de 1, de modo que colinearidade não parece ser o principal problema nesta especificação. O uso de HAC deve ser acompanhado da discussão sobre a dinâmica e a estacionariedade, e não apenas da tabela de significância.

Se há persistência/tendência não resolvida, os resultados em nível não devem fundamentar a conclusão principal. Em etapas posteriores, considerar ARDL/ECM e cointegração apenas após justificar a ordem de integração e excluir séries I(2); erros HAC por si só não tornam uma regressão em nível válida. As variações e defasagens aqui são verificações exploratórias, não prova de que todos os problemas foram resolvidos.

## Conclusão para o trabalho

Nos quatro modelos em nível desta base, a inflação apresenta coeficiente positivo e o endividamento coeficiente negativo, mas nenhum desses coeficientes é significativo a 5% no teste bilateral com a configuração HAC principal. Portanto, essas regressões não fornecem evidência estatística suficiente para sustentar a hipótese de que ambos estejam associados positivamente à informalidade no período. A inclusão da dummy não altera essa leitura. Os resultados em variações e com defasagens devem ser discutidos como sensibilidade, respeitando a mudança do significado dos coeficientes.

Este estudo não demonstra causalidade. Atividade econômica, desemprego, rendimento, composição setorial, transferências, juros e mudanças de medição podem afetar as séries simultaneamente. A taxa de informalidade também pode cair pela saída de informais da ocupação; ela não mede isoladamente criação de postos formais. Com apenas 40 observações, priorizar modelos parcimoniosos e evitar muitos controles e defasagens. A conclusão sobre perda efetiva de poder de compra depende de ampliar a base.

## Reprodutibilidade e referências

Base fornecida pelo usuário; metadados e SHA-256 em auditoria.json. A aba de metodologia informa SIDRA 8529 (informalidade), SIDRA 1737 (IPCA) e SGS 29037 (endividamento). Não foram substituídos dados da planilha por dados externos. As páginas SIDRA e BCB não puderam ser lidas na consulta desta execução; a atribuição das séries acima deriva dos metadados, não de uma auditoria externa concluída.

- [Informalidade — SIDRA 8529](https://sidra.ibge.gov.br/tabela/8529).
- [IPCA — SIDRA 1737](https://sidra.ibge.gov.br/tabela/1737).
- [BCB — SGS 29037](https://dadosabertos.bcb.gov.br/dataset/29037-endividamento-das-familias-com-o-sistema-financeiro-nacional-em-relacao-a-renda-acumulada-dos).
- [statsmodels — covariâncias robustas e HAC](https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.RegressionResults.get_robustcov_results.html).
- [statsmodels — teste ADF](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.adfuller.html).
