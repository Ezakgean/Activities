from __future__ import annotations

"""Text normalization helpers for Portuguese tokens."""

import re
import unicodedata
from typing import Iterable, List


STOPWORDS_PT = {
    "a", "o", "os", "as", "um", "uma", "uns", "umas",
    "de", "da", "do", "das", "dos", "em", "no", "na", "nos", "nas",
    "por", "para", "com", "sem", "sob", "sobre", "entre", "ate",
    "e", "ou", "mas", "que", "se", "ao", "aos", "aquela", "aquele",
    "aquelas", "aqueles", "esta", "este", "estas", "estes", "isso", "isto",
    "ha", "tem", "tinha", "ser", "sao", "foi", "foram", "era", "eram",
    "mais", "menos", "muito", "pouco", "tambem", "ja", "nao", "sim",
    "como", "quando", "onde", "porque", "por que", "porquê", "por que",
    "sua", "seu", "suas", "seus", "meu", "minha", "meus", "minhas",
    "dele", "dela", "deles", "delas", "lhe", "lhes", "nosso", "nossa",
    "nossos", "nossas", "cada", "outro", "outra", "outros", "outras",
}


def _strip_accents(text: str) -> str:
    """Remove accents from text."""
    return (
        unicodedata.normalize("NFKD", text)
        .encode("ascii", "ignore")
        .decode("ascii")
    )


def normalize(text: str) -> str:
    """Lowercase and remove accents."""
    text = text.lower()
    text = _strip_accents(text)
    return text


def tokenize(text: str) -> List[str]:
    """Tokenize text into alphanumeric tokens."""
    text = normalize(text)
    tokens = re.findall(r"[a-z0-9]+", text)
    return tokens


def filter_tokens(tokens: Iterable[str], min_len: int = 3) -> List[str]:
    """Filter tokens by length and Portuguese stopwords."""
    out = []
    for t in tokens:
        if len(t) < min_len:
            continue
        if t in STOPWORDS_PT:
            continue
        out.append(t)
    return out
