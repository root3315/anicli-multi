"""Проверка, что установленный anicli-ru предоставляет нужный нам контракт.

Мы наследуемся от внутреннего FSM anicli-ru и опираемся на набор ключей его
контекста. Это единственная существенная связанность проекта (спека §5).
Здесь она проверяется явно, чтобы после обновления upstream пользователь получил
внятное сообщение вместо трейсбэка.
"""

REQUIRED_CONTEXT_KEYS: tuple[str, ...] = (
    "results",
    "result_num",
    "anime",
    "episodes",
    "extractor_name",
    "default_quality",
    "mpv_opts",
    "m3u_size",
)

_REQUIRED_FSM_METHODS = ("next_state", "go_back", "set_prompt_var")
_REQUIRED_FSM_STATES = ("step_1", "step_2", "step_3", "step_3_batched")
# состояния, обработчик которых мы вызываем напрямую из своих делегатов
_DELEGATED_FSM_STATES = ("step_3", "step_3_batched")


class CompatError(RuntimeError):
    """Установленная версия anicli-ru несовместима с anicli-multi."""


def check_compat() -> list[str]:
    """Вернуть список проблем совместимости. Пустой список — всё в порядке."""
    problems: list[str] = []

    try:
        from anicli.cli.contexts import Context
        from anicli.cli.fsm import BaseAnimeFSM
        from anicli.cli.main import APP
        from anicli.cli.ptk_lib import command, fsm_route, fsm_state  # noqa: F401
    except ImportError as exc:
        return [f"не удалось импортировать anicli-ru: {exc}"]

    declared = set(getattr(Context, "__annotations__", {}))
    missing_keys = [key for key in REQUIRED_CONTEXT_KEYS if key not in declared]
    if missing_keys:
        problems.append("в контексте FSM нет ключей: " + ", ".join(missing_keys))

    for method in _REQUIRED_FSM_METHODS:
        if not callable(getattr(BaseAnimeFSM, method, None)):
            problems.append(f"у BaseAnimeFSM нет метода {method}()")

    for state in _REQUIRED_FSM_STATES:
        state_obj = getattr(BaseAnimeFSM, state, None)
        if state_obj is None:
            problems.append(f"у BaseAnimeFSM нет состояния {state}")
        elif state in _DELEGATED_FSM_STATES and not callable(getattr(state_obj, "handler", None)):
            # мы вызываем обработчик напрямую, чтобы дописать подсказку после плеера
            problems.append(f"у состояния {state} нет вызываемого handler")

    manager = getattr(APP, "command_manager", None)
    if manager is None:
        problems.append("у APP нет command_manager")
    else:
        for method in ("register", "get_command", "execute"):
            if not callable(getattr(manager, method, None)):
                problems.append(f"у command_manager нет метода {method}()")

    if not callable(getattr(APP, "start_fsm", None)):
        problems.append("у APP нет метода start_fsm()")
    if getattr(APP, "fsm_manager", None) is None:
        problems.append("у APP нет fsm_manager")

    return problems


def check_hdrezka_override() -> list[str]:
    """Проверить, что расширенный поиск hdrezka можно подключить.

    Мы опираемся на приватный PageSearch._split_doc и CSS-класс вёрстки сайта.
    Если контракт изменился, hdrezka работает штатным экстрактором в аниме-режиме.
    """
    try:
        from anicli_api._http import ANUBIS_BYPASS_HEADERS  # noqa: F401
        from anicli_api.source import hdrezka
        from anicli_api.source.parsers.hdrezka_parser import PageSearch
    except ImportError as exc:
        return [f"не удалось импортировать hdrezka из anicli-api: {exc}"]

    problems: list[str] = []
    if not callable(getattr(PageSearch, "_split_doc", None)):
        problems.append("у PageSearch нет метода _split_doc")
    for name in ("Search", "Extractor"):
        if getattr(hdrezka, name, None) is None:
            problems.append(f"в anicli_api.source.hdrezka нет {name}")
    return problems


def assert_compat() -> None:
    """Бросить CompatError, если контракт anicli-ru изменился."""
    problems = check_compat()
    if not problems:
        return
    try:
        import anicli

        version = getattr(anicli, "__version__", "неизвестно")
    except ImportError:
        version = "не установлен"
    msg = (
        f"anicli-multi несовместим с установленной версией anicli-ru ({version}).\n"
        + "\n".join(f"  - {p}" for p in problems)
        + "\nПереустановите совместимую версию: pip install 'anicli-ru>=6.1,<7'"
    )
    raise CompatError(msg)
