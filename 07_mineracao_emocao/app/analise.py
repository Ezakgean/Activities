from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import math
from pathlib import Path
import re
import textwrap
import unicodedata

from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure
import pandas as pd

from .dataset import TEST_DATA, TRAINING_DATA


SUPPORTED_EXTENSIONS = {".txt", ".csv"}

DEFAULT_INPUT = Path(__file__).resolve().parents[1] / "data" / "input" / "frases_exemplo.txt"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "output"

OUTPUT_SUMMARY = "resumo_mineracao_emocao.txt"
OUTPUT_PREDICTIONS = "previsoes_emocoes.csv"
OUTPUT_CONFUSION = "matriz_confusao_emocoes.csv"
OUTPUT_ERRORS = "erros_classificacao_emocoes.csv"
OUTPUT_METRICS = "metricas_modelo_emocoes.csv"
OUTPUT_PNG = "dashboard_mineracao_emocao.png"
OUTPUT_PDF = "relatorio_mineracao_emocao.pdf"

FIG_BG = "#0f0f10"
PANEL_BG = "#141516"
GRID_COLOR = "#35373b"
TEXT_PRIMARY = "#f7f7f7"
TEXT_MUTED = "#9aa0a6"
BORDER_COLOR = "#2a2c30"
EMOTION_COLORS = {
    "alegria": "#f5b041",
    "desgosto": "#95a5a6",
    "medo": "#e74c3c",
    "tristeza": "#3498db",
}
EMOTION_ORDER = ("alegria", "desgosto", "medo", "tristeza")

RAW_STOPWORDS = {
    "a",
    "agora",
    "ainda",
    "algo",
    "algum",
    "alguma",
    "algumas",
    "alguns",
    "ao",
    "aos",
    "aquela",
    "aquelas",
    "aquele",
    "aqueles",
    "as",
    "ate",
    "até",
    "com",
    "como",
    "da",
    "das",
    "de",
    "dela",
    "dele",
    "deles",
    "depois",
    "do",
    "dos",
    "e",
    "ela",
    "elas",
    "ele",
    "eles",
    "em",
    "entao",
    "então",
    "era",
    "essa",
    "essas",
    "esse",
    "esses",
    "esta",
    "está",
    "estao",
    "estão",
    "estar",
    "estas",
    "este",
    "estes",
    "estou",
    "eu",
    "foi",
    "ha",
    "há",
    "isso",
    "isto",
    "ja",
    "já",
    "la",
    "lá",
    "lhe",
    "mais",
    "mas",
    "me",
    "mesmo",
    "meu",
    "meus",
    "minha",
    "minhas",
    "muito",
    "na",
    "nas",
    "nao",
    "não",
    "nem",
    "no",
    "nos",
    "nós",
    "nossa",
    "nossas",
    "nosso",
    "nossos",
    "o",
    "os",
    "ou",
    "para",
    "pela",
    "pelas",
    "pelo",
    "pelos",
    "por",
    "pra",
    "que",
    "quem",
    "se",
    "sem",
    "ser",
    "seu",
    "seus",
    "só",
    "so",
    "sua",
    "suas",
    "tambem",
    "também",
    "te",
    "tem",
    "tenho",
    "ter",
    "todo",
    "todos",
    "tu",
    "um",
    "uma",
    "umas",
    "uns",
    "vai",
    "vou",
    "voce",
    "você",
}

STEM_SUFFIXES = (
    "mente",
    "amentos",
    "imento",
    "imentos",
    "idades",
    "idade",
    "adora",
    "ador",
    "antes",
    "ante",
    "istas",
    "ista",
    "ezas",
    "eza",
    "icos",
    "icas",
    "ico",
    "ica",
    "osos",
    "osas",
    "oso",
    "osa",
    "ivas",
    "ivos",
    "iva",
    "ivo",
    "adas",
    "ados",
    "ada",
    "ado",
    "idas",
    "idos",
    "ida",
    "ido",
    "coes",
    "cao",
    "ções",
    "ção",
    "eis",
    "ais",
    "ns",
    "es",
    "s",
)


