# 02_IPO_DATAS

**Idioma / Language:** [Português](#pt-br) | [English](#en)

---

## PT-BR

Scraping da pagina da CVM (SRE) para coletar registros de ofertas e filtrar apenas IPOs, extraindo detalhes do registro e a tabela de especies.

### Como funciona
1. Abre a pagina de consulta da CVM (SRE).
2. Seleciona tipo (ex.: ACOES) e ano.
3. Percorre os resultados com paginacao.
4. Abre cada registro e extrai os detalhes do BODY.
5. Mantem somente IPO = "SIM".
6. Extrai a tabela "ESPECIES".
7. Salva em JSON (merge por chave unica) e opcionalmente CSV.

### O que exatamente o script faz (detalhado)
Fluxo completo executado por `app/scraping/sre_consulta.py`:
- Abre `https://sistemas.cvm.gov.br/port/redir.asp?subpage=consulta` e procura o frame correto contendo os selects de consulta.
- Seleciona `TipoEmis` (ex.: ACOES) e `Ano`, clicando em “Procura” para carregar os resultados.
- Localiza a tabela de resultados e coleta todos os links de registro, percorrendo pagina por pagina ate nao existir o link “Proxima/Próxima/>>”.
- Para cada link de registro, abre uma nova aba e extrai:
  - Campos do cabecalho via labels (ex.: Numero do Processo, Data Protocolo, Analista, Emissora, IPO, Lider, Encerramento Distribuicao).
  - Primeira linha da tabela “REGISTROS” (Data e Numero do Registro).
  - Todas as linhas validas da tabela “ESPÉCIES”.
- Filtra registros que nao sao IPO (mantem apenas IPO = "SIM"; se o campo nao existir, aceita).
- Filtra linhas espurias da tabela “ESPÉCIES” (rodapes/observacoes) e valida especies com heuristicas:
  - Tipo valido (ex.: ON, PN, UNIT, etc.) ou 1–5 letras maiusculas.
  - Pelo menos um valor numerico em quantidade/preco/volume.
- Normaliza o numero do registro (remove espacos extras e normaliza barras).
- Gera 1 linha de saida por especie (um registro pode virar varias linhas).
- Faz merge com JSON existente usando chave unica `(ano, registro_link, registro_numero, especie_tipo, especie_classe)` para evitar duplicatas.
- Mantem tambem os dados do run atual na GUI para copia sem merge.
- Opcionalmente gera CSV com as mesmas colunas do JSON.

### Campos gerados
Cada linha final contem:
- `ano`, `registro_link`, `registro_texto`
- `emissora`, `numero_processo`, `data_protocolo`, `analista`, `ipo`, `lider`, `enc_distribuicao`
- `registro_data`, `registro_numero`
- `especie_tipo`, `especie_classe`, `especie_quantidade`, `especie_preco`, `especie_volume`, `especie_garantidos`, `especie_sobras`

### Estrutura de pastas relevante
- `app/scraping/sre_consulta.py`: script principal de scraping e exportacao.
- `data/output/`: destino padrao do JSON/CSV (criado automaticamente).
- `requirements.txt`: dependencias Python.
- `scripts/setup.sh`: atalho para instalar dependencias e o Chromium do Playwright.

### Requisitos
- Python 3.10+
- Dependencias em `requirements.txt`
- Playwright com navegadores instalados

### Instalacao
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

Opcional (Linux): se faltar dependencias do sistema para o Playwright, rode:
```bash
python -m playwright install-deps
```

Atalho (faz pip + browsers):
```bash
./scripts/setup.sh
```

### Interface grafica (recomendado)
```bash
python -m app
```

Preencha:
- **TipoEmis** (ex.: `ACOES`)
- **Anos** (ex.: `2005,2008-2010`)
- **JSON out** (pode usar `{ano}` no caminho)
- **CSV out** (opcional, pode usar `{ano}`)
- **Pasta JSON / Pasta CSV**: botao para selecionar a pasta de saida mantendo o nome do arquivo

Observacao: no Linux, o Tkinter pode exigir o pacote `python3-tk`.

#### Copiar JSON na GUI
- **Copiar JSON (merge)**: copia o JSON consolidado (apos merge em disco).
- **Copiar JSON (sem merge)**: copia apenas os dados coletados no run atual.

### Uso (CLI)
```bash
# Com navegador visivel
python -m app.scraping.sre_consulta --ano 2005 --tipo ACOES --headed

# Sem navegador visivel
python -m app.scraping.sre_consulta --ano 2005 --tipo ACOES
```

### Saidas
- JSON default em `data/output/sre_consulta.json`
- CSV opcional quando informado `--csv-out`

### Boas praticas do projeto
- Respeite termos de uso do site e limites de requisicao.
- Rode em horarios de menor carga.
- Guarde os arquivos de saida fora do controle de versao se forem grandes.

### Troubleshooting
- **Erro do Playwright**: rode `python -m playwright install`.
- **Timeout**: tente novamente ou use `--headed` para ver a navegacao.
- **Nenhum resultado**: verifique ano/tipo e a pagina da CVM.

---

## EN

Scraper for CVM (SRE) public page to collect offering records and keep only IPOs, extracting record details and the species table.

### How it works
1. Opens the CVM (SRE) search page.
2. Selects type (e.g., ACOES) and year.
3. Walks all results with pagination.
4. Opens each record and extracts BODY details.
5. Keeps only IPO = "SIM".
6. Extracts the "ESPECIES" table.
7. Saves JSON (merge by unique key) and optional CSV.

### What the script actually does (detailed)
Full flow executed by `app/scraping/sre_consulta.py`:
- Opens `https://sistemas.cvm.gov.br/port/redir.asp?subpage=consulta` and finds the correct frame with the search selects.
- Selects `TipoEmis` (e.g., ACOES) and `Ano`, clicks “Procura” to load results.
- Locates the results table and collects all record links, paginating until no “Proxima/Próxima/>>” link exists.
- For each record link, opens a new tab and extracts:
  - Header fields via labels (e.g., Process Number, Protocol Date, Analyst, Issuer, IPO, Lead, Distribution End).
  - First row of the “REGISTROS” table (Date and Registration Number).
  - All valid rows of the “ESPÉCIES” table.
- Filters out non-IPO records (keeps only IPO = "SIM"; if field is missing, it accepts the record).
- Filters spurious “ESPÉCIES” rows (footers/notes) and validates species with heuristics:
  - Valid type (e.g., ON, PN, UNIT, etc.) or 1–5 uppercase letters.
  - At least one numeric value in quantity/price/volume.
- Normalizes the registration number (trim spaces and normalize slashes).
- Produces 1 output row per species (a single record can become multiple rows).
- Merges into existing JSON using unique key `(ano, registro_link, registro_numero, especie_tipo, especie_classe)` to avoid duplicates.
- Keeps current run data in the GUI to allow copy without merge.
- Optionally exports CSV with the same columns as JSON.

### Output fields
Each final row includes:
- `ano`, `registro_link`, `registro_texto`
- `emissora`, `numero_processo`, `data_protocolo`, `analista`, `ipo`, `lider`, `enc_distribuicao`
- `registro_data`, `registro_numero`
- `especie_tipo`, `especie_classe`, `especie_quantidade`, `especie_preco`, `especie_volume`, `especie_garantidos`, `especie_sobras`

### Relevant folder structure
- `app/scraping/sre_consulta.py`: main scraping/export script.
- `data/output/`: default JSON/CSV output target (auto-created).
- `requirements.txt`: Python dependencies.
- `scripts/setup.sh`: shortcut to install dependencies and Playwright Chromium.

### Requirements
- Python 3.10+
- Dependencies in `requirements.txt`
- Playwright with browsers installed

### Installation
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

Optional (Linux): if Playwright system deps are missing, run:
```bash
python -m playwright install-deps
```

Shortcut (pip + browsers):
```bash
./scripts/setup.sh
```

### GUI (recommended)
```bash
python -m app
```

Fill in:
- **TipoEmis** (e.g., `ACOES`)
- **Anos** (e.g., `2005,2008-2010`)
- **JSON out** (you can use `{ano}` in the path)
- **CSV out** (optional, can use `{ano}`)
- **JSON Folder / CSV Folder**: button to pick the output folder while keeping the filename

Note: on Linux, Tkinter may require the `python3-tk` package.

#### Copy JSON in the GUI
- **Copy JSON (merge)**: copies the consolidated JSON (after merge on disk).
- **Copy JSON (no merge)**: copies only the current run data.

### CLI usage
```bash
# With visible browser
python -m app.scraping.sre_consulta --ano 2005 --tipo ACOES --headed

# Headless
python -m app.scraping.sre_consulta --ano 2005 --tipo ACOES
```

### Outputs
- Default JSON at `data/output/sre_consulta.json`
- Optional CSV when `--csv-out` is provided

### Project best practices
- Respect site terms and request limits.
- Run during off-peak hours.
- Keep large outputs out of version control.

### Troubleshooting
- **Playwright error**: run `python -m playwright install`.
- **Timeout**: retry or use `--headed` to observe navigation.
- **No results**: verify year/type and CVM page availability.
