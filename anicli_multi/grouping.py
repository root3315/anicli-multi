"""Склейка результатов поиска разных источников в группы по одному тайтлу."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Callable

from rich.markup import escape

from .kinds import ANIME, resolve_kind
from .normalize import normalize_title

# (имя источника, объект результата поиска)
Entry = tuple[str, Any]
# (тип контента, нормализованное название)
GroupKey = tuple[str, str]
KindResolver = Callable[[str, str], str]


@dataclass
class TitleGroup:
    """Один тайтл одного типа, найденный на одном или нескольких источниках."""

    key: GroupKey
    title: str
    kind: str = ANIME
    entries: list[Entry] = field(default_factory=list)

    @property
    def sources(self) -> list[str]:
        return [source for source, _ in self.entries]

    def __str__(self) -> str:
        # render_table печатает str(result), а rich трактует [...] как разметку.
        # Название экранируем: в выдаче встречается «Наруто [OVA-8]».
        # Бейдж пишем как \[тип], чтобы rich вывел скобки буквально.
        badge = "" if self.kind == ANIME else f" \\[{self.kind}]"
        return f"{escape(self.title)}{badge} [dim]({', '.join(self.sources)})[/dim]"


def _priority_index(source: str, priority: Sequence[str]) -> int:
    """Позиция источника в приоритете; неизвестный источник уходит в конец."""
    try:
        return priority.index(source)
    except ValueError:
        return len(priority)


def relevance_rank(query_key: str, title_key: str) -> int:
    """Насколько название отвечает запросу. Меньше — релевантнее.

    Без этого ранга выдача сортируется числом источников, и по запросу
    «во все тяжкие» полсотни аниме, случайно совпавших по слову «во» и найденных
    на трёх источниках, обходят сам сериал, найденный на одном.
    """
    if not query_key:
        return 0
    if title_key == query_key:
        return 0
    if title_key.startswith(query_key):
        return 1
    if query_key in title_key:
        return 2
    return 3


def group_results(
    per_source: Sequence[tuple[str, Sequence[Any]]],
    priority: Sequence[str],
    kind_resolver: KindResolver = resolve_kind,
    query: str = "",
) -> list[TitleGroup]:
    """Сгруппировать результаты по паре (тип контента, нормализованное название).

    Склейка только по точному совпадению ключа — см. спеку §6.
    Тип входит в ключ намеренно: без него одноимённые аниме и игровой фильм
    склеились бы в одну строку.
    Внутри группы источники упорядочены по приоритету, отображаемое название
    берётся у источника с наивысшим приоритетом.
    """
    groups: dict[GroupKey, TitleGroup] = {}

    for source, results in per_source:
        for result in results:
            normalized = normalize_title(result.title)
            if not normalized:
                continue
            kind = kind_resolver(source, getattr(result, "url", "") or "")
            key: GroupKey = (kind, normalized)
            group = groups.get(key)
            if group is None:
                groups[key] = TitleGroup(key=key, title=result.title, kind=kind, entries=[(source, result)])
                continue
            # один источник на группу: дубли внутри источника отбрасываем
            if source in group.sources:
                continue
            group.entries.append((source, result))

    ordered: list[TitleGroup] = []
    for group in groups.values():
        group.entries.sort(key=lambda e: _priority_index(e[0], priority))
        _, best_result = group.entries[0]
        group.title = best_result.title.strip()
        ordered.append(group)

    query_key = normalize_title(query)
    ordered.sort(
        key=lambda g: (
            relevance_rank(query_key, g.key[1]),
            -len(g.entries),
            _priority_index(g.entries[0][0], priority),
            g.title.lower(),
        )
    )
    return ordered
