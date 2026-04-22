# Activities

Índice rápido: [PT-BR](#pt-br) | [EN](#en)

---

## PT-BR

Repositório com atividades e projetos pessoais em tecnologia, dados e economia. Cada pasta representa um módulo independente, com escopo próprio, exemplos de entrada e saídas geradas localmente.

### Organização
- Os projetos ficam na raiz, com prefixo numérico para manter a ordem.
- `01_` e `02_` têm `requirements.txt` próprios.
- `03_`, `04_`, `05_` e `07_` compartilham o `requirements.txt` da raiz.

### Projetos
- `01_corrupto_grafo_noticias`: busca notícias via Vertex AI Search e gera rede de palavras, arquivo de títulos e CSV de frequências.
- `02_IPO_DATAS`: scraper da CVM (SRE) para ofertas públicas, com filtro de IPO, merge em JSON e CSV opcional.
- `03_regressão_linear`: regressão linear simples entre renda e despesa com alimentação, com GUI, gráfico e PDF.
- `04_regressao_escolas`: análise de regressão escolar com estatísticas descritivas, testes t, modelos OLS e exportação de tabelas.
- `05_salario_x_escolaridade`: análise salarial por escolaridade com regressões por estado, dashboard executivo e relatório em PDF.
- `07_mineracao_emocao`: classificação de emoções em frases em português, com dashboard, matriz de confusão, tabelas e PDF.

### Execução rápida
- `01_corrupto_grafo_noticias`: `cd 01_corrupto_grafo_noticias && python -m src`
- `02_IPO_DATAS`: `cd 02_IPO_DATAS && python -m app`
- `03_regressão_linear`: `cd 03_regressão_linear && python -m app`
- `04_regressao_escolas`: `cd 04_regressao_escolas && python -m app`
- `05_salario_x_escolaridade`: `cd 05_salario_x_escolaridade && python -m app`
- `07_mineracao_emocao`: `cd 07_mineracao_emocao && python -m app`

### Estrutura do repositório
- `src/`: ativos compartilhados do repositório, como a logo usada na interface.
- `requirements.txt`: dependências comuns dos módulos `03_`, `04_` e `05_`.
- Pastas numeradas: cada atividade mantém código, dados e documentação próprios.

---

## EN

Repository with personal activities and projects in technology, data, and economics. Each top-level folder is a standalone module with its own scope, sample inputs, and locally generated outputs.

### Organization
- Projects live at the repository root and use numeric prefixes to preserve order.
- `01_` and `02_` keep their own `requirements.txt`.
- `03_`, `04_`, `05_`, and `07_` share the root `requirements.txt`.

### Projects
- `01_corrupto_grafo_noticias`: searches news through Vertex AI Search and generates a word network, title dump, and frequency CSV.
- `02_IPO_DATAS`: CVM (SRE) scraper for public offerings, with IPO filtering, JSON merge, and optional CSV export.
- `03_regressão_linear`: simple linear regression between income and food expenses, with GUI, chart, and PDF report.
- `04_regressao_escolas`: school-regression analysis with descriptive statistics, t-tests, OLS models, and table exports.
- `05_salario_x_escolaridade`: salary-by-schooling analysis with state-level regressions, executive dashboard, and PDF report.
- `07_mineracao_emocao`: emotion classification for Portuguese sentences, with dashboard, confusion matrix, exported tables, and PDF.

### Quick start
- `01_corrupto_grafo_noticias`: `cd 01_corrupto_grafo_noticias && python -m src`
- `02_IPO_DATAS`: `cd 02_IPO_DATAS && python -m app`
- `03_regressão_linear`: `cd 03_regressão_linear && python -m app`
- `04_regressao_escolas`: `cd 04_regressao_escolas && python -m app`
- `05_salario_x_escolaridade`: `cd 05_salario_x_escolaridade && python -m app`
- `07_mineracao_emocao`: `cd 07_mineracao_emocao && python -m app`

### Repository structure
- `src/`: shared repository assets, such as the logo used by the GUIs.
- `requirements.txt`: shared dependencies for modules `03_`, `04_`, and `05_`.
- Numbered folders: each activity keeps its own code, data, and documentation.
