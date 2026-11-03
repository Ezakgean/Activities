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

Não há interface gráfica nem coleta online. O código valida identificadores, duplicatas, ausências e agregações mensais; recusa bases incompletas em vez de imputar observações. A planilha original está copiada em `data/input/` e permanece intacta.

## Modelos

Todas as séries originais estão em porcentagem; os coeficientes são interpretados em pontos percentuais.

| Modelo | Dependente | Explicativas |
| --- | --- | --- |
| M1 | Informalidade | IPCA trimestral |
| M2 | Informalidade | Endividamento |
| M3 | Informalidade | IPCA + endividamento |
| M4 | Informalidade | IPCA + endividamento + dummy pandemia |

Todos incluem intercepto. Dummy principal: 2020T1–2021T4. A janela é uma escolha analítica, com sensibilidades 2020T2–2021T4 e 2020T1–2023T2. Estimação OLS e inferência HAC/Bartlett com quatro defasagens, correção de amostra finita e distribuição t; sensibilidade HAC(1) incluída. Significância principal bilateral de 5%; p unilateral para a hipótese positiva também exportado. F robusto testa as explicativas econômicas conjuntamente, sem a dummy.

D1–D4 diferenciam as equações originais, inclusive a dummy de M4. A mudança do IPCA mede aceleração da inflação. R1 usa mudança da informalidade, sua defasagem, inflação defasada, mudança do endividamento defasada, dummy em nível e sazonalidade. R2 acrescenta tendência e sazonalidade ao M4. R3/R4 alteram a janela da dummy. Esses modelos são sensibilidades e não identificam causalidade.

## Resultados e arquivos

Abra [data/output/relatorio.html](data/output/relatorio.html) no navegador. O HTML inclui os gráficos e funciona sem internet. Pode ser impresso como PDF pelo navegador. A versão em Markdown está em [data/output/relatorio.md](data/output/relatorio.md).

- `resultados.xlsx`: base tratada, coeficientes, IC95%, testes direcionais e bilaterais, ajuste, testes conjuntos, diagnósticos, estacionariedade, sensibilidade HAC, descritivas e correlações.
- CSVs com as mesmas tabelas, em UTF-8 com BOM.
- `series.png`, `coeficientes.png`, `ajuste_m4.png`: gráficos exportáveis.
- `modelo_1_ipca.png/.pdf`: dispersão com reta e IC95% HAC, e observado versus ajustado no tempo.
- `modelo_2_endividamento.png/.pdf`: dispersão com reta e IC95% HAC, e observado versus ajustado no tempo.
- `modelo_3_ipca_endividamento.png/.pdf`: relações condicionais, contrastes individuais e simultâneo (+1 p.p. em cada explicativa), e ajuste no tempo.
- `modelo_4_pandemia.png/.pdf`: relações condicionais por dummy, contrastes incluindo D=1 versus D=0, e ajuste no tempo com a janela da pandemia destacada.
- `sumarios_modelos.txt`: sumários completos dos 12 modelos.
- `auditoria.json`: hash do Excel de entrada, versões dos pacotes, parâmetros e metadados da planilha.

As fontes informadas no Excel são SIDRA 8529, SIDRA 1737 e SGS 29037. A execução confere a consistência interna, mas não substitui a auditoria das séries contra as fontes oficiais. A documentação metodológica, limitações e interpretação dos diagnósticos estão no relatório gerado. Os arquivos em `data/output/` são substituídos ao executar novamente com a mesma pasta de saída.

## Verificação

A partir desta pasta, com as dependências instaladas:

```bash
python -m unittest discover -s tests -v
```

Os testes verificam a agregação da base real, dados mensais corrompidos, fronteiras da dummy, tratamento de lacunas e defasagens, coeficientes OLS e a direção correta do teste unilateral positivo.
