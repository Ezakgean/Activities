# 02_IPO_DATAS

**Idioma / Language:** [Português](#pt-br) | [English](#en)

---

## PT-BR

Scraper em Python para a consulta pública da CVM (SRE), focado em ofertas do tipo `ACOES`, com filtro de IPO, extração dos detalhes do registro e exportação estruturada em JSON e CSV.

### Objetivo
- navegar na consulta pública da CVM
- coletar todos os registros de um ano e tipo de emissão
- manter apenas registros com `IPO = SIM`
- extrair a tabela de espécies e consolidar os dados

### Como funciona
1. Abre a consulta da CVM e localiza o frame correto.
2. Seleciona `TipoEmis` e `Ano`.
3. Percorre todas as páginas de resultado.
4. Abre cada registro em nova aba.
5. Extrai campos do cabeçalho, a primeira linha da tabela `REGISTROS` e as linhas válidas de `ESPÉCIES`.
6. Mantém apenas IPOs e normaliza o número do registro.
7. Faz merge no JSON final e opcionalmente gera CSV.

### Campos extraídos
Cada linha final pode conter:
- `ano`, `registro_link`, `registro_texto`
- `emissora`, `numero_processo`, `data_protocolo`, `analista`, `ipo`, `lider`, `enc_distribuicao`
- `registro_data`, `registro_numero`
- `especie_tipo`, `especie_classe`, `especie_quantidade`, `especie_preco`, `especie_volume`, `especie_garantidos`, `especie_sobras`

### Requisitos
- Python 3.10+
- Dependências em `requirements.txt`
- Playwright com Chromium instalado

### Instalação
```bash
cd 02_IPO_DATAS
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

Se o sistema exigir dependências adicionais do navegador:
```bash
python -m playwright install-deps
```

Atalho:
```bash
cd 02_IPO_DATAS
./scripts/setup.sh
```

### Interface gráfica
```bash
cd 02_IPO_DATAS
python -m app
```

Na GUI, é possível:
- definir `TipoEmis`
- informar anos únicos ou intervalos como `2008-2010`
- escolher caminhos de saída para JSON e CSV
- usar `{ano}` no nome do arquivo para gerar uma saída por ano
- copiar o JSON consolidado ou apenas os dados do run atual

### Uso em linha de comando
```bash
cd 02_IPO_DATAS

# navegador visível
python -m app.scraping.sre_consulta --ano 2005 --tipo ACOES --headed

# headless com JSON e CSV explícitos
python -m app.scraping.sre_consulta \
  --ano 2005 \
  --tipo ACOES \
  --json-out data/output/sre_consulta_2005.json \
  --csv-out data/output/sre_consulta_2005.csv
```

Opções úteis:
- `--max-registros`: limita a coleta para depuração
- `--headed`: abre o Chromium visível

### Saídas
- JSON consolidado em `data/output/`
- CSV opcional quando `--csv-out` é informado
- no repositório há exemplos como `data/output/sre_consulta_2005.json`

### Estrutura relevante
- `app/gui.py`: GUI para rodar consultas por ano e copiar resultados
- `app/scraping/sre_consulta.py`: scraper principal e fluxo de exportação
- `scripts/setup.sh`: instalação rápida do ambiente
- `data/output/`: pasta de saída dos arquivos gerados

### Observações
- O merge usa chave única por registro e espécie para evitar duplicatas.
- O scraper mantém os dados do run atual em memória para a opção de cópia sem merge.
- Respeite limites e disponibilidade do site da CVM.

### Troubleshooting
- **Erro do Playwright**: rode `python -m playwright install chromium`.
- **Timeout**: tente novamente ou use `--headed`.
- **Nenhum resultado**: confirme ano, tipo e disponibilidade da página da CVM.

---

## EN

Python scraper for the CVM (SRE) public search page, focused on `ACOES` offerings, with IPO filtering, record-detail extraction, and structured JSON/CSV export.

### Goal
- navigate the CVM public search
- collect all records for a given year and issuance type
- keep only records with `IPO = SIM`
- extract the species table and consolidate the data

### How it works
1. Opens the CVM search page and finds the correct frame.
2. Selects `TipoEmis` and `Ano`.
3. Walks through all result pages.
4. Opens each record in a new tab.
5. Extracts header fields, the first `REGISTROS` row, and valid `ESPÉCIES` rows.
6. Keeps only IPO records and normalizes the registration number.
7. Merges into the target JSON and optionally exports CSV.

### Extracted fields
Each final row may include:
- `ano`, `registro_link`, `registro_texto`
- `emissora`, `numero_processo`, `data_protocolo`, `analista`, `ipo`, `lider`, `enc_distribuicao`
- `registro_data`, `registro_numero`
- `especie_tipo`, `especie_classe`, `especie_quantidade`, `especie_preco`, `especie_volume`, `especie_garantidos`, `especie_sobras`

### Requirements
- Python 3.10+
- Dependencies in `requirements.txt`
- Playwright with Chromium installed

### Installation
```bash
cd 02_IPO_DATAS
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

If your system needs extra browser dependencies:
```bash
python -m playwright install-deps
```

Shortcut:
```bash
cd 02_IPO_DATAS
./scripts/setup.sh
```

### GUI
```bash
cd 02_IPO_DATAS
python -m app
```

Inside the GUI you can:
- set `TipoEmis`
- provide single years or ranges such as `2008-2010`
- choose JSON and CSV output paths
- use `{ano}` in filenames to generate one file per year
- copy the merged JSON or only the current-run data

### CLI usage
```bash
cd 02_IPO_DATAS

# visible browser
python -m app.scraping.sre_consulta --ano 2005 --tipo ACOES --headed

# headless with explicit JSON and CSV outputs
python -m app.scraping.sre_consulta \
  --ano 2005 \
  --tipo ACOES \
  --json-out data/output/sre_consulta_2005.json \
  --csv-out data/output/sre_consulta_2005.csv
```

Useful options:
- `--max-registros`: limits collection for debugging
- `--headed`: opens visible Chromium

### Outputs
- consolidated JSON in `data/output/`
- optional CSV when `--csv-out` is provided
- the repository already includes examples such as `data/output/sre_consulta_2005.json`

### Relevant structure
- `app/gui.py`: GUI to run yearly queries and copy results
- `app/scraping/sre_consulta.py`: main scraper and export flow
- `scripts/setup.sh`: quick environment setup
- `data/output/`: generated output folder

### Notes
- Merge uses a unique key by record and species to avoid duplicates.
- The scraper keeps current-run data in memory for copy-without-merge.
- Respect CVM site limits and availability.

### Troubleshooting
- **Playwright error**: run `python -m playwright install chromium`.
- **Timeout**: retry or use `--headed`.
- **No results**: confirm year, type, and CVM page availability.
