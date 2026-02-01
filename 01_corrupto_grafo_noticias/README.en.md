# 01_corrupto_grafo_noticias

Python app that uses **Vertex AI Search (Discovery Engine)** to search news, collect titles, and build a related-words network. Focus: Portuguese (pt-BR).

## How it works
1. Calls Vertex AI Search (Search Service).
2. Extracts titles from results.
3. Normalizes text and removes Portuguese stopwords.
4. Builds a graph with the central word and most frequent related words.

## Requirements
- Python 3.10+
- Dependencies in `requirements.txt`
- Google Cloud project with **Discovery Engine API** enabled
- A **Search App/Engine** with ingested data
- Credentials via service account **or** Application Default Credentials (ADC)

## Installation
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## GUI (recommended)
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

## CLI usage
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

## Vertex AI Search setup (summary)
1. Enable the **Discovery Engine API** in your project.
2. Create a **Search App/Engine** in Vertex AI Search.
3. Connect a data store and finish ingestion/indexing.
4. Copy the **Engine ID**.
5. Configure credentials (ADC or service account).

## Outputs
- `reports/titles.txt`: collected titles
- `reports/words.csv`: words and frequencies
- `reports/graph.html`: interactive network

## Project best practices
- Validate parameters (pages/top) with safe limits.
- Reuse the pipeline across CLI and GUI.
- Keep functions small and single-purpose.
- Basic logs for easier debugging.
- Never commit sensitive credentials.

## Notes
- On Linux, Tkinter may require the `python3-tk` package.
- Costs and quotas depend on your Vertex AI Search setup.
- Use responsibly and follow Google terms.

## Troubleshooting
- **Auth error**: check `GOOGLE_APPLICATION_CREDENTIALS` or login with ADC.
- **Permission error**: verify IAM permissions for Discovery Engine.
- **No titles**: confirm the Engine has data and the data store is indexed.
