from anicli_multi.fsm import (
    MAX_PROMPT_TITLE,
    NAV_HINT,
    MultiSearchFSM,
    SourceRow,
    resolve_entry,
    shorten_title,
)
from anicli_multi.grouping import TitleGroup


class FakeResult:
    def __init__(self, title: str):
        self.title = title


def test_source_row_str_is_source_name():
    assert str(SourceRow("animego")) == "animego"


def test_resolve_entry_single_source_returns_it():
    group = TitleGroup(key="наруто", title="Наруто", entries=[("animego", FakeResult("Наруто"))])
    assert resolve_entry(group) == ("animego", group.entries[0][1])


def test_resolve_entry_multiple_sources_returns_none():
    group = TitleGroup(
        key="наруто",
        title="Наруто",
        entries=[("animego", FakeResult("Наруто")), ("hdrezka", FakeResult("Наруто"))],
    )
    assert resolve_entry(group) is None


def test_fsm_route_key_is_multi():
    assert MultiSearchFSM.key == "multi"


def test_fsm_declares_both_first_states():
    assert "step_1" in MultiSearchFSM.states
    assert "step_1_source" in MultiSearchFSM.states


def test_fsm_inherits_playback_states_from_upstream():
    """Шаги выбора серии и озвучки не переопределяются — переиспользуем anicli-ru."""
    for state in ("step_2", "step_3", "step_3_batched"):
        assert state in MultiSearchFSM.states


def test_initial_state_is_step_1():
    assert MultiSearchFSM.initial_state == "step_1"


LONG_TITLE = "Я перевоплотился в седьмого принца, так что я буду совершенствовать свою магию, как захочу"


def test_shorten_title_leaves_short_titles_alone():
    assert shorten_title("Наруто") == "Наруто"


def test_shorten_title_trims_long_title():
    result = shorten_title(LONG_TITLE)
    assert len(result) <= MAX_PROMPT_TITLE
    assert result.endswith("…")
    assert result.startswith("Я перевоплотился")


def test_shorten_title_strips_whitespace():
    assert shorten_title("  Наруто  ") == "Наруто"


def test_shorten_title_at_exact_limit_is_untouched():
    exact = "x" * MAX_PROMPT_TITLE
    assert shorten_title(exact) == exact


def test_nav_hint_mentions_both_navigation_commands():
    assert ".." in NAV_HINT
    assert "~" in NAV_HINT


def test_nav_hint_matches_upstream_navigation_commands():
    """Подсказка должна называть команды, которые действительно существуют."""
    from anicli.cli.ptk_lib.core.fsm import BaseFSM

    available = set(BaseFSM.NAVIGATION_COMMANDS)
    assert ".." in available
    assert "~" in available


def test_validator_appends_nav_hint_to_error(monkeypatch):
    """Текст ошибки — то, что пользователь увидит, застряв на шаге."""
    fsm = MultiSearchFSM.fsm_class.__new__(MultiSearchFSM.fsm_class)
    monkeypatch.setattr(
        type(fsm).__mro__[1],
        "_get_user_dynamic_validator",
        lambda self, state_name, user_input: "episode index or slice required",
        raising=False,
    )
    result = fsm._get_user_dynamic_validator("step_2", "")
    assert "episode index or slice required" in result
    assert NAV_HINT in result


def test_delegated_states_call_upstream_handler():
    """step_3 и step_3_batched — тонкие делегаты, логика остаётся в anicli-ru."""
    from anicli.cli.fsm import BaseAnimeFSM

    for state in ("step_3", "step_3_batched"):
        assert callable(getattr(BaseAnimeFSM, state).handler)
        assert state in MultiSearchFSM.states


async def test_step_3_delegate_forwards_input_and_prints_hint(monkeypatch, capsys):
    """Делегат обязан прокинуть ввод в upstream и напечатать подсказку после плеера."""
    from anicli.cli.fsm import BaseAnimeFSM

    seen = {}

    async def fake_handler(_self, user_input):
        seen["input"] = user_input

    monkeypatch.setattr(BaseAnimeFSM.step_3, "handler", fake_handler)

    fsm = MultiSearchFSM.fsm_class.__new__(MultiSearchFSM.fsm_class)
    await MultiSearchFSM.states["step_3"].handler(fsm, "2")

    assert seen["input"] == "2"
    assert ".." in capsys.readouterr().out


async def test_step_3_batched_delegate_forwards_input(monkeypatch, capsys):
    from anicli.cli.fsm import BaseAnimeFSM

    seen = {}

    async def fake_handler(_self, user_input):
        seen["input"] = user_input

    monkeypatch.setattr(BaseAnimeFSM.step_3_batched, "handler", fake_handler)

    fsm = MultiSearchFSM.fsm_class.__new__(MultiSearchFSM.fsm_class)
    await MultiSearchFSM.states["step_3_batched"].handler(fsm, "1-5")

    assert seen["input"] == "1-5"
    assert ".." in capsys.readouterr().out
