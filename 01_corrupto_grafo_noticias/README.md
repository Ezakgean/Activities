# 01_corrupto_grafo_noticias

**Idioma / Language:** [Português](#pt-br) | [English](#en)

---

## PT-BR

Aplicacao em Python que usa **Vertex AI Search (Discovery Engine)** para buscar noticias, coletar titulos e gerar uma rede de palavras relacionadas. O foco e portugues (pt-BR).

### Como funciona
1. Consulta o Vertex AI Search (Search Service).
2. Extrai titulos dos resultados.
3. Normaliza o texto e remove stopwords em portugues.
4. Gera um grafo com a palavra central e as palavras mais frequentes.

### Requisitos
- Python 3.10+
- Dependencias em `requirements.txt`
- Projeto no Google Cloud com a **Discovery Engine API** habilitada
- Um **Search App/Engine** com dados ingestados
- Credenciais via service account **ou** Application Default Credentials (ADC)

### Instalacao
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Interface grafica (recomendado)
```bash
python -m src.app
```
Ou:
```bash
python -m src
```

Preencha:
- **Project ID**
- **Location** (ex.: `global`)
- **Engine ID**
- **Credenciais JSON (opcional)**: caminho do JSON da service account

Use **Testar conexao** para validar antes de rodar.

### Uso (CLI)
```bash
export GOOGLE_CLOUD_PROJECT="SEU_PROJECT_ID"
export VERTEX_SEARCH_LOCATION="global"
export VERTEX_SEARCH_ENGINE_ID="SEU_ENGINE_ID"
# Opcional: caminho do JSON da service account
export GOOGLE_APPLICATION_CREDENTIALS="/caminho/para/sa.json"

python -m src.main --query "corrupcao" --pages 2 --top 30 \
  --project-id "$GOOGLE_CLOUD_PROJECT" \
  --location "$VERTEX_SEARCH_LOCATION" \
  --engine-id "$VERTEX_SEARCH_ENGINE_ID" \
  --credentials "$GOOGLE_APPLICATION_CREDENTIALS"
```

### Configuracao do Vertex AI Search (resumo)
1. Habilite a **Discovery Engine API** no projeto.
2. Crie um **Search App/Engine** no Vertex AI Search.
3. Conecte um data store e conclua a ingestao/indexacao.
4. Pegue o **Engine ID** do app.
5. Configure credenciais (ADC ou service account).

### Saidas
- `reports/titles.txt`: titulos coletados
- `reports/words.csv`: palavras e frequencias
- `reports/graph.html`: rede interativa

### Boas praticas do projeto
- Validacao de parametros (pages/top) com limites seguros.
- Pipeline reutilizado entre CLI e GUI.
- Funcoes pequenas e separadas por responsabilidade.
- Logs basicos para facilitar depuracao.
- Nao versionar credenciais sensiveis.

### Observacoes
- No Linux, o Tkinter pode exigir instalacao do pacote `python3-tk`.
- Custos e cotas dependem da configuracao do Vertex AI Search.
- Use com responsabilidade e respeite os termos do Google.

### Troubleshooting
- **Erro de autenticacao**: verifique `GOOGLE_APPLICATION_CREDENTIALS` ou execute o login ADC.
- **Erro de permissao**: confirme IAM no projeto e acesso ao Discovery Engine.
- **Nenhum titulo**: revise se o Engine tem dados e se o data store foi indexado.

---

## EN

Python app that uses **Vertex AI Search (Discovery Engine)** to search news, collect titles, and build a related-words network. Focus: Portuguese (pt-BR).

### How it works
1. Calls Vertex AI Search (Search Service).
2. Extracts titles from results.
3. Normalizes text and removes Portuguese stopwords.
4. Builds a graph with the central word and most frequent related words.

### Requirements
- Python 3.10+
- Dependencies in `requirements.txt`
- Google Cloud project with **Discovery Engine API** enabled
- A **Search App/Engine** with ingested data
- Credentials via service account **or** Application Default Credentials (ADC)

### Installation
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### GUI (recommended)
```bash
python -m src.app
```
Or:
```bash
python -m src
```

Fill in:
- **Project ID**
- **Location** (e.g., `global`)
- **Engine ID**
- **Credentials JSON (optional)**: service account JSON path

Use **Test connection** before running.

### CLI usage
```bash
export GOOGLE_CLOUD_PROJECT="YOUR_PROJECT_ID"
export VERTEX_SEARCH_LOCATION="global"
export VERTEX_SEARCH_ENGINE_ID="YOUR_ENGINE_ID"
# Optional: service account JSON path
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/sa.json"

python -m src.main --query "corrupcao" --pages 2 --top 30 \
  --project-id "$GOOGLE_CLOUD_PROJECT" \
  --location "$VERTEX_SEARCH_LOCATION" \
  --engine-id "$VERTEX_SEARCH_ENGINE_ID" \
  --credentials "$GOOGLE_APPLICATION_CREDENTIALS"
```

### Vertex AI Search setup (summary)
1. Enable the **Discovery Engine API** in your project.
2. Create a **Search App/Engine** in Vertex AI Search.
3. Connect a data store and finish ingestion/indexing.
4. Copy the **Engine ID**.
5. Configure credentials (ADC or service account).

### Outputs
- `reports/titles.txt`: collected titles
- `reports/words.csv`: words and frequencies
- `reports/graph.html`: interactive network

### Project best practices
- Validate parameters (pages/top) with safe limits.
- Reuse the pipeline across CLI and GUI.
- Keep functions small and single-purpose.
- Basic logs for easier debugging.
- Never commit sensitive credentials.

### Notes
- On Linux, Tkinter may require the `python3-tk` package.
- Costs and quotas depend on your Vertex AI Search setup.
- Use responsibly and follow Google terms.

### Troubleshooting
- **Auth error**: check `GOOGLE_APPLICATION_CREDENTIALS` or login with ADC.
- **Permission error**: verify IAM permissions for Discovery Engine.
- **No titles**: confirm the Engine has data and the data store is indexed.
