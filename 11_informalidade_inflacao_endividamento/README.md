# Atividade 11 — Informalidade, inflação e endividamento

Análise trimestral do Brasil (2016T1–2025T4), a partir da planilha fornecida, para investigar se inflação e endividamento familiar estão associados ao aumento da taxa de informalidade. O IPCA representa pressão de preços; sem rendimento real não é possível testar diretamente perda de poder de compra.

## Executar

Usando as dependências compartilhadas já instaladas, a partir da raiz do repositório:

```bash
.venv/bin/python 11_informalidade_inflacao_endividamento/informalidade.py
```

Ou com ambiente próprio:

```bash
cd 11_informalidade_inflacao_endividamento
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m app
```

Parâmetros opcionais (a nova planilha deve preservar as abas e os 40 trimestres da base):

```bash
python informalidade.py --arquivo data/input/base_regressao_informalidade_ipca_endividamento_2016_2025.xlsx --saida data/output --hac-lags 4
```

Não há interface gráfica. A execução padrão não acessa a rede; a auditoria reutiliza respostas oficiais salvas em `data/input/fontes_oficiais`. Para atualizar esses snapshots explicitamente, execute `python -m app.fontes` ou use `python informalidade.py --atualizar-fontes`. As consultas registram URL, data/hora e SHA-256 e não modificam o Excel original. O código valida identificadores, duplicatas, ausências e agregações mensais; recusa bases incompletas em vez de imputar observações. A planilha original está copiada em `data/input/` e permanece intacta.

## Modelos

Todas as séries originais estão em porcentagem; os coeficientes são interpretados em pontos percentuais.

| Modelo | Dependente | Explicativas |
| --- | --- | --- |
| M1 | Informalidade | IPCA trimestral |
| M2 | Informalidade | Endividamento |
| M3 | Informalidade | IPCA + endividamento |
| M4 | Informalidade | IPCA + endividamento + dummy pandemia |

Todos incluem intercepto. Dummy principal: 2020T1–2021T4. A janela é uma escolha analítica, com sensibilidades 2020T2–2021T4 e 2020T1–2023T2. Estimação OLS e inferência HAC/Bartlett com quatro defasagens, correção de amostra finita e distribuição t; sensibilidades HAC(1), HAC(2) e HAC(4) incluídas. Significância principal bilateral de 5%; p unilateral para a hipótese positiva também exportado. Os testes F robustos incluem testes individuais de todos os coeficientes (inclusive intercepto), o teste global de todos os regressores exceto intercepto, o bloco das explicativas econômicas e o bloco sazonal quando presente. Para uma restrição, F = t² e seu p-valor equivale ao teste t bilateral.

D1–D4 diferenciam as equações originais, inclusive a dummy de M4. A mudança do IPCA mede aceleração da inflação. R1 usa mudança da informalidade, sua defasagem, inflação defasada, mudança do endividamento defasada, dummy em nível e sazonalidade. R2 acrescenta tendência e sazonalidade ao M4. R3/R4 alteram a janela da dummy. Esses modelos são sensibilidades e não identificam causalidade.

## Resultados e arquivos

Abra [data/output/relatorio.html](data/output/relatorio.html) no navegador. O HTML inclui os nove gráficos incorporados nas seções de análise e funciona sem internet. A apresentação traz navegação por seção, resumo inicial, barras comparativas de VIF e tabelas completas por modelo em painéis expansíveis. O botão de impressão abre todas as tabelas para salvar um PDF completo. A versão Markdown também incorpora os gráficos por referência aos PNGs locais. A versão em Markdown está em [data/output/relatorio.md](data/output/relatorio.md).

- `resultados.xlsx`: base tratada, coeficientes, IC95%, testes direcionais e bilaterais, ajuste, testes conjuntos, diagnósticos, estacionariedade, sensibilidade HAC, descritivas e correlações.
- `testes_t.csv` e `testes_f.csv` (também como abas de `resultados.xlsx`): testes dos 12 modelos, com estatísticas, hipóteses nulas, graus de liberdade, valores críticos e decisões a 5%. O relatório apresenta os resultados de todos os coeficientes e modelos. P-valores por teste, sem ajuste por comparações múltiplas.
- `multicolinearidade.csv`: VIF, tolerância, R² auxiliar e classificação de cada explicativa dos 12 modelos.
- `colinearidade_modelos.csv`: número de condição das explicativas centradas/padronizadas, posto da matriz e verificação de dependência linear exata por modelo. Ambos também constam na planilha e no relatório; os limites são referências diagnósticas, sem p-valores.
- CSVs com as mesmas tabelas, em UTF-8 com BOM.
- `series.png`, `coeficientes.png`, `ajuste_m4.png`: gráficos exportáveis.
- `modelo_1_ipca.png/.pdf`: dispersão com reta e IC95% HAC, e observado versus ajustado no tempo.
- `modelo_2_endividamento.png/.pdf`: dispersão com reta e IC95% HAC, e observado versus ajustado no tempo.
- `modelo_3_ipca_endividamento.png/.pdf`: relações condicionais, contrastes individuais e simultâneo (+1 p.p. em cada explicativa), e ajuste no tempo.
- `modelo_4_pandemia.png/.pdf`: relações condicionais por dummy, contrastes incluindo D=1 versus D=0, e ajuste no tempo com a janela da pandemia destacada.
- `sumarios_modelos.txt`: sumários completos dos 12 modelos.
- `auditoria.json`: hash do Excel de entrada, versões dos pacotes, parâmetros e metadados da planilha.

