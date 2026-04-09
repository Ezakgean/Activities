# 05_salario_x_escolaridade

**Idioma / Language:** [Portugues](#pt-br) | [English](#en)

---

## PT-BR

Template inicial em Python para um novo programa seguindo a mesma estrutura dos demais modulos do repositorio. Esta base ja vem com GUI, execucao por linha de comando, pasta de entrada, pasta de saida e um pipeline inicial de inspecao de dados tabulares.

### Objetivo desta base
- padronizar a estrutura do modulo `05_...`
- facilitar a criacao de um novo programa sem recomecar do zero
- deixar um ponto unico para evoluir a logica principal depois

### Como funciona
1. Carrega um arquivo tabular (`.csv`, `.xlsx` ou `.xls`).
2. Faz uma leitura inicial do esquema e do volume de dados.
3. Gera um resumo textual da execucao.
4. Exporta inventario de colunas, amostra dos dados e estatisticas numericas.
5. Opcionalmente gera um PDF simples com o resumo.

### Arquivo de exemplo
- `data/input/exemplo_salario_escolaridade.csv`

### Requisitos
- Python 3.10+
- Dependencias instaladas a partir do `requirements.txt` da raiz do repositorio

### Instalacao
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
```

### Interface grafica (recomendado)
```bash
cd 05_salario_x_escolaridade
python -m app
```

Na GUI:
- escolha o arquivo de entrada
- escolha a pasta de saida
- clique em **Executar**
- opcionalmente clique em **Gerar PDF**

### Uso em linha de comando
```bash
cd 05_salario_x_escolaridade
python salario_escolaridade.py --arquivo data/input/exemplo_salario_escolaridade.csv --saida data/output --pdf
```

### Saidas
- `data/output/resumo_salario_escolaridade.txt`
- `data/output/colunas_detectadas.csv`
- `data/output/amostra_dados.csv`
- `data/output/estatisticas_numericas.csv`
- `data/output/relatorio_salario_escolaridade.pdf` (opcional)

### Estrutura de pastas relevante
- `app/gui.py`: interface grafica.
- `app/analise.py`: pipeline inicial do modulo.
- `data/input/`: arquivos de entrada.
- `data/output/`: destino padrao das saidas.
- `salario_escolaridade.py`: ponto de entrada em CLI.

### Observacoes
- O modulo esta pronto para servir como base de um novo programa na mesma estrutura dos anteriores.
- A logica principal pode ser evoluida centralmente em `app/analise.py`.
- No Linux, o Tkinter pode exigir o pacote `python3-tk`.

---

## EN

Initial Python template for a new program following the same structure as the other modules in this repository. This base already includes a GUI, CLI entry point, input/output folders, and a starter pipeline for tabular data inspection.

### Purpose of this base
- standardize the `05_...` module structure
- make it easier to start a new program without rebuilding everything
- keep a single place to evolve the core logic later

### How it works
1. Loads a tabular file (`.csv`, `.xlsx`, or `.xls`).
2. Performs an initial read of the schema and data volume.
3. Generates a text summary of the execution.
4. Exports a column inventory, data sample, and numeric statistics.
5. Optionally generates a simple PDF report.

### Example input file
- `data/input/exemplo_salario_escolaridade.csv`

### Requirements
- Python 3.10+
- Dependencies installed from the repository root `requirements.txt`

### Installation
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
```

### GUI (recommended)
```bash
cd 05_salario_x_escolaridade
python -m app
```

### CLI usage
```bash
cd 05_salario_x_escolaridade
python salario_escolaridade.py --arquivo data/input/exemplo_salario_escolaridade.csv --saida data/output --pdf
```

### Outputs
- `data/output/resumo_salario_escolaridade.txt`
- `data/output/colunas_detectadas.csv`
- `data/output/amostra_dados.csv`
- `data/output/estatisticas_numericas.csv`
- `data/output/relatorio_salario_escolaridade.pdf` (optional)

### Relevant folder structure
- `app/gui.py`: GUI layer.
- `app/analise.py`: starter pipeline for the module.
- `data/input/`: input files.
- `data/output/`: default output directory.
- `salario_escolaridade.py`: CLI entry point.
