from anicli_multi.grouping import TitleGroup, group_results


class FakeResult:
    """Подделка BaseSearch: нужен только .title."""

    def __init__(self, title: str):
        self.title = title


PRIORITY = ["animego", "hdrezka", "yummy-anime", "anilibria"]


def test_same_title_across_sources_becomes_one_group():
    per_source = [
        ("animego", [FakeResult("Наруто")]),
        ("hdrezka", [FakeResult("Наруто ")]),
        ("anilibria", [FakeResult("НАРУТО")]),
    ]
    groups = group_results(per_source, PRIORITY)
    assert len(groups) == 1
    assert groups[0].sources == ["animego", "hdrezka", "anilibria"]


def test_display_title_comes_from_highest_priority_source():
    per_source = [
        ("hdrezka", [FakeResult("наруто")]),
        ("animego", [FakeResult("Наруто")]),
    ]
    groups = group_results(per_source, PRIORITY)
    assert groups[0].title == "Наруто"


def test_different_titles_stay_separate():
    per_source = [
        ("animego", [FakeResult("Наруто"), FakeResult("Наруто: Ураганные хроники")]),
    ]
    groups = group_results(per_source, PRIORITY)
    assert len(groups) == 2


def test_groups_sorted_by_source_count_desc():
    per_source = [
        ("animego", [FakeResult("Один источник"), FakeResult("Два источника")]),
        ("hdrezka", [FakeResult("Два источника")]),
    ]
    groups = group_results(per_source, PRIORITY)
    assert groups[0].title == "Два источника"
    assert len(groups[0].sources) == 2


def test_duplicate_title_within_one_source_kept_once():
    """Источник вернул дубль — в группе должна остаться одна запись от него."""
    per_source = [("animego", [FakeResult("Наруто"), FakeResult("Наруто ")])]
    groups = group_results(per_source, PRIORITY)
    assert len(groups) == 1
    assert groups[0].sources == ["animego"]
    assert len(groups[0].entries) == 1


def test_entries_ordered_by_priority():
    per_source = [
        ("anilibria", [FakeResult("Наруто")]),
        ("animego", [FakeResult("Наруто")]),
        ("hdrezka", [FakeResult("Наруто")]),
    ]
    groups = group_results(per_source, PRIORITY)
    assert groups[0].sources == ["animego", "hdrezka", "anilibria"]


def test_empty_input():
    assert group_results([], PRIORITY) == []


def test_source_absent_from_priority_goes_last():
    per_source = [
        ("неизвестный", [FakeResult("Наруто")]),
        ("animego", [FakeResult("Наруто")]),
    ]
    groups = group_results(per_source, PRIORITY)
    assert groups[0].sources == ["animego", "неизвестный"]


def test_str_contains_title_and_sources():
    per_source = [
        ("animego", [FakeResult("Наруто")]),
        ("hdrezka", [FakeResult("Наруто")]),
    ]
    rendered = str(group_results(per_source, PRIORITY)[0])
    assert "Наруто" in rendered
    assert "animego" in rendered
    assert "hdrezka" in rendered


def test_title_group_is_dataclass_with_expected_fields():
    group = TitleGroup(key="наруто", title="Наруто", entries=[("animego", FakeResult("Наруто"))])
    assert group.sources == ["animego"]
