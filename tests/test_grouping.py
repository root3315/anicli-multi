from anicli_multi.grouping import TitleGroup, group_results, relevance_rank


class FakeResult:
    """Подделка BaseSearch: нужны только .title и .url."""

    def __init__(self, title: str, url: str = "https://animego.me/anime/x"):
        self.title = title
        self.url = url


PRIORITY = ["animego", "hdrezka", "yummy-anime", "anilibria"]

FILM_URL = "https://hdrezka-home.tv/films/drama/1-tetrad-smerti-2017.html"
HDREZKA_ANIME_URL = "https://hdrezka-home.tv/animation/x/2-tetrad-smerti-2006.html"
ANIMEGO_URL = "https://animego.me/anime/tetrad-smerti-1"


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
    group = TitleGroup(
        key=("аниме", "наруто"),
        title="Наруто",
        kind="аниме",
        entries=[("animego", FakeResult("Наруто"))],
    )
    assert group.sources == ["animego"]


def test_movie_and_anime_with_same_title_do_not_merge():
    """Главный тест спеки: игровой фильм и аниме «Тетрадь смерти» — разные строки."""
    per_source = [
        ("animego", [FakeResult("Тетрадь смерти", ANIMEGO_URL)]),
        ("hdrezka", [FakeResult("Тетрадь смерти", FILM_URL)]),
    ]
    groups = group_results(per_source, PRIORITY)
    assert len(groups) == 2
    assert sorted(g.kind for g in groups) == ["аниме", "фильм"]


def test_hdrezka_anime_still_merges_with_anime_sources():
    """Регрессия: аниме с hdrezka обязано склеиваться с аниме-источниками."""
    per_source = [
        ("animego", [FakeResult("Тетрадь смерти", ANIMEGO_URL)]),
        ("hdrezka", [FakeResult("Тетрадь смерти", HDREZKA_ANIME_URL)]),
    ]
    groups = group_results(per_source, PRIORITY)
    assert len(groups) == 1
    assert groups[0].sources == ["animego", "hdrezka"]
    assert groups[0].kind == "аниме"


def test_group_key_is_pair_of_kind_and_title():
    per_source = [("hdrezka", [FakeResult("Интерстеллар", FILM_URL)])]
    group = group_results(per_source, PRIORITY)[0]
    assert group.key == ("фильм", "интерстеллар")


def test_badge_shown_for_non_anime():
    per_source = [("hdrezka", [FakeResult("Интерстеллар", FILM_URL)])]
    assert "[фильм]" in str(group_results(per_source, PRIORITY)[0])


def test_badge_hidden_for_anime():
    per_source = [("animego", [FakeResult("Наруто", ANIMEGO_URL)])]
    assert "[аниме]" not in str(group_results(per_source, PRIORITY)[0])


def test_markup_like_title_is_escaped_for_rich():
    """Скобка со строчной латиницы — разметка для rich, без экранирования текст пропадёт."""
    per_source = [("animego", [FakeResult("Тайтл [ova-8]", ANIMEGO_URL)])]
    assert r"\[ova-8]" in str(group_results(per_source, PRIORITY)[0])


def test_title_survives_real_rich_render():
    """Проверка через настоящий рендер rich, а не подстрокой."""
    from rich.markup import render

    per_source = [("animego", [FakeResult("Тайтл [ova-8]", ANIMEGO_URL)])]
    plain = render(str(group_results(per_source, PRIORITY)[0])).plain
    assert "Тайтл [ova-8]" in plain


def test_badge_survives_real_rich_render():
    from rich.markup import render

    per_source = [("hdrezka", [FakeResult("Интерстеллар", FILM_URL)])]
    plain = render(str(group_results(per_source, PRIORITY)[0])).plain
    assert "Интерстеллар [фильм]" in plain


def test_relevance_rank_orders_exact_prefix_substring_rest():
    assert relevance_rank("во все тяжкие", "во все тяжкие") == 0
    assert relevance_rank("во все тяжкие", "во все тяжкие мини эпизоды") == 1
    assert relevance_rank("во все тяжкие", "el camino во все тяжкие") == 2
    assert relevance_rank("во все тяжкие", "власть книжного червя") == 3


def test_relevance_rank_without_query_is_neutral():
    assert relevance_rank("", "что угодно") == 0


def test_exact_match_outranks_multi_source_noise():
    """Тот самый случай: сериал с одного источника должен быть выше мусора с трёх."""
    per_source = [
        ("animego", [FakeResult("Призванный в другой мир во второй раз"), FakeResult("Во все тяжкие мини")]),
        ("yummy-anime", [FakeResult("Призванный в другой мир во второй раз")]),
        ("anilibria", [FakeResult("Призванный в другой мир во второй раз")]),
        ("hdrezka", [FakeResult("Во все тяжкие", FILM_URL)]),
    ]
    groups = group_results(per_source, PRIORITY, query="во все тяжкие")
    assert groups[0].title == "Во все тяжкие"


def test_prefix_match_outranks_substring_match():
    per_source = [
        ("animego", [FakeResult("Наука Интерстеллар"), FakeResult("Интерстеллар навсегда")]),
    ]
    groups = group_results(per_source, PRIORITY, query="интерстеллар")
    assert [g.title for g in groups] == ["Интерстеллар навсегда", "Наука Интерстеллар"]


def test_without_query_sorting_is_unchanged():
    """Обратная совместимость: без запроса первым ключом остаётся число источников."""
    per_source = [
        ("animego", [FakeResult("Один"), FakeResult("Два")]),
        ("hdrezka", [FakeResult("Два")]),
    ]
    groups = group_results(per_source, PRIORITY)
    assert groups[0].title == "Два"


def test_custom_kind_resolver_is_used():
    per_source = [("animego", [FakeResult("Что-то", ANIMEGO_URL)])]
    groups = group_results(per_source, PRIORITY, kind_resolver=lambda _s, _u: "шоу")
    assert groups[0].kind == "шоу"
