# 01_corrupto_grafo_noticias

Aplicacao em Python que consulta o Google Custom Search por "corrupcao", coleta os titulos e gera uma rede de palavras relacionadas com base nos titulos de noticias. O foco e portugues (pt-BR).

## Como funciona
1. Consulta a API do Google Custom Search.
2. Extrai titulos dos resultados.
3. Normaliza o texto e remove stopwords em portugues.
4. Gera um grafo com a palavra central e as palavras mais frequentes.

## Requisitos
- Python 3.10+
- Dependencias em `requirements.txt`
- Chave da API do Google e ID do Custom Search (CX)
- Billing ativo no projeto do Google Cloud

## Instalacao
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Uso (CLI)
```bash
# Opcional: usar variaveis de ambiente em vez da interface
export GOOGLE_API_KEY="SUA_CHAVE"
export GOOGLE_CSE_ID="SEU_CX"
python -m src.main --query "corrupcao" --pages 2 --top 30
```

## Interface grafica
```bash
python -m src.app
```
Ou:
```bash
python -m src
```

## Boas praticas do projeto
- Variaveis sensiveis informadas na interface (ou via variaveis de ambiente).
- Validacao de parametros (pages/top) com limites seguros.
- Pipeline reutilizado entre CLI e GUI.
- Funcoes pequenas e separadas por responsabilidade.
- Logs basicos para facilitar depuracao.

## Como obter as chaves (Google Custom Search)
### 1) Criar a API Key
1. Acesse o Google Cloud Console.
2. Crie um projeto (ou use um existente).
3. Ative a API **Custom Search API**.
4. Va em **APIs & Services > Credentials** e crie uma **API Key**.
5. Em **Restrictions**, selecione **API restrictions** e escolha **Custom Search API**.

### 2) Criar o mecanismo de busca (CSE) e pegar o CX
1. Acesse o **Google Programmable Search Engine**.
2. Crie um novo mecanismo de pesquisa.
3. Em **Sites to search**, escolha **Search the entire web**.
4. No painel do mecanismo, copie o **Search engine ID (cx)**.

### 3) Billing, limites e custos
- Ative o **Billing** no projeto, caso contrario a API retorna 403.
- A API tem cota gratuita limitada e pode cobrar por volume de consultas.
- Verifique **Quotas & Billing** no Google Cloud Console.

## Saidas
- `reports/titles.txt`: titulos coletados
- `reports/words.csv`: palavras e frequencias
- `reports/graph.html`: rede interativa

## Observacoes
- No Linux, o Tkinter pode exigir instalacao do pacote `python3-tk`.
- O limite de resultados e custos dependem da configuracao da API.
- Use com responsabilidade e respeite os termos do Google.
- Nao versionar chaves sensiveis.

## Troubleshooting
- **Erro 403**: verifique se a API esta habilitada, se o billing esta ativo e se a chave nao esta restrita por referrer.
- **Nenhum titulo**: aumente `--pages` ou revise o CSE para pesquisar na web inteira.
