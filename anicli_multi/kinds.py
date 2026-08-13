"""Тип контента: аниме, фильм, сериал, мультфильм, шоу."""

from urllib.parse import urlsplit

ANIME = "аниме"
MOVIE = "фильм"
SERIES = "сериал"
CARTOON = "мультфильм"
SHOW = "шоу"

# Первый сегмент пути в URL hdrezka -> отображаемый тип
CATEGORY_TO_KIND: dict[str, str] = {
    "animation": ANIME,
    "films": MOVIE,
    "series": SERIES,
    "cartoons": CARTOON,
    "show": SHOW,
}
KNOWN_CATEGORIES = frozenset(CATEGORY_TO_KIND)

# Источники, у которых тип определяется по URL. Для остальных тип всегда «аниме»:
# у аниме-сайтов свои схемы путей (/anime/, /release/), и случайное совпадение
# сегмента с «films» дало бы ложный тип.
CATEGORY_SOURCES = frozenset({"hdrezka"})


def category_from_url(url: str) -> str:
    """Первый сегмент пути. Пустая строка, если разобрать нечего."""
    try:
        path = urlsplit(url).path
    except ValueError:
        return ""
    parts = [part for part in path.split("/") if part]
    return parts[0] if parts else ""


def resolve_kind(source: str, url: str) -> str:
    """Тип контента для результата поиска."""
    if source not in CATEGORY_SOURCES:
        return ANIME
    return CATEGORY_TO_KIND.get(category_from_url(url), ANIME)