@dataclass
class EmotionModel:
    labels: tuple[str, ...]
    vocabulary: tuple[str, ...]
    class_counts: dict[str, int]
    document_counts: dict[str, Counter]
    total_documents: int
    alpha: float = 1.0


@dataclass
class PipelineResult:
    summary_text: str
    figure: Figure
    metrics_df: pd.DataFrame
    predictions_df: pd.DataFrame
    confusion_df: pd.DataFrame
    errors_df: pd.DataFrame
    output_dir: Path
    summary_path: Path
    predictions_path: Path
    confusion_path: Path
    errors_path: Path
    metrics_path: Path
    dashboard_path: Path
    accuracy: float
    baseline_accuracy: float
    labels: tuple[str, ...]
    input_count: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Classifica frases em portugues nas classes alegria, desgosto, medo e tristeza."
    )
    parser.add_argument(
        "--arquivo",
        type=Path,
        default=DEFAULT_INPUT,
        help="Arquivo TXT ou CSV com frases para classificar.",
    )
    parser.add_argument(
        "--saida",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Pasta onde os arquivos de saida serao gravados.",
    )
    parser.add_argument(
        "--pdf",
        action="store_true",
        help="Gera tambem um PDF com o resumo e o dashboard.",
    )
    return parser.parse_args()


def format_percent(value: float) -> str:
    return f"{value * 100:.1f}%".replace(".", ",")


def format_decimal(value: float) -> str:
    return f"{value:.4f}".replace(".", ",")


def _normalize_basic(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    return "".join(character for character in normalized if not unicodedata.combining(character))


STOPWORDS = {_normalize_basic(word) for word in RAW_STOPWORDS}


def _simple_stem(token: str) -> str:
    for suffix in STEM_SUFFIXES:
        if len(token) > len(suffix) + 2 and token.endswith(suffix):
            token = token[: -len(suffix)]
            break
    return token


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-zA-ZÀ-ÿ]+", text)
    normalized: list[str] = []
    for token in tokens:
        base = _normalize_basic(token)
        if not base or base in STOPWORDS:
            continue
        stemmed = _simple_stem(base)
        if len(stemmed) < 2 or stemmed in STOPWORDS:
            continue
        normalized.append(stemmed)
    return normalized


