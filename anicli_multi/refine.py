"""Доводка выдачи: отсечение нерелевантного, фильтр по типу, срез до лимита."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Optional

from .grouping import IRRELEVANT_RANK, TitleGroup, relevance_rank


@dataclass
class RefineResult:
    """Что показывать и что сказать пользователю под таблицей."""

    groups: list[TitleGroup] = field(default_factory=list)
    """Строки для показа — уже после отсечения, фильтра и среза."""
    total: int = 0
    """Сколько строк осталось после отсечения и фильтра, до среза."""
    hidden_irrelevant: int = 0
    """Сколько строк убрано как нерелевантные."""
    kind_filter_dropped: bool = False
    """Фильтр по типу не дал ничего и был мягко отменён."""


def refine(
    groups: Sequence[TitleGroup],
    query_key: str,
    kind: Optional[str],
    max_results: int,
) -> RefineResult:
    """Привести выдачу к тому, что стоит показывать.

    Порядок важен: сначала отсекаем нерелевантное, потом фильтруем по типу.
    Обратный порядок дал бы фильтру возможность вытащить наверх строки, которые
    к запросу отношения не имеют.
    """
    result = RefineResult()
    if not groups:
        return result

    relevant = [g for g in groups if relevance_rank(query_key, g.key[1]) < IRRELEVANT_RANK]
    if relevant:
        base = relevant
        result.hidden_irrelevant = len(groups) - len(relevant)
    else:
        # пустой экран хуже неточного
        base = list(groups)

    if kind is not None:
        matching = [g for g in base if g.kind == kind]
        if matching:
            base = matching
        else:
            result.kind_filter_dropped = True

    result.total = len(base)
    result.groups = base[:max_results] if max_results >= 1 else list(base)
    return result
