from anicli_multi.fsm import MultiSearchFSM, SourceRow, resolve_entry
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
