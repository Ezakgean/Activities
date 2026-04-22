# 07_mineracao_emocao

**Idioma / Language:** [Português](#pt-br) | [English](#en)

---

## PT-BR

Aplicação em Python para a atividade 07 de mineração de emoção, classificando frases em português nas classes `alegria`, `desgosto`, `medo` e `tristeza` por meio de um classificador Naive Bayes com interface gráfica no mesmo padrão das demais activities.

### Contexto do exercício
O exercício parte de uma base rotulada de frases curtas em português e busca identificar a emoção predominante em novas entradas. Nesta versão, a atividade foi reorganizada em módulos de análise, interface e dados, seguindo a convenção do repositório.

### Como funciona
1. Normaliza o texto, remove stopwords e reduz variações simples de sufixo.
2. Treina um classificador Bernoulli Naive Bayes com a base rotulada da atividade.
3. Avalia o modelo em um conjunto de teste interno e monta a matriz de confusão.
4. Lê um arquivo `TXT` ou `CSV` com frases novas.
5. Gera previsões, dashboard PNG, tabelas CSV, resumo textual e PDF opcional.

### Requisitos
- Python 3.10+
- Dependências instaladas a partir do `requirements.txt` da raiz do repositório

### Instalação
```bash
cd 07_mineracao_emocao
python -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
```

### Interface gráfica
```bash
cd 07_mineracao_emocao
python -m app
```

Na GUI:
- use a tela `Execucao` para selecionar um arquivo `TXT` ou `CSV` e a pasta de saída
- rode a classificação e acompanhe o status da rodada
- navegue pelo menu superior entre `Dashboard`, `Resumo`, `Previsoes`, `Matriz` e `Arquivos`
- use **Gerar PDF** após a execução, se quiser consolidar o relatório

### Linha de comando
```bash
cd 07_mineracao_emocao
python mineracao.py --arquivo data/input/frases_exemplo.txt --saida data/output --pdf
```

### Formatos aceitos
- `TXT`: uma frase por linha
- `CSV`: coluna `frase`, coluna `texto` ou primeira coluna do arquivo

### Saídas
- `data/output/resumo_mineracao_emocao.txt`
- `data/output/previsoes_emocoes.csv`
- `data/output/matriz_confusao_emocoes.csv`
- `data/output/erros_classificacao_emocoes.csv`
- `data/output/metricas_modelo_emocoes.csv`
- `data/output/dashboard_mineracao_emocao.png`
- `data/output/relatorio_mineracao_emocao.pdf`

### Estrutura relevante
- `app/gui.py`: interface gráfica, navegação entre telas e renderização do dashboard
- `app/analise.py`: pipeline de classificação, métricas e exportação dos artefatos
- `app/dataset.py`: base rotulada usada no treino e no teste
- `data/input/frases_exemplo.txt`: arquivo padrão para testar a atividade
- `data/output/`: diretório padrão de saída
- `mineracao.py`: ponto de entrada em CLI

### Observações
- A atividade usa um Naive Bayes com presença de tokens, alinhado ao espírito do exercício original.
- A normalização textual foi implementada sem dependências extras além das já usadas no repositório.
- No Linux, o Tkinter pode exigir `python3-tk`.

---

## EN

Python app for activity 07 emotion mining, classifying Portuguese sentences into `alegria`, `desgosto`, `medo`, and `tristeza` through a Naive Bayes classifier with a GUI that matches the pattern of the other activities.

### Exercise context
The exercise starts from a labeled dataset of short Portuguese sentences and aims to identify the predominant emotion in new inputs. In this version, the activity was reorganized into analysis, GUI, and data modules following the repository convention.

### How it works
1. Normalizes text, removes stopwords, and trims simple suffix variations.
2. Trains a Bernoulli Naive Bayes classifier on the labeled activity dataset.
3. Evaluates the model on an internal test split and builds a confusion matrix.
4. Reads a `TXT` or `CSV` file with new sentences.
5. Generates predictions, a PNG dashboard, CSV tables, a text summary, and an optional PDF.

### Requirements
- Python 3.10+
- Dependencies installed from the repository root `requirements.txt`

### Installation
```bash
cd 07_mineracao_emocao
python -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
```

### GUI
```bash
cd 07_mineracao_emocao
python -m app
```

Inside the GUI:
- use the `Execucao` screen to select a `TXT` or `CSV` input and the output folder
- run the classification and monitor the current round status
- navigate through `Dashboard`, `Resumo`, `Previsoes`, `Matriz`, and `Arquivos`
- use **Gerar PDF** after execution if you want the consolidated report

### CLI usage
```bash
cd 07_mineracao_emocao
python mineracao.py --arquivo data/input/frases_exemplo.txt --saida data/output --pdf
```

### Accepted formats
- `TXT`: one sentence per line
- `CSV`: `frase` column, `texto` column, or the first column in the file

### Outputs
- `data/output/resumo_mineracao_emocao.txt`
- `data/output/previsoes_emocoes.csv`
- `data/output/matriz_confusao_emocoes.csv`
- `data/output/erros_classificacao_emocoes.csv`
- `data/output/metricas_modelo_emocoes.csv`
- `data/output/dashboard_mineracao_emocao.png`
- `data/output/relatorio_mineracao_emocao.pdf`

### Relevant structure
- `app/gui.py`: GUI, screen navigation, and dashboard rendering
- `app/analise.py`: classification pipeline, metrics, and artifact export
- `app/dataset.py`: labeled dataset used for training and testing
- `data/input/frases_exemplo.txt`: default input file for the activity
- `data/output/`: default output directory
- `mineracao.py`: CLI entry point

### Notes
- The activity uses token-presence Naive Bayes, staying close to the original exercise intent.
- Text normalization was implemented without adding extra dependencies beyond those already used in the repository.
- On Linux, Tkinter may require `python3-tk`.
