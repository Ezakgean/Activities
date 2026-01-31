from __future__ import annotations

"""Google Custom Search client."""

import logging
import os
from typing import List

import requests


GOOGLE_CSE_URL = "https://www.googleapis.com/customsearch/v1"
RESULTS_PER_PAGE = 10
MAX_PAGES = 10
REQUEST_TIMEOUT_S = 30

logger = logging.getLogger(__name__)


def fetch_titles(
    query: str,
    pages: int = 1,
    api_key: str | None = None,
    cx: str | None = None,
) -> List[str]:
    """Fetch result titles from Google Custom Search."""
    api_key = api_key or os.getenv("GOOGLE_API_KEY")
    cx = cx or os.getenv("GOOGLE_CSE_ID")
    if not api_key or not cx:
        raise ValueError("API key e CX sao obrigatorios. Defina GOOGLE_API_KEY e GOOGLE_CSE_ID.")

    titles: List[str] = []
    seen = set()

    session = requests.Session()
    try:
        safe_pages = int(pages)
    except (TypeError, ValueError):
        safe_pages = 1
    safe_pages = max(1, min(safe_pages, MAX_PAGES))
    if safe_pages != pages:
        logger.debug("Ajustando pages de %s para %s", pages, safe_pages)
    for page_idx in range(safe_pages):
        start = page_idx * RESULTS_PER_PAGE + 1
        params = {
            "key": api_key,
            "cx": cx,
            "q": query,
            "hl": "pt",
            "gl": "br",
            "lr": "lang_pt",
            "num": RESULTS_PER_PAGE,
            "start": start,
            "safe": "active",
        }
        resp = session.get(GOOGLE_CSE_URL, params=params, timeout=REQUEST_TIMEOUT_S)
        if resp.status_code == 403:
            raise ValueError(
                "403 Forbidden. Verifique se a Custom Search API esta habilitada, "
                "se o billing esta ativo e se a chave nao tem restricao de referrer."
            )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        for item in items:
            title = (item.get("title") or "").strip()
            if title and title not in seen:
                titles.append(title)
                seen.add(title)

    return titles
