"""FSM мультипоиска: свой выбор тайтла и источника, дальше — штатные шаги anicli-ru."""

from collections.abc import Sequence
from typing import Any, Optional, TypedDict, Union

from anicli.cli.fsm import BaseAnimeFSM
from anicli.cli.helpers.render import render_table
from anicli.cli.helpers.validator import validate_prompt_index
from anicli.cli.ptk_lib import fsm_route, fsm_state
from rich import get_console

from .grouping import TitleGroup

CONSOLE = get_console()


class MultiContext(TypedDict, total=False):
    """Контекст FSM мультипоиска.

    Объявлен самостоятельно, а не наследованием от anicli.cli.contexts.Context:
    anicli-ru не поставляет py.typed, поэтому для mypy его Context — это Any,
    и наследование не дало бы никакой проверки типов. Здесь перечислено всё,
    что мы читаем и пишем; соответствие контракту upstream проверяет compat.py.
    """

    # наши поля
    query: str
    groups: list[TitleGroup]
    group_entries: list[tuple[str, Any]]
    # контракт anicli-ru, который заполняем мы
    extractor_name: str
    results: list[Any]
    result_num: int
    anime: Any
    episodes: Sequence[Any]
    # контракт anicli-ru, который приходит из команды
    default_quality: int
    mpv_opts: str
    m3u_size: int


class SourceRow:
    """Строка таблицы выбора источника. render_table печатает str(элемент)."""

    __slots__ = ("name",)

    def __init__(self, name: str):
        self.name = name

    def __str__(self) -> str:
        return self.name


def resolve_entry(group: TitleGroup) -> Optional[tuple[str, Any]]:
    """Вернуть единственную пару (источник, результат) или None, если выбор неоднозначен."""
    if len(group.entries) == 1:
        return group.entries[0]
    return None


# Навигация есть в anicli-ru (BaseFSM.NAVIGATION_COMMANDS), но нигде не показана
# пользователю: после просмотра серии он оказывается перед голым промптом и не знает,
# как выйти. Показываем подсказку в трёх местах — под таблицей серий, после
# воспроизведения и в тексте ошибки ввода.
NAV_HINT = "«..» назад · «~» в главное меню"

MAX_PROMPT_TITLE = 40


def shorten_title(title: str, limit: int = MAX_PROMPT_TITLE) -> str:
    """Укоротить название для промпта.

    Длинные названия («Я перевоплотился в седьмого принца, так что…») разносят
    промпт на несколько строк и делают ввод нечитаемым.
    """
    title = title.strip()
    if len(title) <= limit:
        return title
    return title[: limit - 1].rstrip() + "…"


@fsm_route("multi")
class MultiSearchFSM(BaseAnimeFSM[MultiContext]):
    ROUTE_NAME = "multi"

    def _get_user_dynamic_validator(self, state_name: str, user_input: str) -> Union[bool, str]:
        if state_name == "step_1":
            result: Union[bool, str] = validate_prompt_index(self.ctx.get("groups", []), user_input)
        elif state_name == "step_1_source":
            result = validate_prompt_index(self.ctx.get("group_entries", []), user_input)
        else:
            result = super()._get_user_dynamic_validator(state_name, user_input)
        # текст ошибки — единственная обратная связь, которую пользователь гарантированно
        # увидит, застряв на шаге; дописываем к нему способ выйти
        if isinstance(result, str):
            return f"{result} · {NAV_HINT}"
        return result

    def _get_user_dynamic_completions(
        self, state_name: str, current_text: str
    ) -> Union[list[str], list[tuple[str, str]]]:
        if state_name == "step_1":
            groups: Sequence[TitleGroup] = self.ctx.get("groups", [])
            return [(str(i), g.title) for i, g in enumerate(groups, 1)]
        if state_name == "step_1_source":
            entries = self.ctx.get("group_entries", [])
            return [(str(i), source) for i, (source, _) in enumerate(entries, 1)]
        return super()._get_user_dynamic_completions(state_name, current_text)

    @fsm_state("step_1", prompt_message="~/{ROUTE_NAME} ")
    async def step_1(self, user_input: str):
        """Выбран тайтл. Один источник — идём дальше, несколько — спрашиваем источник."""
        groups: list[TitleGroup] = self.ctx["groups"]
        group = groups[int(user_input) - 1]

        entry = resolve_entry(group)
        if entry is not None:
            await self._open_anime(*entry)
            return

        self.ctx["group_entries"] = group.entries
        render_table(group.title, [SourceRow(source) for source, _ in group.entries])
        await self.next_state("step_1_source")

    @fsm_state("step_1_source", prompt_message="~/{ROUTE_NAME}/source ")
    async def step_1_source(self, user_input: str):
        """Выбран источник для тайтла, найденного на нескольких сайтах."""
        entries: list[tuple[str, Any]] = self.ctx["group_entries"]
        source, result = entries[int(user_input) - 1]
        await self._open_anime(source, result)

    async def _open_anime(self, source: str, result: Any) -> None:
        """Подготовить контекст под наследуемый step_2 и перейти в него.

        extractor_name проставляется здесь, после выбора источника — благодаря
        этому история просмотров пишется с корректным источником (спека §5).
        """
        self.ctx["extractor_name"] = source
        self.ctx["results"] = [result]
        self.ctx["result_num"] = 0

        anime = await result.a_get_anime()
        episodes = await anime.a_get_episodes()
        self.ctx["anime"] = anime
        self.ctx["episodes"] = episodes

        self.set_prompt_var("result", shorten_title(anime.title))
        render_table(anime.title, episodes)
        CONSOLE.print(f"[dim]{NAV_HINT}[/dim]")
        await self.next_state("step_2")

    # Ниже — тонкие делегаты к наследуемым шагам. Своей логики не добавляют,
    # только печатают подсказку после возврата из плеера: в этот момент upstream
    # ничего не выводит, и пользователь остаётся перед голым промптом.
    @fsm_state("step_3", prompt_message="~/{ROUTE_NAME}/{result}/episode/{episode} ")
    async def step_3(self, user_input: str):
        await BaseAnimeFSM.step_3.handler(self, user_input)
        CONSOLE.print(f"[dim]{NAV_HINT}[/dim]")

    @fsm_state("step_3_batched", prompt_message="~/{ROUTE_NAME}/{result}/episode/{episode} ")
    async def step_3_batched(self, user_input: str):
        await BaseAnimeFSM.step_3_batched.handler(self, user_input)
        CONSOLE.print(f"[dim]{NAV_HINT}[/dim]")
