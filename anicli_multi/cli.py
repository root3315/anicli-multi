"""Точка входа `ani`: настраивает APP из anicli-ru и делегирует ему разбор аргументов."""

import sys
from typing import Optional

from .compat import CompatError, assert_compat
from .config import MultiConfig, load_config

_SOURCES_FLAG = "--sources"

# Флаги upstream, не принимающие значения. Без этого списка `ani --ongoing наруто`
# проглотил бы «наруто» как значение --ongoing вместо поискового запроса.
_BOOLEAN_FLAGS = frozenset({"--ongoing", "--force", "--help", "--install-completion", "--show-completion"})


def split_own_args(argv: list[str]) -> tuple[Optional[str], list[str]]:
    """Вынуть наш собственный --sources из argv; остальное уходит upstream как есть."""
    sources: Optional[str] = None
    rest: list[str] = []
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == _SOURCES_FLAG and index + 1 < len(argv):
            sources = argv[index + 1]
            index += 2
            continue
        if arg.startswith(_SOURCES_FLAG + "="):
            sources = arg.split("=", 1)[1]
            index += 1
            continue
        rest.append(arg)
        index += 1
    return sources, rest


def build_upstream_argv(argv: list[str], primary: str) -> list[str]:
    """Собрать аргументы для `anicli-ru cli`.

    Позиционные слова склеиваются в один поисковый запрос и уходят в --search.
    Явный -s/--source пользователя имеет приоритет над источником по умолчанию.
    """
    flags: list[str] = []
    words: list[str] = []
    index = 0
    has_explicit_source = False

    while index < len(argv):
        arg = argv[index]
        if arg.startswith("-"):
            if arg in ("-s", "--source") or arg.startswith("--source="):
                has_explicit_source = True
            flags.append(arg)
            takes_value = arg not in _BOOLEAN_FLAGS and "=" not in arg
            # значение следующим токеном: пробрасываем, не считая его запросом
            if takes_value and index + 1 < len(argv) and not argv[index + 1].startswith("-"):
                flags.append(argv[index + 1])
                index += 2
                continue
            index += 1
            continue
        words.append(arg)
        index += 1

    result = ["cli"]
    if not has_explicit_source:
        result += ["-s", primary]
    result += flags
    if words:
        result += ["--search", " ".join(words)]
    return result


def main() -> None:
    try:
        assert_compat()
    except CompatError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc

    from anicli.cli.main import APP
    from anicli.main import app as upstream_app

    from .commands import build_extractors, install

    raw_sources, argv = split_own_args(sys.argv[1:])
    config: MultiConfig = load_config()
    if raw_sources:
        config.sources = [s.strip() for s in raw_sources.split(",") if s.strip()]

    install(APP, config)

    extractors = build_extractors(config.sources)
    APP.context._data["multi_extractors"] = extractors
    APP.context._data["multi_timeout"] = config.timeout

    primary = config.sources[0] if config.sources else "animego"
    upstream_app(args=build_upstream_argv(argv, primary), prog_name="ani")
