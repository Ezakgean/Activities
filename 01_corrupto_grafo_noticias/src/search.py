from __future__ import annotations

"""Vertex AI Search (Discovery Engine) client."""

import logging
from typing import List

import google.auth
from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine_v1 as discoveryengine
from google.protobuf.json_format import MessageToDict

logger = logging.getLogger(__name__)

RESULTS_PER_PAGE = 10
MAX_PAGES = 10
DEFAULT_SERVING_CONFIG = "default_config"


def fetch_titles(
    query: str,
    pages: int,
    project_id: str,
    location: str,
    engine_id: str,
    credentials_path: str | None = None,
) -> List[str]:
    """Fetch result titles from Vertex AI Search."""
    credentials = None
    if credentials_path:
        credentials, _ = google.auth.load_credentials_from_file(credentials_path)

    client_options = (
        ClientOptions(api_endpoint=f"{location}-discoveryengine.googleapis.com")
        if location != "global"
        else None
    )
    client = discoveryengine.SearchServiceClient(credentials=credentials, client_options=client_options)
    serving_config = (
        f"projects/{project_id}/locations/{location}/collections/default_collection/"
        f"engines/{engine_id}/servingConfigs/{DEFAULT_SERVING_CONFIG}"
    )

    titles: List[str] = []
    seen = set()

    safe_pages = _clamp_pages(pages)
    page_token = ""
    for _ in range(safe_pages):
        request = discoveryengine.SearchRequest(
            serving_config=serving_config,
            query=query,
            page_size=RESULTS_PER_PAGE,
            page_token=page_token,
        )
        response = client.search(request=request)
        for result in response.results:
            title = _extract_title(result)
            if title and title not in seen:
                titles.append(title)
                seen.add(title)
        page_token = response.next_page_token
        if not page_token:
            break

    return titles


def _clamp_pages(pages: int | str | None) -> int:
    try:
        value = int(pages)
    except (TypeError, ValueError):
        value = 1
    return max(1, min(value, MAX_PAGES))


def _extract_title(result: discoveryengine.SearchResponse.SearchResult) -> str:
    doc = result.document
    if not doc:
        return ""
    if getattr(doc, "title", ""):
        return str(doc.title).strip()

    for struct in (doc.derived_struct_data, doc.struct_data):
        if struct:
            data = MessageToDict(struct)
            for key in ("title", "name", "documentTitle"):
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()

    return ""
