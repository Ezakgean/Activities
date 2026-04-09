# 01_corrupto_grafo_noticias

**Idioma / Language:** [Português](#pt-br) | [English](#en)

---

## PT-BR

Aplicação em Python que usa **Vertex AI Search (Discovery Engine)** para buscar notícias, coletar títulos e gerar uma rede de palavras relacionadas em português.

### Objetivo
- consultar um Search App/Engine no Vertex AI Search
- extrair títulos dos resultados
- normalizar o texto e remover stopwords em português
- gerar uma rede com a palavra central e os termos mais frequentes

### Como funciona
1. Envia a consulta ao Vertex AI Search.
2. Coleta os títulos retornados.
3. Limpa, tokeniza e normaliza o texto.
4. Conta frequências e monta a estrutura do grafo.
5. Exporta títulos, frequências e a visualização interativa.

### Requisitos
- Python 3.10+
- Dependências em `requirements.txt`
- Projeto no Google Cloud com **Discovery Engine API** habilitada
- Um **Search App/Engine** com dados indexados
- Credenciais via service account ou Application Default Credentials (ADC)

### Instalação
```bash
cd 01_corrupto_grafo_noticias
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Interface gráfica
```bash
cd 01_corrupto_grafo_noticias
python -m src.app
```
Ou:
```bash
cd 01_corrupto_grafo_noticias
python -m src
```

Preencha na GUI:
- `Project ID`
- `Location` como `global`, quando aplicável
- `Engine ID`
- `Credenciais JSON`, se quiser apontar diretamente para a service account

Use **Testar conexão** antes de executar a busca.

### Uso em linha de comando
```bash
cd 01_corrupto_grafo_noticias

export GOOGLE_CLOUD_PROJECT="SEU_PROJECT_ID"
export VERTEX_SEARCH_LOCATION="global"
export VERTEX_SEARCH_ENGINE_ID="SEU_ENGINE_ID"
export GOOGLE_APPLICATION_CREDENTIALS="/caminho/para/sa.json"

python -m src.main --query "corrupcao" --pages 2 --top 30 \
  --project-id "$GOOGLE_CLOUD_PROJECT" \
  --location "$VERTEX_SEARCH_LOCATION" \
  --engine-id "$VERTEX_SEARCH_ENGINE_ID" \
  --credentials "$GOOGLE_APPLICATION_CREDENTIALS"
```

### Saídas
- `reports/titles.txt`: títulos coletados
- `reports/words.csv`: palavras e frequências
- `reports/graph.html`: rede interativa

### Estrutura relevante
- `src/app.py`: GUI para configurar consulta e credenciais
- `src/main.py`: ponto de entrada em CLI
- `src/search.py`: integração com Vertex AI Search
- `src/text.py`: limpeza e normalização do texto
- `src/graph.py`: geração da rede de palavras
- `reports/`: saída dos artefatos gerados

### Observações
- No Linux, o Tkinter pode exigir `python3-tk`.
- Custos, cotas e latência dependem da configuração do Vertex AI Search.
- Não versionar credenciais sensíveis.

### Troubleshooting
- **Erro de autenticação**: valide `GOOGLE_APPLICATION_CREDENTIALS` ou faça login por ADC.
- **Erro de permissão**: confirme IAM e acesso ao Discovery Engine.
- **Nenhum resultado**: verifique se o Engine possui dados indexados.

---

## EN

Python app that uses **Vertex AI Search (Discovery Engine)** to search news, collect titles, and generate a related-word network in Portuguese.

### Goal
- query a Vertex AI Search App/Engine
- collect returned titles
- normalize text and remove Portuguese stopwords
- build a network centered on the query and its most frequent related terms

### How it works
1. Sends a query to Vertex AI Search.
2. Collects result titles.
3. Cleans, tokenizes, and normalizes the text.
4. Counts frequencies and builds the graph structure.
5. Exports titles, frequencies, and the interactive visualization.

### Requirements
- Python 3.10+
- Dependencies in `requirements.txt`
- Google Cloud project with **Discovery Engine API** enabled
- A **Search App/Engine** with indexed data
- Credentials via service account or Application Default Credentials (ADC)

### Installation
```bash
cd 01_corrupto_grafo_noticias
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### GUI
```bash
cd 01_corrupto_grafo_noticias
python -m src.app
```
Or:
```bash
cd 01_corrupto_grafo_noticias
python -m src
```

Fill in:
- `Project ID`
- `Location`, such as `global`
- `Engine ID`
- `Credentials JSON`, if you want to point directly to a service-account file

Use **Test connection** before running the query.

### CLI usage
```bash
cd 01_corrupto_grafo_noticias

export GOOGLE_CLOUD_PROJECT="YOUR_PROJECT_ID"
export VERTEX_SEARCH_LOCATION="global"
export VERTEX_SEARCH_ENGINE_ID="YOUR_ENGINE_ID"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/sa.json"

python -m src.main --query "corrupcao" --pages 2 --top 30 \
  --project-id "$GOOGLE_CLOUD_PROJECT" \
  --location "$VERTEX_SEARCH_LOCATION" \
  --engine-id "$VERTEX_SEARCH_ENGINE_ID" \
  --credentials "$GOOGLE_APPLICATION_CREDENTIALS"
```

### Outputs
- `reports/titles.txt`: collected titles
- `reports/words.csv`: words and frequencies
- `reports/graph.html`: interactive network

### Relevant structure
- `src/app.py`: GUI for query and credential setup
- `src/main.py`: CLI entry point
- `src/search.py`: Vertex AI Search integration
- `src/text.py`: text cleanup and normalization
- `src/graph.py`: word-network generation
- `reports/`: generated artifacts

### Notes
- On Linux, Tkinter may require `python3-tk`.
- Costs, quotas, and latency depend on your Vertex AI Search setup.
- Do not commit sensitive credentials.

### Troubleshooting
- **Authentication error**: validate `GOOGLE_APPLICATION_CREDENTIALS` or use ADC login.
- **Permission error**: confirm IAM access to Discovery Engine.
- **No results**: verify that the Engine contains indexed data.
