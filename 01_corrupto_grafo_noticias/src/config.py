from __future__ import annotations

"""Config and validation helpers for the project."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Validated settings for the pipeline."""

    project_id: str
    location: str
    engine_id: str
    credentials_path: str | None = None
    query: str = "corrupcao"
    pages: int = 1
    top: int = 30


def _get_required_env(name: str) -> str:
    """Return an env var or raise a clear error if missing."""
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} nao encontrado. Informe pela interface ou nas variaveis de ambiente.")
    return value


def normalize_settings(
    project_id: str | None,
    location: str | None,
    engine_id: str | None,
    credentials_path: str | None,
    query: str | None,
    pages: int | str | None,
    top: int | str | None,
) -> Settings:
    """Normalize and validate user input from CLI or UI."""
    project_value = (project_id or os.getenv("GOOGLE_CLOUD_PROJECT", "")).strip()
    location_value = (location or os.getenv("VERTEX_SEARCH_LOCATION", "")).strip()
    engine_value = (engine_id or os.getenv("VERTEX_SEARCH_ENGINE_ID", "")).strip()
    creds_value = (credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")).strip()

    if not project_value:
        project_value = _get_required_env("GOOGLE_CLOUD_PROJECT")
    if not location_value:
        location_value = "global"
    if not engine_value:
        engine_value = _get_required_env("VERTEX_SEARCH_ENGINE_ID")

    query_value = (query or "corrupcao").strip() or "corrupcao"
    pages_value = _parse_int(pages, default=1, min_value=1, max_value=10, name="pages")
    top_value = _parse_int(top, default=30, min_value=5, max_value=200, name="top")

    return Settings(
        project_id=project_value,
        location=location_value,
        engine_id=engine_value,
        credentials_path=creds_value or None,
        query=query_value,
        pages=pages_value,
        top=top_value,
    )


def _parse_int(value, default: int, min_value: int, max_value: int, name: str) -> int:
    """Parse ints safely and clamp to a min/max range."""
    if value is None or value == "":
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    if parsed < min_value:
        return min_value
    if parsed > max_value:
        return max_value
    return parsed
