"""Разбор поискового запроса: текст для источников плюс фильтр по типу контента.

Пользователь естественно пишет «жизнь по вызову сериал». Если отправить это в
источники как есть, hdrezka начинает искать буквальную фразу и отдаёт мусор, а
слово «сериал» рушит оценку релевантности. Вырезаем его и превращаем в фильтр.
"""

import re
from dataclasses import dataclass
from typing import Optional

from .kinds import ANIME, CARTOON, MOVIE, SERIES, SHOW

# Уточнения, которые пользователь дописывает к названию. Они не встречаются в
# названиях тайтлов, зато портят и оценку релевантности, и выдачу самих источников:
# animego на «Re zero 1 сезон» отдал 50 результатов вместо 27 на «Re zero».
#
# «сезон» и «серия» вырезаются только рядом с числом — иначе «Сезон охоты»
# превратился бы в «охоты».
_QUALIFIER_PATTERNS = [
    re.compile(r"\b\d+\s*-?\s*(?:й|ый|ой)?\s*сезон\b", re.IGNORECASE),
    re.compile(r"\bсезон\s*\d+\b", re.IGNORECASE),
    re.compile(r"\b\d+\s*сери[яйи]\b", re.IGNORECASE),
    re.compile(r"\bсери[яйи]\s*\d+\b", re.IGNORECASE),
    re.compile(r"\b\d+\s*эпизод\b", re.IGNORECASE),
    re.compile(r"\bэпизод\s*\d+\b", re.IGNORECASE),
    re.compile(r"\b(?:смотреть|онлайн|бесплатно|hd)\b", re.IGNORECASE),
]
_SPACE_RE = re.compile(r"\s+")


def strip_qualifiers(text: str) -> str:
    """Убрать служебные уточнения. Пустой результат откатывается к исходнику."""
    cleaned = text
    for pattern in _QUALIFIER_PATTERNS:
        cleaned = pattern.sub(" ", cleaned)
    cleaned = _SPACE_RE.sub(" ", cleaned).strip()
    return cleaned or text.strip()

KIND_WORDS: dict[str, str] = {
    "сериал": SERIES,
    "сериалы": SERIES,
    "сериала": SERIES,
    "фильм": MOVIE,
    "фильмы": MOVIE,
    "фильма": MOVIE,
    "кино": MOVIE,
    "аниме": ANIME,
    "мультфильм": CARTOON,
    "мультфильмы": CARTOON,
    "мультик": CARTOON,
    "мультики": CARTOON,
    "мультсериал": CARTOON,
    "шоу": SHOW,
}


@dataclass(frozen=True)
class ParsedQuery:
    """Результат разбора ввода пользователя."""

    text: str
    """Что отправлять источникам."""
    kind: Optional[str]
    """Фильтр по типу контента или None."""
    raw: str
    """Исходный ввод — для заголовка таблицы."""


def parse_query(raw: str) -> ParsedQuery:
    """Вырезать слово типа, если оно стоит первым или последним.

    Слово в середине не трогаем: там оно почти наверняка часть названия.
    Единственное слово тоже не трогаем — «аниме» это запрос, а не фильтр.

    Уточнения вроде «1 сезон» убираются до разбора типа, чтобы «жизнь по вызову
    сериал 1 сезон» дало текст «жизнь по вызову» и фильтр «сериал».
    """
    tokens = strip_qualifiers(raw).split()
    if len(tokens) < 2:
        return ParsedQuery(text=" ".join(tokens), kind=None, raw=raw)

    kind = KIND_WORDS.get(tokens[-1].lower())
    if kind is not None:
        return ParsedQuery(text=" ".join(tokens[:-1]), kind=kind, raw=raw)

    kind = KIND_WORDS.get(tokens[0].lower())
    if kind is not None:
        return ParsedQuery(text=" ".join(tokens[1:]), kind=kind, raw=raw)

    return ParsedQuery(text=" ".join(tokens), kind=None, raw=raw)
