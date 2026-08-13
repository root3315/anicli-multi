"""Склейка результатов поиска разных источников в группы по одному тайтлу."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence, Tuple

from .normalize import normalize_title

# (имя источника, объект результата поиска)
Entry = Tuple[str, Any]


@dataclass
class TitleGroup:
    """Один тайтл, найденный на одном или нескольких источниках."""

    key: str
    title: str
    entries: List[Entry] = field(default_factory=list)

    @property
    def sources(self) -> List[str]:
        return [source for source, _ in self.entries]

    def __str__(self) -> str:
        # render_table из anicli-ru печатает str(result); rich-разметка тут допустима
        return f"{self.title} [dim]({', '.join(self.sources)})[/dim]"


def _priority_index(source: str, priority: Sequence[str]) -> int:
    """Позиция источника в приоритете; неизвестный источник уходит в конец."""
    try:
        return priority.index(source)
    except ValueError:
        return len(priority)


def group_results(
    per_source: Sequence[Tuple[str, Sequence[Any]]],
    priority: Sequence[str],
) -> List[TitleGroup]:
    """Сгруппировать результаты по нормализованному названию.

    Склейка только по точному совпадению ключа — см. спеку §6.
    Внутри группы источники упорядочены по приоритету, отображаемое название
    берётся у источника с наивысшим приоритетом.
    """
    groups: Dict[str, TitleGroup] = {}

    for source, results in per_source:
        for result in results:
            key = normalize_title(result.title)
            if not key:
                continue
            group = groups.get(key)
            if group is None:
                groups[key] = TitleGroup(key=key, title=result.title, entries=[(source, result)])
                continue
            # один источник на группу: дубли внутри источника отбрасываем
            if source in group.sources:
                continue
            group.entries.append((source, result))

    ordered: List[TitleGroup] = []
    for group in groups.values():
        group.entries.sort(key=lambda e: _priority_index(e[0], priority))
        _, best_result = group.entries[0]
        group.title = best_result.title.strip()
        ordered.append(group)

    ordered.sort(
        key=lambda g: (
            -len(g.entries),
            _priority_index(g.entries[0][0], priority),
            g.title.lower(),
        )
    )
    return ordered