def load_sentences(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {path}")

    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(f"Formato nao suportado: {suffix}. Use um destes: {supported}")

    if suffix == ".txt":
        sentences = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
        sentences = [sentence for sentence in sentences if sentence]
        if not sentences:
            raise ValueError("O arquivo TXT nao contem frases validas.")
        return sentences

    frame = pd.read_csv(path)
    if frame.empty:
        raise ValueError("O arquivo CSV nao contem linhas.")

    columns = {column.casefold(): column for column in frame.columns}
    if "frase" in columns:
        series = frame[columns["frase"]]
    elif "texto" in columns:
        series = frame[columns["texto"]]
    else:
        series = frame.iloc[:, 0]

    sentences = [str(value).strip() for value in series.tolist() if str(value).strip()]
    if not sentences:
        raise ValueError("Nao foi possivel extrair frases do CSV informado.")
    return sentences


def _prepare_labeled_data(dataset: list[tuple[str, str]]) -> list[tuple[list[str], str]]:
    prepared: list[tuple[list[str], str]] = []
    for sentence, label in dataset:
        prepared.append((tokenize(sentence), label))
    return prepared


def train_model(dataset: list[tuple[str, str]]) -> EmotionModel:
    prepared = _prepare_labeled_data(dataset)
    labels = tuple(label for label in EMOTION_ORDER if any(target == label for _, target in prepared))
    class_counts = {label: 0 for label in labels}
    document_counts = {label: Counter() for label in labels}
    vocabulary: set[str] = set()

    for tokens, label in prepared:
        class_counts[label] += 1
        unique_tokens = set(tokens)
        vocabulary.update(unique_tokens)
        document_counts[label].update(unique_tokens)

    return EmotionModel(
        labels=labels,
        vocabulary=tuple(sorted(vocabulary)),
        class_counts=class_counts,
        document_counts=document_counts,
        total_documents=len(prepared),
    )


def predict_distribution(model: EmotionModel, tokens: list[str]) -> dict[str, float]:
    unique_tokens = set(tokens)
    log_scores: dict[str, float] = {}

    for label in model.labels:
        class_total = model.class_counts[label]
        log_probability = math.log(class_total / model.total_documents)
        counts = model.document_counts[label]

        for token in model.vocabulary:
            present_probability = (counts[token] + model.alpha) / (class_total + 2 * model.alpha)
            if token in unique_tokens:
                log_probability += math.log(present_probability)
            else:
                log_probability += math.log(1.0 - present_probability)

        log_scores[label] = log_probability

    max_score = max(log_scores.values())
    shifted = {label: math.exp(score - max_score) for label, score in log_scores.items()}
    total = sum(shifted.values()) or 1.0
    return {label: shifted[label] / total for label in model.labels}


def predict_sentence(model: EmotionModel, sentence: str) -> dict[str, object]:
    tokens = tokenize(sentence)
    distribution = predict_distribution(model, tokens)
    ordered = sorted(distribution.items(), key=lambda item: item[1], reverse=True)
    best_label, best_probability = ordered[0]
    second_label, second_probability = ordered[1] if len(ordered) > 1 else ("", 0.0)
    return {
        "frase": sentence,
        "tokens_normalizados": ", ".join(tokens),
        "emocao_prevista": best_label,
        "confianca": best_probability,
        "emocao_secundaria": second_label,
        "confianca_secundaria": second_probability,
    }


def classify_sentences(model: EmotionModel, sentences: list[str]) -> pd.DataFrame:
    rows = [predict_sentence(model, sentence) for sentence in sentences]
    return pd.DataFrame(rows)


def evaluate_model(model: EmotionModel, dataset: list[tuple[str, str]]) -> tuple[pd.DataFrame, pd.DataFrame, float]:
    rows: list[dict[str, object]] = []
    expected: list[str] = []
    predicted: list[str] = []

    for sentence, label in dataset:
        prediction = predict_sentence(model, sentence)
        prediction["emocao_esperada"] = label
        rows.append(prediction)
        expected.append(label)
        predicted.append(str(prediction["emocao_prevista"]))

    evaluation_df = pd.DataFrame(rows)
    confusion_df = build_confusion_frame(expected, predicted, model.labels)
    accuracy = float((evaluation_df["emocao_esperada"] == evaluation_df["emocao_prevista"]).mean())
    return evaluation_df, confusion_df, accuracy


def build_confusion_frame(
    expected: list[str],
    predicted: list[str],
    labels: tuple[str, ...],
) -> pd.DataFrame:
    frame = pd.DataFrame(0, index=list(labels), columns=list(labels), dtype=int)
    for expected_label, predicted_label in zip(expected, predicted, strict=True):
        if expected_label not in frame.index:
            frame.loc[expected_label] = 0
        if predicted_label not in frame.columns:
            frame[predicted_label] = 0
        frame.loc[expected_label, predicted_label] += 1
    return frame.reindex(index=list(labels), columns=list(labels), fill_value=0)


def build_metrics_frame(
    model: EmotionModel,
    accuracy: float,
    baseline_accuracy: float,
    input_count: int,
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "acuracia_teste": accuracy,
                "baseline_majoritaria": baseline_accuracy,
                "frases_treinamento": model.total_documents,
                "frases_teste": len(TEST_DATA),
                "frases_arquivo": input_count,
                "tamanho_vocabulario": len(model.vocabulary),
                "classes_modeladas": ", ".join(model.labels),
            }
        ]
    )


