# 10_divida_gastos_publicos

**Idioma / Language:** [Português](#pt-br) | [English](#en)

---

## PT-BR

Aplicação em Python para analisar a dívida pública e os gastos da União. Consolida arquivos do **Relatório Mensal da Dívida (RMD)** em uma série histórica comparável, preservando os valores nominais e calculando a série real quando houver um arquivo de IPCA.

### Objetivo
- ler múltiplos JSONs mensais do RMD em `data/input`
- extrair estoque, composição, prazo, vencimento em 12 meses e fluxos
- manter a série nominal exatamente como publicada
- calcular série real com IPCA em uma base comum
- calcular `Dívida / PIB` quando houver série de PIB compatível
- exportar CSV, JSON consolidado, resumo textual e dashboard PNG

### Estrutura da activity
- `app/analise.py`: pipeline principal de consolidação
- `app/gui.py`: interface gráfica para executar a rotina
- `data/input/`: JSONs do RMD e arquivos opcionais de IPCA/PIB
- `data/output/`: artefatos gerados
- `divida_publica.py`: ponto de entrada em linha de comando

### Entradas esperadas
O app já lê automaticamente qualquer `*.json` em `data/input`.

Arquivos opcionais:
- `data/input/ipca.csv`
  - colunas mínimas: `periodo`, `ipca_indice`
  - exemplo: `2000-11,100.23`
- `data/input/pib.csv`
  - colunas mínimas: `periodo`, `pib_nominal_brl_bilhoes`
  - exemplo: `2000-11,2100.50`

### Saídas
- `data/output/serie_divida_publica_consolidada.json`
- `data/output/serie_divida_publica_consolidada.csv`
- `data/output/resumo_divida_publica.txt`
- `data/output/dashboard_divida_publica.png`

### Requisitos
- Python 3.10+
- dependências da raiz do repositório ou do `requirements.txt` local

### Instalação
```bash
cd 10_divida_gastos_publicos
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Interface gráfica
```bash
cd 10_divida_gastos_publicos
python divida_publica.py
```

O painel permite alternar o gráfico entre estoque nominal/real, composição por indexador e fluxos de emissões e resgates.

### Painel de gráficos
O painel dedicado usa gráficos de linha e separa trechos com lacunas para não desenhar conexões artificiais entre competências.

```bash
python -m app.painel_graficos
```

### Atualizar os dados

A consolidação lê os arquivos locais; para buscar novas publicações, execute os coletores abaixo. Os comandos partem da pasta `10_divida_gastos_publicos`, com o ambiente virtual ativo.

**Gastos da União:** na interface, abra **Gastos públicos por categoria** e clique em **Coletar último ano** ou **Coletar todo o histórico**. A coleta consulta o catálogo e reaproveita arquivos cujo cache continua válido. Pelo terminal, para forçar um novo download do último ano disponível:

```bash
python -m app.gastos_publicos --atualizar
```

Para conferir revisões de todos os anos, forçando novo download:

```bash
python -m app.gastos_publicos --todos-anos --atualizar
```

Essa operação pode levar vários minutos. Se o painel já estiver aberto, clique em **Recarregar arquivos** depois da coleta pelo terminal. As séries de gastos são reconstruídas automaticamente.

**Dívida pública (RMD):** escolha as competências em `AAAA-MM`. Exemplo de atualização de julho a setembro de 2026, incluindo revisão do mês já existente:

```bash
python -m app.coletor_lote_rmd --inicio 2026-07 --fim 2026-09 --sobrescrever
python divida_publica.py --cli
```

Ajuste o intervalo ao período desejado. Relatórios ainda não publicados ou não reconhecidos aparecem como falhas em `data/input/relatorio_coleta_rmd.json`; o coletor continua os demais meses. Sem `--sobrescrever`, meses que já possuem JSON são ignorados. Após a coleta, a consolidação atualiza os CSVs e o dashboard; na interface, clique em **Rodar consolidacao** e reabra o painel de gráficos.

IPCA e PIB são entradas opcionais e precisam ser atualizados separadamente nos respectivos CSVs; esses coletores não os baixam.

### Linha de comando
```bash
cd 10_divida_gastos_publicos
python divida_publica.py --cli \
  --entrada data/input \
  --saida data/output \
  --ipca data/input/ipca.csv \
  --pib data/input/pib.csv
```

### Atualização pelo PDF do RMD
O coletor abaixo localiza o PDF publicado na página do Tesouro, extrai os totais e atualiza o JSON. Ao sobrescrever o arquivo, cria um backup `*.json.bak`.

```bash
python -m app.scraper_rmd \
  --pagina https://www.tesourotransparente.gov.br/publicacoes/relatorio-mensal-da-divida-rmd/2000/11 \
  --json data/input/rmd_divida_publica_2000_11.json
```

Para manter uma cópia do PDF baixado:

```bash
python -m app.scraper_rmd --salvar-pdf data/input/pdfs/rmd_2000_11.pdf
```

### Coleta em lote
Gera um JSON por mês. Por padrão, extrai estoque, composição por indexador e fluxos nos formatos reconhecidos. Campos não encontrados permanecem ausentes; a composição só é aceita quando seus percentuais somam aproximadamente 100%. Use `--somente-estoque` para limitar a coleta. A opção antiga `--dados-completos` continua aceita.

A leitura de PDF usa `pdftotext` quando instalado (pacote `poppler-utils` no Linux), com alternativa em `pdfplumber`. Relatórios `.doc` exigem `catdoc`.

```bash
python -m app.coletor_lote_rmd --inicio 2000-11 --fim 2001-12
python divida_publica.py --cli
```

Use `--sobrescrever` para atualizar competências que já existem. O arquivo `data/input/relatorio_coleta_rmd.json` informa sucessos e falhas.

Para preencher os gráficos a partir de arquivos que antes continham apenas estoque:

```bash
python -m app.coletor_lote_rmd --inicio 2000-11 --fim 2026-07 --sobrescrever
python divida_publica.py --cli
```

Depois de consolidar, reabra o painel de gráficos. Nos relatórios recentes, `taxa_flutuante_pct` representa a categoria publicada pelo Tesouro, separada de `selic_pct` dos relatórios antigos. Os fluxos recentes são totais da DPF; `abrangencia_fluxos` identifica essa diferença em relação às ofertas públicas antigas. Emissão líquida não é tratada como impacto de liquidez. Prazo e outros indicadores antigos não são extraídos com as mesmas regras nos relatórios modernos, que usam outras unidades e tabelas.

### Observações metodológicas
- os valores nominais não são substituídos pelos reais
- apenas variáveis monetárias são desinflacionadas
- prazo médio, percentuais de composição e vencimento em 12 meses permanecem nominais em sua unidade original
- `Dívida / PIB` usa séries nominais compatíveis, sem exigir deflacionamento prévio

---

## EN

Python app to consolidate **Brazilian Monthly Debt Report (RMD)** JSON files into a comparable historical series, preserving nominal values and computing a real series when an IPCA file is available.

### Goal
- read multiple monthly RMD JSON files from `data/input`
- extract stock, composition, maturity, 12-month due share, and flows
- preserve the nominal series exactly as published
- compute a real series using IPCA on a common base
- compute `Debt / GDP` when a compatible GDP series is provided
- export CSV, consolidated JSON, text summary, and a PNG dashboard

### Relevant structure
- `app/analise.py`: main consolidation pipeline
- `app/gui.py`: GUI to run the process
- `data/input/`: RMD JSON files plus optional IPCA/GDP files
- `data/output/`: generated artifacts
- `divida_publica.py`: CLI entry point

### Expected inputs
The app automatically reads every `*.json` file in `data/input`.

Optional files:
- `data/input/ipca.csv`
  - minimum columns: `periodo`, `ipca_indice`
- `data/input/pib.csv`
  - minimum columns: `periodo`, `pib_nominal_brl_bilhoes`

### Outputs
- `data/output/serie_divida_publica_consolidada.json`
- `data/output/serie_divida_publica_consolidada.csv`
- `data/output/resumo_divida_publica.txt`
- `data/output/dashboard_divida_publica.png`

### GUI
```bash
cd 10_divida_gastos_publicos
python -m app
```

### CLI
```bash
cd 10_divida_gastos_publicos
python divida_publica.py --cli \
  --entrada data/input \
  --saida data/output \
  --ipca data/input/ipca.csv \
  --pib data/input/pib.csv
```

## Gastos públicos por categoria — Tesouro Transparente

O projeto também coleta a base oficial [Despesas e Transferências Totais da União (critério valor pago)](https://www.tesourotransparente.gov.br/ckan/dataset/despesas-e-transferencias-totais). O catálogo CKAN fornece os links atuais das planilhas; não é necessário editar URLs mensalmente. A coleta usa `requests` e a leitura das planilhas usa `openpyxl`.

Na interface iniciada com `python divida_publica.py`, clique em **Gastos públicos por categoria**. Selecione ano, mês ou acumulado disponível e agrupe por função (saúde, educação etc.), subfunção, órgão ou natureza do gasto. O filtro **Investimentos (GND 4)** mostra apenas a parcela classificada como investimento; **Despesas primárias** usa a classificação da própria base. O gráfico mostra as 12 maiores categorias, e a tabela lista todas. **Coletar último ano** atualiza os dados sem bloquear a janela.

```bash
source .venv/bin/activate
pip install -r requirements.txt
python divida_publica.py
```

Coleta pelo terminal:

```bash
# Descobrir anos oferecidos pelo Tesouro
python -m app.gastos_publicos --listar-anos

# Último ano disponível (padrão) ou anos específicos
python -m app.gastos_publicos
python -m app.gastos_publicos --anos 2026

# Forçar novo download, mesmo quando o cache é válido
python -m app.gastos_publicos --anos 2026 --atualizar

# Reprocessar sem internet
python -m app.gastos_publicos --arquivo data/input/gastos_publicos/despesas_2026.xlsx --anos 2026
```

Arquivos produzidos:

- `data/input/gastos_publicos/`: planilha original, catálogo e identificação da fonte do download.
- `data/output/gastos_publicos/gastos_ANO_detalhados.csv`: pagamentos com função, subfunção, órgão, grupo de despesa, programa, ação e categoria RTN.
- `data/output/gastos_publicos/gastos_ANO_categorias.csv`: pagamentos agregados por mês e classificações, usados pelo painel.
- `data/output/gastos_publicos/gastos_ANO_resumo.json`: totais mensais, contagens de validação, fonte, data da coleta e SHA-256.

Os valores estão em **reais correntes**, com centavos. Pagamentos totais incluem despesas pagas e restos a pagar pagos, sem somar esses componentes uma segunda vez. A coleta ignora abas de resumo para evitar duplicidade, preserva ajustes negativos e distingue ausência de pagamento informado de zero. Confere competência e soma dos componentes. Se a própria fonte tiver uma soma divergente, preserva PAGAMENTOS_TOTAIS e registra linha, competência e diferença em `divergencias_componentes` no resumo do ano. Competências ou números inválidos interrompem o processamento antes de substituir as saídas do ano. Reexecutar substitui o ano, sem acrescentar duplicatas.

**Cobertura:** União, conforme a base publicada pelo Tesouro, incluindo transferências e despesas financeiras. Não representa o gasto consolidado de todos os entes públicos. Somar todas as linhas não reproduz necessariamente a despesa primária do RTN, que exige filtros e ajustes próprios. Gasto em uma função, como educação, inclui outras naturezas além de investimento. Meses ainda não publicados não são preenchidos com zero. Planilhas históricas com colunas diferentes das reconhecidas são recusadas com mensagem explícita.

### Histórico de gastos: ano a ano e mês a mês

No painel **Gastos públicos por categoria**, clique em **Coletar todo o histórico** para percorrer todos os anos encontrados no catálogo. Depois selecione o **Ano** e, em **Período**, um mês ou o **Acumulado disponível**. A primeira coleta baixa e processa as planilhas anuais; as seguintes reaproveitam as bases sem mudanças. Falhas em um ano não interrompem os demais, e os detalhes ficam em `relatorio_coleta_historica.json`.

```bash
# Todos os anos disponibilizados pelo Tesouro, descobertos automaticamente
python -m app.gastos_publicos --todos-anos

# Um intervalo de anos, inclusive as duas pontas
python -m app.gastos_publicos --inicio 2008 --fim 2026

# Anos específicos, mantendo o detalhamento mensal
python -m app.gastos_publicos --anos 2020 2023 2026
```

Além dos arquivos por ano, a coleta gera em `data/output/gastos_publicos/`:

- `serie_gastos_mensal.csv`: total pago, investimentos pagos e pagamentos classificados como primários, por mês.
- `serie_gastos_anual.csv`: os mesmos valores somados por ano, com `meses_disponiveis` e `ano_completo`.
- `relatorio_coleta_historica.json`: resultado de cada ano na execução mais recente, meses reconhecidos e erros encontrados.

As séries consolidadas incluem todos os anos já processados na pasta de saída, inclusive os preservados de execuções anteriores. `ano_completo=True` indica presença dos 12 meses; não é garantia de que a fonte não sofrerá revisões. Meses ausentes não são interpolados. As comparações são em valores nominais, sem correção pela inflação. A primeira execução completa pode levar vários minutos.

A coleta histórica usa três processos por padrão. Para limitar o consumo de recursos ou executar sequencialmente, informe `--processos 1`; em máquinas com capacidade disponível, use até oito processos, por exemplo:

```bash
python -m app.gastos_publicos --todos-anos --processos 6
```
