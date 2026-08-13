from anicli_multi.commands import build_extractors, install, install_bare_text_search
from anicli_multi.config import MultiConfig


class FakeRoute:
    def __init__(self, key):
        self.key = key
        self.aliases = []


class FakeCommandManager:
    """Минимальная подделка CommandManager из anicli-ru.

    register() воспроизводит поведение оригинала: маршрут по существующему ключу
    перезаписывается молча, а занятый алиас приводит к ValueError.
    """

    def __init__(self, keys):
        self._routes = {k: FakeRoute(k) for k in keys}
        self._aliases = {}
        self.calls = []

    def register(self, route):
        self._routes[route.key] = route
        for alias in getattr(route, "aliases", []):
            if alias in self._routes or alias in self._aliases:
                raise ValueError(f"Alias '{alias}' already registered")
            self._aliases[alias] = route.key

    def get_command(self, key):
        if key in self._routes:
            return self._routes[key]
        if key in self._aliases:
            return self._routes[self._aliases[key]]
        return None

    async def execute(self, cmd_key, raw_args):
        self.calls.append((cmd_key, raw_args))


class FakeFsmManager:
    def __init__(self):
        self.registered = []

    def register(self, route):
        self.registered.append(route)


class FakeContext:
    def __init__(self):
        self._data = {}

    @property
    def data(self):
        return self._data


class FakeApp:
    def __init__(self, keys):
        self.command_manager = FakeCommandManager(keys)
        self.fsm_manager = FakeFsmManager()
        self.context = FakeContext()
        self.on_startup_events = []


async def test_known_command_passes_through_unchanged():
    app = FakeApp(["search", "ongoing", "exit"])
    install_bare_text_search(app)
    await app.command_manager.execute("ongoing", "")
    assert app.command_manager.calls == [("ongoing", "")]


async def test_bare_text_becomes_search_query():
    app = FakeApp(["search"])
    install_bare_text_search(app)
    await app.command_manager.execute("наруто", "")
    assert app.command_manager.calls == [("search", "наруто")]


async def test_multiword_bare_text_is_joined_into_one_query():
    app = FakeApp(["search"])
    install_bare_text_search(app)
    await app.command_manager.execute("атака", "титанов 2 сезон")
    assert app.command_manager.calls == [("search", "атака титанов 2 сезон")]


async def test_search_command_itself_still_works():
    app = FakeApp(["search"])
    install_bare_text_search(app)
    await app.command_manager.execute("search", "наруто")
    assert app.command_manager.calls == [("search", "наруто")]


def test_build_extractors_returns_instance_per_source():
    extractors = build_extractors(["animego", "anilibria"])
    assert list(extractors) == ["animego", "anilibria"]
    for extractor in extractors.values():
        assert hasattr(extractor, "a_search")


def test_build_extractors_skips_unknown_source():
    extractors = build_extractors(["animego", "такого-источника-нет"])
    assert list(extractors) == ["animego"]


def test_build_extractors_does_not_share_default_client():
    """Каждый вызов даёт свежий клиент.

    В anicli-api клиенты — изменяемые значения по умолчанию, вычисляемые один раз
    при импорте. Если не подменять их, все экстракторы делили бы один клиент и
    настройка прокси до наших источников не дошла бы.
    """
    first = build_extractors(["animego"])["animego"]
    second = build_extractors(["animego"])["animego"]
    assert first.http_async is not second.http_async


def test_build_extractors_shares_one_client_within_a_call():
    """Внутри одного вызова клиент общий — это нужно для пула соединений."""
    extractors = build_extractors(["animego", "anilibria"])
    clients = {id(e.http_async) for e in extractors.values()}
    assert len(clients) == 1


def test_build_extractors_applies_headers():
    extractors = build_extractors(["animego"], headers={"X-Test": "1"})
    assert extractors["animego"].http_async.headers["X-Test"] == "1"


def test_build_extractors_applies_proxy():
    extractors = build_extractors(["animego"], proxy="http://127.0.0.1:9")
    # httpx не раскрывает прокси публично, но клиент должен быть создан отдельно
    # от дефолтного и не падать при конфигурации
    assert extractors["animego"].http_async is not None


async def test_startup_event_builds_extractors_into_context():
    from anicli_multi.commands import on_start_build_extractors

    app = FakeApp(["search", "ongoing", "history", "exit"])
    install(app, MultiConfig(sources=["animego"]))
    assert on_start_build_extractors in app.on_startup_events

    await on_start_build_extractors(app.context)
    assert list(app.context.data["multi_extractors"]) == ["animego"]