def build_top_tokens(model: EmotionModel, limit: int = 5) -> dict[str, list[str]]:
    top_tokens: dict[str, list[str]] = {}
    for label in model.labels:
        counts = model.document_counts[label]
        ranked = [
            token
            for token, _count in sorted(
                counts.items(),
                key=lambda item: (item[1] / max(model.class_counts[label], 1), item[1], item[0]),
                reverse=True,
            )[:limit]
        ]
        top_tokens[label] = ranked
    return top_tokens


def build_summary_text(
    model: EmotionModel,
    metrics_df: pd.DataFrame,
    predictions_df: pd.DataFrame,
    confusion_df: pd.DataFrame,
    accuracy: float,
    baseline_accuracy: float,
    top_tokens: dict[str, list[str]],
) -> str:
    metrics = metrics_df.iloc[0]
    lines = [
        "ATIVIDADE 07 - MINERACAO DE EMOCAO",
        "",
        "Visao geral",
        f"- Frases de treinamento: {int(metrics['frases_treinamento'])}",
        f"- Frases de teste: {int(metrics['frases_teste'])}",
        f"- Frases classificadas na rodada: {int(metrics['frases_arquivo'])}",
        f"- Classes modeladas: {metrics['classes_modeladas']}",
        f"- Tamanho do vocabulario: {int(metrics['tamanho_vocabulario'])}",
        f"- Acuracia no conjunto de teste: {format_percent(accuracy)}",
        f"- Baseline majoritaria: {format_percent(baseline_accuracy)}",
        "",
        "Distribuicao prevista para o arquivo de entrada",
    ]

    predicted_counts = (
        predictions_df["emocao_prevista"].value_counts().reindex(model.labels, fill_value=0)
        if not predictions_df.empty
        else pd.Series(0, index=model.labels)
    )
    for label, count in predicted_counts.items():
        lines.append(f"- {label}: {int(count)} frases")

    lines.append("")
    lines.append("Principais sinais por classe")
    for label in model.labels:
        highlight = ", ".join(top_tokens.get(label, [])) or "-"
        lines.append(f"- {label}: {highlight}")

    if not predictions_df.empty:
        strongest = predictions_df.sort_values("confianca", ascending=False).iloc[0]
        weakest = predictions_df.sort_values("confianca", ascending=True).iloc[0]
        lines.extend(
            [
                "",
                "Rodada atual",
                f"- Maior confianca: {format_percent(float(strongest['confianca']))} | {strongest['emocao_prevista']} | {strongest['frase']}",
                f"- Menor confianca: {format_percent(float(weakest['confianca']))} | {weakest['emocao_prevista']} | {weakest['frase']}",
            ]
        )

    lines.append("")
    lines.append("Matriz de confusao (linhas = esperado, colunas = previsto)")
    lines.extend(confusion_df.to_string().splitlines())
    return "\n".join(lines)


def _style_axis(axis, title: str) -> None:
    axis.set_title(title, color=TEXT_PRIMARY, fontsize=12, fontweight="bold", pad=10)
    axis.set_facecolor(PANEL_BG)
    axis.tick_params(colors=TEXT_MUTED, labelsize=9)
    for spine in axis.spines.values():
        spine.set_color(BORDER_COLOR)
    axis.grid(axis="y", color=GRID_COLOR, linestyle="--", linewidth=0.7, alpha=0.75)
    axis.set_axisbelow(True)


def _plot_bar(axis, series: pd.Series, title: str) -> None:
    _style_axis(axis, title)
    colors = [EMOTION_COLORS.get(label, "#f5821f") for label in series.index]
    bars = axis.bar(series.index, series.values, color=colors, width=0.62)
    axis.set_ylabel("Frases", color=TEXT_MUTED)
    ymax = max(series.max(), 1)
    axis.set_ylim(0, ymax * 1.25)
    for bar in bars:
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(ymax * 0.03, 0.15),
            f"{int(bar.get_height())}",
            ha="center",
            va="bottom",
            color=TEXT_PRIMARY,
            fontsize=9,
        )


