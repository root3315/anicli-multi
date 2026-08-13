"""Команды поверх APP из anicli-ru: мультипоиск, алиасы, голый текст как запрос."""

from collections.abc import Sequence
from typing import Any, Optional

from anicli.cli.helpers.render import render_table
from anicli.cli.ptk_lib import command
from anicli.common.extractors import dynamic_load_extractor_module
from rich import get_console

from .aggregate import SourceFailure, search_all
from .config import MultiConfig
from .fsm import MultiSearchFSM
from .grouping import group_results

CONSOLE = get_console()


def build_extractors(
    sources: Sequence[str],
    *,
    proxy: Optional[str] = None,
    headers: Optional[dict] = None,
    cookies: Optional[Any] = None,
    timeout: Optional[float] = None,
) -> dict[str, Any]:
    """Создать по экземпляру Extractor на источник с общим HTTP-клиентом.

    Клиент создаётся здесь намеренно, а не берётся по умолчанию: в anicli-api
    BaseExtractor.__init__ объявлен как `def __init__(self, http_client=HTTPSync(),
    http_async_client=HTTPAsync())` — изменяемые значения по умолчанию, вычисляемые
    один раз при импорте. Все экземпляры делили бы один клиент, и настройка прокси,
    которую upstream применяет только к своему экстрактору, до наших не дошла бы.

    Неизвестные источники пропускаются.
    """
    from anicli_api._http import HTTPAsync, HTTPSync

    if proxy:
        http = HTTPSync(proxy=proxy, headers=headers or {}, cookies=cookies or {}, timeout=timeout)
        http_async = HTTPAsync(proxy=proxy, headers=headers or {}, cookies=cookies or {}, timeout=timeout)
    else:
        http = HTTPSync()
        http_async = HTTPAsync()
        for client in (http, http_async):
            if headers:
                client.headers.update(headers)
            if cookies:
                client.cookies.update(cookies)
            if timeout is not None:
                client.timeout = timeout

    extractors: dict[str, Any] = {}
    for name in sources:
        try:
            module = dynamic_load_extractor_module(name)
        except (NameError, ImportError):
            CONSOLE.print(f"[yellow]Источник {name} недоступен, пропущен[/yellow]")
            continue
        extractor = module.Extractor()
        extractor.http = http
        extractor.http_async = http_async
        extractors[name] = extractor
    return extractors


async def on_start_build_extractors(ctx: Any) -> None:
    """Стартовое событие: собрать экстракторы уже после применения настроек CLI.

    Регистрируется в on_startup_events APP и выполняется, когда прокси, заголовки
    и куки из аргументов командной строки уже лежат в контексте.
    """
    sources = ctx.data.get("multi_sources") or []
    ctx.data["multi_extractors"] = build_extractors(
        sources,
        proxy=ctx.data.get("proxy"),
        headers=ctx.data.get("headers"),
        cookies=ctx.data.get("cookies"),
        timeout=ctx.data.get("timeout"),
    )


def _print_failures(failures: Sequence[SourceFailure]) -> None:
    for failure in failures:
        CONSOLE.print(f"[yellow]⚠ {failure.source}: {failure.reason}[/yellow]")


@command("search", help="поиск по нескольким источникам сразу")
async def multi_search_command(query: str, ctx: Any):
    query = query.strip()
    if not query:
        CONSOLE.print("[yellow]Нужен запрос: просто наберите название[/yellow]")
        return

    extractors: dict[str, Any] = ctx.data.get("multi_extractors") or {}
    timeout: float = ctx.data.get("multi_timeout", 10.0)
    if not extractors:
        CONSOLE.print("[red]Ни один источник не доступен[/red]")
        return

    with CONSOLE.status(f"Ищу «{query}» на {len(extractors)} источниках…"):
        per_source, failures = await search_all(extractors, query, timeout=timeout)

    groups = group_results(per_source, priority=list(extractors))
    if not groups:
        CONSOLE.print("Ничего не найдено")
        _print_failures(failures)
        return

    render_table(f"Результаты: {query}", groups)
    _print_failures(failures)

    await ctx.app.start_fsm(
        "multi",
        "step_1",
        context={
            "query": query,
            "groups": groups,
            "extractor_name": groups[0].entries[0][0],
            "default_quality": ctx.data.get("quality", 2060),
            "mpv_opts": ctx.data.get("mpv_opts", ""),
            "m3u_size": ctx.data.get("m3u_size", 6),
        },
    )


def _make_alias(alias: str, target: str, help_text: str):
    @command(alias, help=help_text)
    async def _delegate(args: str, ctx: Any):
        await ctx.app.command_manager.execute(target, args)

    return _delegate


def install_bare_text_search(app: Any) -> None:
    """Неизвестная команда трактуется как поисковый запрос.

    Оборачивается публичный CommandManager.execute; Application._handle_global_input
    вызывает его через self.command_manager, поэтому подмена атрибута экземпляра
    перехватывает весь ввод главного меню.
    """
    manager = app.command_manager
    original_execute = manager.execute

    async def execute(cmd_key: str, raw_args: str) -> None:
        if manager.get_command(cmd_key) is None:
            query = f"{cmd_key} {raw_args}".strip()
            await original_execute("search", query)
            return
        await original_execute(cmd_key, raw_args)

    manager.execute = execute


def install(app: Any, config: MultiConfig) -> None:
    """Зарегистрировать всё на APP из anicli-ru. Идемпотентна."""
    # переопределяет штатный search: register перезаписывает маршрут по тому же ключу
    app.command_manager.register(multi_search_command)
    app.fsm_manager.register(MultiSearchFSM)

    # Алиасы — отдельные команды-делегаты, а не поле aliases= на маршруте.
    # register() бросает ValueError, если alias уже занят, поэтому повторный
    # вызов install() ронял бы приложение. Делегаты идемпотентны за счёт проверки.
    aliases: list[tuple[str, str, str]] = [
        ("s", "search", "то же, что search"),
        ("o", "ongoing", "то же, что ongoing"),
        ("h", "history", "то же, что history"),
        ("q", "exit", "то же, что exit"),
    ]
    for alias, target, help_text in aliases:
        if app.command_manager.get_command(alias) is None:
            app.command_manager.register(_make_alias(alias, target, help_text))

    app.context._data["multi_sources"] = list(config.sources)
    app.context._data["multi_timeout"] = config.timeout

    # экстракторы строятся стартовым событием: на этот момент прокси и заголовки
    # из аргументов CLI уже применены к контексту
    if on_start_build_extractors not in app.on_startup_events:
        app.on_startup_events.append(on_start_build_extractors)

    if config.bare_text_search:
        install_bare_text_search(app)