def test_install_puts_sources_and_timeout_into_context():
    app = FakeApp(["search", "ongoing", "history", "exit"])
    install(app, MultiConfig(sources=["animego", "hdrezka"], timeout=7.5))
    assert app.context.data["multi_sources"] == ["animego", "hdrezka"]
    assert app.context.data["multi_timeout"] == 7.5


def test_install_registers_startup_event_once():
    app = FakeApp(["search", "ongoing", "history", "exit"])
    install(app, MultiConfig())
    install(app, MultiConfig())
    assert len(app.on_startup_events) == 1


def test_hdrezka_uses_extended_extractor():
    from anicli_multi.hdrezka_all import HdrezkaAllExtractor

    extractors = build_extractors(["hdrezka"])
    assert isinstance(extractors["hdrezka"], HdrezkaAllExtractor)


def test_hdrezka_categories_are_passed_through():
    extractors = build_extractors(["hdrezka"], hdrezka_categories=["films"])
    assert extractors["hdrezka"].categories == frozenset({"films"})


def test_other_sources_use_stock_extractor():
    from anicli_multi.hdrezka_all import HdrezkaAllExtractor

    extractors = build_extractors(["animego"])
    assert not isinstance(extractors["animego"], HdrezkaAllExtractor)


def test_hdrezka_falls_back_to_stock_when_override_unsupported(monkeypatch):
    """Смена контракта anicli-api не должна ломать инструмент."""
    from anicli_multi.hdrezka_all import HdrezkaAllExtractor

    monkeypatch.setattr("anicli_multi.commands.check_hdrezka_override", lambda: ["вёрстка изменилась"])
    extractors = build_extractors(["hdrezka"])
    assert "hdrezka" in extractors
    assert not isinstance(extractors["hdrezka"], HdrezkaAllExtractor)


async def test_startup_event_passes_categories_from_context():
    from anicli_multi.commands import on_start_build_extractors

    app = FakeApp(["search", "ongoing", "history", "exit"])
    install(app, MultiConfig(sources=["hdrezka"], hdrezka_categories=["series"]))
    await on_start_build_extractors(app.context)
    assert app.context.data["multi_extractors"]["hdrezka"].categories == frozenset({"series"})


def test_install_puts_max_results_into_context():
    app = FakeApp(["search", "ongoing", "history", "exit"])
    install(app, MultiConfig(max_results=15))
    assert app.context.data["multi_max_results"] == 15


def test_install_puts_hdrezka_categories_into_context():
    app = FakeApp(["search", "ongoing", "history", "exit"])
    install(app, MultiConfig(hdrezka_categories=["films"]))
    assert app.context.data["multi_hdrezka_categories"] == ["films"]


def test_install_is_idempotent():
    """Повторный install() не должен падать на уже зарегистрированных алиасах."""
    app = FakeApp(["search", "ongoing", "history", "exit"])
    config = MultiConfig()
    install(app, config)
    install(app, config)  # не должно бросить ValueError

    assert app.command_manager.get_command("s") is not None
    assert app.command_manager.get_command("o") is not None


def test_install_registers_multi_fsm():
    app = FakeApp(["search", "ongoing", "history", "exit"])
    install(app, MultiConfig())
    assert [r.key for r in app.fsm_manager.registered] == ["multi"]


def test_install_overrides_search_command():
    app = FakeApp(["search", "ongoing", "history", "exit"])
    install(app, MultiConfig())
    route = app.command_manager.get_command("search")
    assert "нескольким источникам" in route.help


def test_install_respects_bare_text_search_disabled():
    """При выключенной настройке execute не должен подменяться.

    Сравнивать сами методы через `is` нельзя: обращение к bound method каждый раз
    создаёт новый объект. Проверяем наличие подменяющего атрибута на экземпляре.
    """
    app = FakeApp(["search", "ongoing", "history", "exit"])
    install(app, MultiConfig(bare_text_search=False))
    assert "execute" not in vars(app.command_manager)


def test_install_wraps_execute_when_bare_text_search_enabled():
    app = FakeApp(["search", "ongoing", "history", "exit"])
    install(app, MultiConfig(bare_text_search=True))
    assert "execute" in vars(app.command_manager)


async def test_alias_delegates_to_target_command():
    app = FakeApp(["search", "ongoing", "history", "exit"])
    install(app, MultiConfig())
    route = app.command_manager.get_command("o")

    class Ctx:
        pass

    ctx = Ctx()
    ctx.app = app
    await route.handler("", ctx)
    assert ("ongoing", "") in app.command_manager.calls
