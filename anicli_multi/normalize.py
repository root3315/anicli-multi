"""Нормализация названий тайтлов для группировки между источниками."""

import re

# Счётчик серий: [1-220 из 220], [1 из 1], (12 of 12)
_EPISODE_COUNT_RE = re.compile(
    r"[\[\(]\s*\d+\s*[-–—]?\s*\d*\s*(?:из|of)\s*\d+\s*[\]\)]",
    re.IGNORECASE,
)
_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)
_SPACE_RE = re.compile(r"\s+")


def normalize_title(raw: str) -> str:
    """Привести название к ключу группировки.

    Разные написания одного тайтла должны давать одинаковый ключ, разные
    тайтлы — разный. При сомнении выбирается разделение, а не склейка.
    """
    text = raw.lower().replace("ё", "е")
    # альтернативное название после "/" отбрасываем: "Наруто / Naruto" -> "Наруто"
    text = text.split("/")[0]
    text = _EPISODE_COUNT_RE.sub(" ", text)
    text = _PUNCT_RE.sub(" ", text)
    return _SPACE_RE.sub(" ", text).strip()
