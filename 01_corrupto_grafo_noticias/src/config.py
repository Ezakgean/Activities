from __future__ import annotations

"""Config and validation helpers for the project."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Validated settings for the pipeline."""

    api_key: str
    cx: str
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
    api_key: str | None,
    cx: str | None,
    query: str | None,
    pages: int | str | None,
    top: int | str | None,
) -> Settings:
    """Normalize and validate user input from CLI or UI."""
    api_key_value = (api_key or os.getenv("GOOGLE_API_KEY", "")).strip()
    cx_value = (cx or os.getenv("GOOGLE_CSE_ID", "")).strip()

    if not api_key_value:
        api_key_value = _get_required_env("GOOGLE_API_KEY")
    if not cx_value:
        cx_value = _get_required_env("GOOGLE_CSE_ID")

    query_value = (query or "corrupcao").strip() or "corrupcao"
    pages_value = _parse_int(pages, default=1, min_value=1, max_value=10, name="pages")
    top_value = _parse_int(top, default=30, min_value=5, max_value=200, name="top")

    return Settings(
        api_key=api_key_value,
        cx=cx_value,
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
