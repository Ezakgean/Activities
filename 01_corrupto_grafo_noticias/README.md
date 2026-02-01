# 01_corrupto_grafo_noticias

Aplicacao em Python que usa **Vertex AI Search (Discovery Engine)** para buscar noticias, coletar titulos e gerar uma rede de palavras relacionadas. O foco e portugues (pt-BR).

## Como funciona
1. Consulta o Vertex AI Search (Search Service).
2. Extrai titulos dos resultados.
3. Normaliza o texto e remove stopwords em portugues.
4. Gera um grafo com a palavra central e as palavras mais frequentes.

## Requisitos
- Python 3.10+
- Dependencias em `requirements.txt`
- Projeto no Google Cloud com a **Discovery Engine API** habilitada
- Um **Search App/Engine** com dados ingestados
- Credenciais via service account **ou** Application Default Credentials (ADC)

## Instalacao
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Interface grafica (recomendado)
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

## Uso (CLI)
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

## Configuracao do Vertex AI Search (resumo)
1. Habilite a **Discovery Engine API** no projeto.
2. Crie um **Search App/Engine** no Vertex AI Search.
3. Conecte um data store e conclua a ingestao/indexacao.
4. Pegue o **Engine ID** do app.
5. Configure credenciais (ADC ou service account).

## Saidas
- `reports/titles.txt`: titulos coletados
- `reports/words.csv`: palavras e frequencias
- `reports/graph.html`: rede interativa

## Boas praticas do projeto
- Validacao de parametros (pages/top) com limites seguros.
- Pipeline reutilizado entre CLI e GUI.
- Funcoes pequenas e separadas por responsabilidade.
- Logs basicos para facilitar depuracao.
- Nao versionar credenciais sensiveis.

## Observacoes
- No Linux, o Tkinter pode exigir instalacao do pacote `python3-tk`.
- Custos e cotas dependem da configuracao do Vertex AI Search.
- Use com responsabilidade e respeite os termos do Google.

## Troubleshooting
- **Erro de autenticacao**: verifique `GOOGLE_APPLICATION_CREDENTIALS` ou execute o login ADC.
- **Erro de permissao**: confirme IAM no projeto e acesso ao Discovery Engine.
- **Nenhum titulo**: revise se o Engine tem dados e se o data store foi indexado.