def build_dashboard_figure(
    model: EmotionModel,
    predictions_df: pd.DataFrame,
    confusion_df: pd.DataFrame,
) -> Figure:
    train_counts = pd.Series(model.class_counts).reindex(model.labels, fill_value=0)
    prediction_counts = (
        predictions_df["emocao_prevista"].value_counts().reindex(model.labels, fill_value=0)
        if not predictions_df.empty
        else pd.Series(0, index=model.labels)
    )

    recall_values = []
    for label in model.labels:
        row_sum = int(confusion_df.loc[label].sum())
        recall = float(confusion_df.loc[label, label] / row_sum) if row_sum else 0.0
        recall_values.append(recall)
    recall_series = pd.Series(recall_values, index=model.labels)

    figure = Figure(figsize=(14, 10), facecolor=FIG_BG)
    axis_train = figure.add_subplot(221)
    axis_predictions = figure.add_subplot(222)
    axis_confusion = figure.add_subplot(223)
    axis_recall = figure.add_subplot(224)

    _plot_bar(axis_train, train_counts, "Distribuicao de Treinamento")
    _plot_bar(axis_predictions, prediction_counts, "Distribuicao das Previsoes")
    _style_axis(axis_recall, "Recall por Classe no Teste")
    recall_bars = axis_recall.bar(
        recall_series.index,
        recall_series.values,
        color=[EMOTION_COLORS.get(label, "#f5821f") for label in recall_series.index],
        width=0.62,
    )
    axis_recall.set_ylim(0, 1.08)
    axis_recall.set_ylabel("Recall", color=TEXT_MUTED)
    axis_recall.set_yticks([0.0, 0.25, 0.5, 0.75, 1.0])
    axis_recall.set_yticklabels(
        [format_percent(value) for value in [0.0, 0.25, 0.5, 0.75, 1.0]],
        color=TEXT_MUTED,
    )
    for bar in recall_bars:
        axis_recall.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.03,
            format_percent(float(bar.get_height())),
            ha="center",
            va="bottom",
            color=TEXT_PRIMARY,
            fontsize=9,
        )

    axis_confusion.set_facecolor(PANEL_BG)
    axis_confusion.set_title(
        "Matriz de Confusao do Conjunto de Teste",
        color=TEXT_PRIMARY,
        fontsize=12,
        fontweight="bold",
        pad=10,
    )
    heatmap = axis_confusion.imshow(confusion_df.values, cmap="Oranges")
    axis_confusion.set_xticks(range(len(model.labels)))
    axis_confusion.set_yticks(range(len(model.labels)))
    axis_confusion.set_xticklabels(model.labels, color=TEXT_MUTED, rotation=20, ha="right")
    axis_confusion.set_yticklabels(model.labels, color=TEXT_MUTED)
    axis_confusion.set_xlabel("Previsto", color=TEXT_MUTED)
    axis_confusion.set_ylabel("Esperado", color=TEXT_MUTED)
    for row_index in range(confusion_df.shape[0]):
        for column_index in range(confusion_df.shape[1]):
            axis_confusion.text(
                column_index,
                row_index,
                str(int(confusion_df.iat[row_index, column_index])),
                ha="center",
                va="center",
                color=TEXT_PRIMARY,
                fontsize=9,
                fontweight="bold",
            )
    colorbar = figure.colorbar(heatmap, ax=axis_confusion, fraction=0.046, pad=0.04)
    colorbar.outline.set_edgecolor(BORDER_COLOR)
    colorbar.ax.yaxis.set_tick_params(color=TEXT_MUTED)
    for label in colorbar.ax.get_yticklabels():
        label.set_color(TEXT_MUTED)

    figure.tight_layout(pad=2.4)
    return figure


