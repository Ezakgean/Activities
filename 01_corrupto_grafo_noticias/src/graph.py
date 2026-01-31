from __future__ import annotations

"""Graph utilities for word networks."""

from typing import Dict

import networkx as nx
from pyvis.network import Network


def build_star_graph(center: str, word_counts: Dict[str, int]) -> nx.Graph:
    """Build a star graph from a center word and word counts."""
    graph = nx.Graph()
    graph.add_node(center, size=30)
    for word, count in word_counts.items():
        if word == center:
            continue
        graph.add_node(word, size=10 + min(count, 20))
        graph.add_edge(center, word, weight=count)
    return graph


def save_graph_html(graph: nx.Graph, output_path: str) -> None:
    """Save a graph as an interactive HTML file."""
    net = Network(height="750px", width="100%", bgcolor="#ffffff", font_color="#111")
    net.from_nx(graph)
    net.force_atlas_2based(gravity=-50, spring_length=120, spring_strength=0.08)
    net.show(output_path)
