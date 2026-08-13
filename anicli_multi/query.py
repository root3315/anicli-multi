"""Разбор поискового запроса: текст для источников плюс фильтр по типу контента.

Пользователь естественно пишет «жизнь по вызову сериал». Если отправить это в
источники как есть, hdrezka начинает искать буквальную фразу и отдаёт мусор, а
слово «сериал» рушит оценку релевантности. Вырезаем его и превращаем в фильтр.
"""

from dataclasses import dataclass
from typing import Optional

from .kinds import ANIME, CARTOON, MOVIE, SERIES, SHOW

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
    """
    tokens = raw.split()
    if len(tokens) < 2:
        return ParsedQuery(text=" ".join(tokens), kind=None, raw=raw)

    kind = KIND_WORDS.get(tokens[-1].lower())
    if kind is not None:
        return ParsedQuery(text=" ".join(tokens[:-1]), kind=kind, raw=raw)

    kind = KIND_WORDS.get(tokens[0].lower())
    if kind is not None:
        return ParsedQuery(text=" ".join(tokens[1:]), kind=kind, raw=raw)

    return ParsedQuery(text=" ".join(tokens), kind=None, raw=raw)
