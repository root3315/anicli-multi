from anicli_multi.hdrezka_all import (
    DEFAULT_CATEGORIES,
    HdrezkaAllExtractor,
    UnfilteredPageSearch,
)
from anicli_multi.kinds import KNOWN_CATEGORIES

ROWS = [
    {
        "title": "Интерстеллар",
        "season": "",
        "thumbnail": "t1",
        "url": "https://hdrezka-home.tv/films/fiction/2259-interstellar-2014.html",
    },
    {
        "title": "Во все тяжкие",
        "season": "Завершен",
        "thumbnail": "t2",
        "url": "https://hdrezka-home.tv/series/thriller/646-vo-vse-tyazhkie.html",
    },
    {
        "title": "Армитаж",
        "season": "",
        "thumbnail": "t3",
        "url": "https://hdrezka-home.tv/animation/adventures/24686-armitazh.html",
    },
    {
        "title": "Медведи",
        "season": "1 сезон",
        "thumbnail": "t4",
        "url": "https://hdrezka-home.tv/cartoons/comedy/91389-medvedi.html",
    },
]


def test_default_categories_cover_all_known():
    assert set(DEFAULT_CATEGORIES) == set(KNOWN_CATEGORIES)


def test_unfiltered_search_is_a_page_search_subclass():
    from anicli_api.source.parsers.hdrezka_parser import PageSearch

    assert issubclass(UnfilteredPageSearch, PageSearch)


def test_unfiltered_split_doc_keeps_non_animation_items():
    """Ровно то, что чинит эта фича: фильтр /animation/ снят."""
    from lxml import html

    doc = html.fromstring(
        "<div>"
        '<div class="b-content__inline_item" data-url="https://x/films/1.html"></div>'
        '<div class="b-content__inline_item" data-url="https://x/animation/2.html"></div>'
        '<div class="b-content__inline_item"></div>'
        "</div>"
    )
    items = UnfilteredPageSearch(doc)._split_doc(doc)
    assert [i.get("data-url") for i in items] == [
        "https://x/films/1.html",
        "https://x/animation/2.html",
    ]


def test_stock_parser_really_filters_out_films():
    """Подтверждает причину существования UnfilteredPageSearch."""
    from anicli_api.source.parsers.hdrezka_parser import PageSearch
    from lxml import html

    doc = html.fromstring(
        "<div>"
        '<div class="b-content__inline_item" data-url="https://x/films/1.html"></div>'
        '<div class="b-content__inline_item" data-url="https://x/animation/2.html"></div>'
        "</div>"
    )
    items = PageSearch(doc)._split_doc(doc)
    assert [i.get("data-url") for i in items] == ["https://x/animation/2.html"]


def _extractor(categories=None):
    return HdrezkaAllExtractor(categories=categories)


def test_all_categories_by_default():
    assert len(_extractor()._to_results(ROWS)) == 4


def test_filters_to_requested_categories():
    assert [r.title for r in _extractor(categories=["films"])._to_results(ROWS)] == ["Интерстеллар"]


def test_animation_only_restores_old_behaviour():
    assert [r.title for r in _extractor(categories=["animation"])._to_results(ROWS)] == ["Армитаж"]


def test_empty_categories_falls_back_to_all():
    assert len(_extractor(categories=[])._to_results(ROWS)) == 4


def test_season_is_appended_to_title_without_trailing_space():
    assert _extractor(categories=["films"])._to_results(ROWS)[0].title == "Интерстеллар"


def test_season_is_appended_when_present():
    assert _extractor(categories=["series"])._to_results(ROWS)[0].title == "Во все тяжкие Завершен"


def test_results_carry_url_for_kind_resolution():
    assert "/series/" in _extractor(categories=["series"])._to_results(ROWS)[0].url


def test_subclasses_upstream_extractor():
    from anicli_api.source import hdrezka

    assert issubclass(HdrezkaAllExtractor, hdrezka.Extractor)