def save_pdf_report(summary_text: str, figure: Figure, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / OUTPUT_PDF

    with PdfPages(pdf_path) as pdf:
        summary_figure = Figure(figsize=(8.27, 11.69), facecolor="white")
        axis = summary_figure.add_subplot(111)
        axis.axis("off")

        wrapped_lines: list[str] = []
        for line in summary_text.splitlines():
            if not line.strip():
                wrapped_lines.append("")
                continue
            wrapped_lines.extend(textwrap.wrap(line, width=92) or [""])

        axis.text(
            0.05,
            0.97,
            "\n".join(wrapped_lines),
            va="top",
            ha="left",
            fontsize=10,
            family="monospace",
        )
        pdf.savefig(summary_figure, bbox_inches="tight")
        pdf.savefig(figure, bbox_inches="tight")

    return pdf_path


def run_pipeline(input_path: Path, output_dir: Path) -> PipelineResult:
    model = train_model(TRAINING_DATA)
    evaluation_df, confusion_df, accuracy = evaluate_model(model, TEST_DATA)
    majority = Counter(label for _sentence, label in TEST_DATA).most_common(1)[0][1]
    baseline_accuracy = majority / len(TEST_DATA)
    sentences = load_sentences(input_path)
    predictions_df = classify_sentences(model, sentences)
    errors_df = evaluation_df[evaluation_df["emocao_esperada"] != evaluation_df["emocao_prevista"]].copy()
    metrics_df = build_metrics_frame(model, accuracy, baseline_accuracy, len(sentences))
    top_tokens = build_top_tokens(model)
    summary_text = build_summary_text(
        model=model,
        metrics_df=metrics_df,
        predictions_df=predictions_df,
        confusion_df=confusion_df,
        accuracy=accuracy,
        baseline_accuracy=baseline_accuracy,
        top_tokens=top_tokens,
    )
    figure = build_dashboard_figure(model, predictions_df, confusion_df)

    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / OUTPUT_SUMMARY
    predictions_path = output_dir / OUTPUT_PREDICTIONS
    confusion_path = output_dir / OUTPUT_CONFUSION
    errors_path = output_dir / OUTPUT_ERRORS
    metrics_path = output_dir / OUTPUT_METRICS
    dashboard_path = output_dir / OUTPUT_PNG

    summary_path.write_text(summary_text, encoding="utf-8")
    predictions_df.to_csv(predictions_path, index=False)
    confusion_df.to_csv(confusion_path, index_label="emocao_esperada")
    errors_df.to_csv(errors_path, index=False)
    metrics_df.to_csv(metrics_path, index=False)
    figure.savefig(dashboard_path, dpi=180, facecolor=figure.get_facecolor(), bbox_inches="tight")

    return PipelineResult(
        summary_text=summary_text,
        figure=figure,
        metrics_df=metrics_df,
        predictions_df=predictions_df,
        confusion_df=confusion_df,
        errors_df=errors_df,
        output_dir=output_dir,
        summary_path=summary_path,
        predictions_path=predictions_path,
        confusion_path=confusion_path,
        errors_path=errors_path,
        metrics_path=metrics_path,
        dashboard_path=dashboard_path,
        accuracy=accuracy,
        baseline_accuracy=baseline_accuracy,
        labels=model.labels,
        input_count=len(sentences),
    )


def main() -> None:
    args = parse_args()
    result = run_pipeline(args.arquivo, args.saida)
    generated_files = [
        result.summary_path,
        result.predictions_path,
        result.confusion_path,
        result.errors_path,
        result.metrics_path,
        result.dashboard_path,
    ]

    if args.pdf:
        pdf_path = save_pdf_report(result.summary_text, result.figure, result.output_dir)
        generated_files.append(pdf_path)

    print(result.summary_text)
    print("\nArquivos gerados:")
    for path in generated_files:
        print(f"- {path}")


if __name__ == "__main__":
    main()