As fontes informadas no Excel são SIDRA 8529, SIDRA 1737 e SGS 29037. A revisão compara os 40 trimestres de cada série e os 120 meses de IPCA e de endividamento com snapshots das APIs oficiais. Na extração registrada em 2026-11-03, todos coincidem (tolerância absoluta de 1e-8 p.p.). Isso não reconstitui versões históricas nem certifica a adequação temporal dos modelos. A documentação metodológica, limitações e interpretação dos diagnósticos estão no relatório gerado. Os arquivos em `data/output/` são substituídos ao executar novamente com a mesma pasta de saída.

## Verificação

A partir desta pasta, com as dependências instaladas:

```bash
python -m unittest discover -s tests -v
```

Os testes verificam a agregação da base real, dados mensais corrompidos, fronteiras da dummy, tratamento de lacunas e defasagens, coeficientes OLS e a direção correta do teste unilateral positivo.

## Revisão do parecer técnico

M1–M4 e a dummy 2020T1–2021T4 foram preservados. Os níveis são referências descritivas; a validação da especificação e a identificação causal continuam limitadas. Nenhuma série de controle ausente foi imputada e nenhum modelo foi selecionado por significância.

- `fontes_resumo.csv`, `fontes_trimestres.csv`, `fontes_meses.csv`: comparação com a versão oficial; snapshots, metadados e manifesto em `data/input/fontes_oficiais/`.
- `reproducao_modelos.csv`, `reproducao_coeficientes.csv`, `reproducao_covariancias.csv`: reconstrução separada das amostras, MQO, HAC/Bartlett, t, F e IC95%; BG, BP e VIF também conferidos por regressões auxiliares. É uma reprodução computacional, não uma auditoria por equipe externa.
- `agregacao_coeficientes.csv`, `agregacao_modelos.csv`: média do endividamento versus último mês do trimestre nos 12 modelos; as diferenças e defasagens são recalculadas. A variante completa está nas abas/CSVs com sufixo `_fim`, incluindo testes t/F e diagnósticos.
- `estacionariedade_sens.csv`: 54 combinações de série, ordem de diferença, parte determinística e limite de defasagens para ADF/KPSS. `quebras_za.csv`: seis testes Zivot–Andrews em nível, com uma quebra candidata. Essas sensibilidades não certificam ordem de integração ou cointegração.
- `sensibilidade_f_hac.csv`: F global/econômico com uma, duas e quatro defasagens. `sensibilidade_hac.csv` agora inclui todos os coeficientes dos 12 modelos.
- `autocorrelacao_modelos.png/.pdf` e `sensibilidade_agregacao.png/.pdf`: novos gráficos, mantendo os sete anteriores.

Os testes adicionais verificam a auditoria offline, adulteração de snapshots, divergências de valores, reprodução dos 12 modelos, detecção de matrizes incorretas, agregação alternativa e especificações temporais.

## Fundamentação e alcance da apresentação

M4 é a referência descritiva principal da apresentação por reunir inflação, endividamento e a janela analítica 2020T1–2021T4 na mesma equação, com parcimônia. Essa definição organiza a pergunta econômica e não certifica a regressão em nível como modelo temporal válido. M1–M3 dão contexto; diferenças, defasagens, tendência e janelas alternativas permanecem complementos exploratórios.

O relatório distingue coeficientes e IC95%, F econômico, F global e diagnósticos. A rejeição global de R1 não é apresentada como confirmação da hipótese sobre os dois regressores econômicos. Não rejeitar um coeficiente não equivale a demonstrar ausência de relação ou equivalência prática a zero. As conclusões são condicionais à especificação e reconhecem a sensibilidade à agregação, sem selecionar resultados por significância.

A revisão de fundamentação e redação reutilizou as tabelas salvas; não reestimou modelos nem alterou coeficientes, testes, dummy, planilha ou gráficos.
