from __future__ import annotations

"""CLI entrypoint and pipeline orchestration."""

import argparse
import logging
from collections import Counter
from pathlib import Path

from .config import normalize_settings
from .graph import build_star_graph, save_graph_html
from .search import fetch_titles
from .text import filter_tokens, normalize, tokenize

logger = logging.getLogger(__name__)


def save_titles(titles: list[str], output_path: Path) -> None:
    """Persist titles to a text file."""
    output_path.write_text("\n".join(titles), encoding="utf-8")


def save_word_counts(counts: Counter, output_path: Path) -> None:
    """Persist word counts to a CSV file."""
    lines = ["word,count"]
    for word, count in counts.most_common():
        lines.append(f"{word},{count}")
    output_path.write_text("\n".join(lines), encoding="utf-8")


def run_pipeline(query: str, pages: int, top: int, api_key: str | None, cx: str | None) -> dict:
    """Run the end-to-end pipeline and return a result dict."""
    settings = normalize_settings(api_key, cx, query, pages, top)
    logger.info("Buscando titulos para query='%s' (pages=%s)", settings.query, settings.pages)
    titles = fetch_titles(settings.query, pages=settings.pages, api_key=settings.api_key, cx=settings.cx)
    if not titles:
        return {"titles": [], "counts": Counter(), "output_dir": None, "message": "Nenhum titulo encontrado."}

    tokens = []
    for title in titles:
        tokens.extend(filter_tokens(tokenize(title)))

    counts = Counter(tokens)

    center_display = settings.query.strip().lower()
    center_norm = normalize(settings.query)
    if center_norm in counts:
        del counts[center_norm]
    top_counts = dict(counts.most_common(settings.top))

    output_dir = Path(__file__).resolve().parents[1] / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    save_titles(titles, output_dir / "titles.txt")
    save_word_counts(counts, output_dir / "words.csv")

    graph = build_star_graph(center_display, top_counts)
    save_graph_html(graph, str(output_dir / "graph.html"))

    return {
        "titles": titles,
        "counts": counts,
        "output_dir": output_dir,
        "message": "OK",
    }


def main() -> None:
    """CLI wrapper around the pipeline."""
    parser = argparse.ArgumentParser(description="Gera rede de palavras a partir de titulos do Google.")
    parser.add_argument("--query", default="corrupcao", help="Termo de busca")
    parser.add_argument("--pages", type=int, default=1, help="Numero de paginas de resultado")
    parser.add_argument("--top", type=int, default=30, help="Numero de palavras no grafo")
    parser.add_argument("--api-key", default=None, help="Google API Key (ou GOOGLE_API_KEY)")
    parser.add_argument("--cx", default=None, help="Google CSE ID (ou GOOGLE_CSE_ID)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    result = run_pipeline(args.query, args.pages, args.top, args.api_key, args.cx)
    titles = result["titles"]
    counts = result["counts"]
    output_dir = result["output_dir"]

    if not titles:
        print(result["message"])
        return

    print(f"Titulos coletados: {len(titles)}")
    print("Top palavras:")
    for word, count in counts.most_common(10):
        print(f"- {word}: {count}")
    print(f"Arquivo: {output_dir / 'titles.txt'}")
    print(f"Arquivo: {output_dir / 'words.csv'}")
    print(f"Grafo: {output_dir / 'graph.html'}")


if __name__ == "__main__":
    main()
