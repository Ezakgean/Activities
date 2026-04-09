# 01_corrupto_grafo_noticias

Python app that uses **Vertex AI Search (Discovery Engine)** to search news, collect titles, and generate a related-word network in Portuguese.

## Goal
- query a Vertex AI Search App/Engine
- collect result titles
- normalize text and remove Portuguese stopwords
- build a network around the query and its most frequent related terms

## How it works
1. Sends a query to Vertex AI Search.
2. Collects titles from the response.
3. Cleans, tokenizes, and normalizes the text.
4. Counts frequencies and builds the graph structure.
5. Exports titles, frequencies, and the interactive visualization.

## Requirements
- Python 3.10+
- Dependencies in `requirements.txt`
- Google Cloud project with **Discovery Engine API** enabled
- A **Search App/Engine** with indexed data
- Credentials via service account or Application Default Credentials (ADC)

## Installation
```bash
cd 01_corrupto_grafo_noticias
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## GUI
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
- `Credentials JSON`, if needed

Use **Test connection** before running the query.

## CLI usage
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

## Outputs
- `reports/titles.txt`
- `reports/words.csv`
- `reports/graph.html`

## Relevant structure
- `src/app.py`: GUI
- `src/main.py`: CLI entry point
- `src/search.py`: Vertex AI Search integration
- `src/text.py`: text cleanup and normalization
- `src/graph.py`: graph generation

## Notes
- On Linux, Tkinter may require `python3-tk`.
- Costs and quotas depend on your Vertex AI Search setup.
- Do not commit sensitive credentials.

## Troubleshooting
- **Authentication error**: validate `GOOGLE_APPLICATION_CREDENTIALS` or use ADC login.
- **Permission error**: confirm IAM access to Discovery Engine.
- **No results**: verify that the Engine contains indexed data.
