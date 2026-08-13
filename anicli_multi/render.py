"""Таблица результатов без скрытых строк.

render_table из anicli-ru при длинной выдаче рисует первые строки, затем
«+N more», затем последние. Скрытые строки при этом остаются выбираемыми по
номеру: можно ввести 45 и попасть в то, чего не было на экране. Здесь строк
ровно столько, сколько показано, и нумерация совпадает один в один.
"""

from collections.abc import Sequence

from rich import box, get_console
from rich.table import Table

from .grouping import TitleGroup
from .refine import RefineResult

CONSOLE = get_console()


def render_groups(title: str, groups: Sequence[TitleGroup]) -> None:
    """Напечатать таблицу результатов."""
    table = Table(box=box.ROUNDED, title=title, title_justify="left", show_header=False)
    for index, group in enumerate(groups, 1):
        table.add_row(str(index), str(group))
    CONSOLE.print(table)


def summary_line(result: RefineResult) -> str:
    """Одна строка со сводкой под таблицей. Пустая, если сказать нечего."""
    parts: list[str] = []
    if result.total > len(result.groups):
        parts.append(f"показано {len(result.groups)} из {result.total} — уточните запрос")
    if result.hidden_irrelevant:
        parts.append(f"скрыто {result.hidden_irrelevant} нерелевантных")
    if result.kind_filter_dropped:
        parts.append("под указанный тип ничего не нашлось, показываю всё")
    return " · ".join(parts)
