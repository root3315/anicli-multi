"""Нормализация названий тайтлов для группировки между источниками."""

import re

# Счётчик серий: [1-220 из 220], [1 из 1], (12 of 12)
_EPISODE_COUNT_RE = re.compile(
    r"[\[\(]\s*\d+\s*[-–—]?\s*\d*\s*(?:из|of)\s*\d+\s*[\]\)]",
    re.IGNORECASE,
)
_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)
_SPACE_RE = re.compile(r"\s+")

# Служебные хвосты со страниц поиска: «3 сезон, 10 серия», «Завершен (все серии)».
# Голые числа сюда намеренно не попадают — «Наруто 2» это часть названия.
_SERVICE_PATTERNS = [
    re.compile(r"\d+\s*-?\s*(?:й|ый|ой)?\s*сезон", re.IGNORECASE),
    re.compile(r"сезон\s*\d+", re.IGNORECASE),
    re.compile(r"\d+\s*сери[яйи]", re.IGNORECASE),
    re.compile(r"сери[яйи]\s*\d+", re.IGNORECASE),
    re.compile(r"\d+\s*эпизод", re.IGNORECASE),
    re.compile(r"эпизод\s*\d+", re.IGNORECASE),
    re.compile(r"[\(\[]\s*все\s+серии\s*[\)\]]", re.IGNORECASE),
    re.compile(r"\bзавершен[оаы]?\b", re.IGNORECASE),
    re.compile(r"\bонгоинг\b", re.IGNORECASE),
]
_ORPHAN_PUNCT_RE = re.compile(r"[\s,;:—–-]+$")
_LEADING_PUNCT_RE = re.compile(r"^[\s,;:—–-]+")


def strip_service_info(title: str) -> str:
    """Убрать служебные хвосты, оставив само название.

    «Жизнь по вызову 3 сезон, 10 серия» -> «Жизнь по вызову».
    Работает только по распознаваемым шаблонам: голые числа не трогаются.
    """
    text = title
    for pattern in _SERVICE_PATTERNS:
        text = pattern.sub(" ", text)
    text = _SPACE_RE.sub(" ", text)
    text = _ORPHAN_PUNCT_RE.sub("", text)
    text = _LEADING_PUNCT_RE.sub("", text)
    return text.strip() or title.strip()


def normalize_title(raw: str) -> str:
    """Привести название к ключу группировки.

    Разные написания одного тайтла должны давать одинаковый ключ, разные
    тайтлы — разный. При сомнении выбирается разделение, а не склейка.
    """
    text = strip_service_info(raw).lower().replace("ё", "е")
    # альтернативное название после "/" отбрасываем: "Наруто / Naruto" -> "Наруто"
    text = text.split("/")[0]
    text = _EPISODE_COUNT_RE.sub(" ", text)
    text = _PUNCT_RE.sub(" ", text)
    return _SPACE_RE.sub(" ", text).strip()
