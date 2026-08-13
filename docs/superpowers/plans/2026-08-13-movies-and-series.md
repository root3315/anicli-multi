# Фильмы и сериалы — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Один поиск в `ani` находит аниме, фильмы, сериалы, мультфильмы и шоу, с видимым типом контента.

**Architecture:** Подкласс `anicli_api.source.hdrezka.Extractor` использует свой `PageSearch` без отсечения по `/animation/` и фильтрует разобранные строки по списку категорий. Тип контента выводится из первого сегмента пути URL и входит в ключ группировки, чтобы одноимённые аниме и игровой фильм не склеивались.

**Tech Stack:** Python 3.9+, anicli-api, lxml/cssselect, rich, pytest.

## Global Constraints

- Установленный `anicli-api` не модифицируется. Расширение только наследованием в нашем пакете.
- Аннотации в стиле PEP 585 (`list`, `dict`, `tuple`), не `typing.List` — этого требует ruff при `target-version = "py39"`.
- Синтаксис только 3.9-совместимый: никаких `X | Y` в аннотациях.
- Категории и их отображаемые имена: `animation`→`аниме`, `films`→`фильм`, `series`→`сериал`, `cartoons`→`мультфильм`, `show`→`шоу`.
- Бейдж типа показывается **только для не-аниме**.
- Склейка групп только по точному совпадению нормализованного названия **в пределах одного типа**.
- Все команды выполняются в активированном `.venv` проекта.
- Сообщения пользователю на русском.

---

### Task 1: Тип контента

**Files:**
- Create: `anicli_multi/kinds.py`
- Test: `tests/test_kinds.py`

**Interfaces:**
- Consumes: ничего.
- Produces:
  - `ANIME: str` = `"аниме"`
  - `CATEGORY_TO_KIND: dict[str, str]`
  - `KNOWN_CATEGORIES: frozenset[str]`
  - `CATEGORY_SOURCES: frozenset[str]` = `{"hdrezka"}`
  - `category_from_url(url: str) -> str`
  - `resolve_kind(source: str, url: str) -> str`

- [ ] **Step 1: Написать падающие тесты**

Файл `tests/test_kinds.py`:

```python
import pytest

from anicli_multi.kinds import (
    ANIME,
    CATEGORY_TO_KIND,
    KNOWN_CATEGORIES,
    category_from_url,
    resolve_kind,
)

FILM_URL = "https://hdrezka-home.tv/films/fiction/2259-interstellar-2014.html"
SERIES_URL = "https://hdrezka-home.tv/series/thriller/646-vo-vse-tyazhkie-2008-latest.html"
ANIME_URL = "https://hdrezka-home.tv/animation/adventures/24686-armitazh.html"
CARTOON_URL = "https://hdrezka-home.tv/cartoons/comedy/91389-medvedi-2026.html"
ANIMEGO_URL = "https://animego.me/anime/naruto-123"


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (FILM_URL, "films"),
        (SERIES_URL, "series"),
        (ANIME_URL, "animation"),
        (CARTOON_URL, "cartoons"),
        (ANIMEGO_URL, "anime"),
    ],
)
def test_category_from_url(url, expected):
    assert category_from_url(url) == expected


@pytest.mark.parametrize("url", ["", "не url", "https://hdrezka-home.tv", "https://hdrezka-home.tv/"])
def test_category_from_url_without_path(url):
    assert category_from_url(url) == ""


def test_category_from_url_does_not_raise_on_broken_url():
    assert category_from_url("http://[") == ""


def test_all_five_categories_are_known():
    assert KNOWN_CATEGORIES == {"animation", "films", "series", "cartoons", "show"}


def test_category_to_kind_values():
    assert CATEGORY_TO_KIND["films"] == "фильм"
    assert CATEGORY_TO_KIND["series"] == "сериал"
    assert CATEGORY_TO_KIND["cartoons"] == "мультфильм"
    assert CATEGORY_TO_KIND["show"] == "шоу"
    assert CATEGORY_TO_KIND["animation"] == ANIME


def test_resolve_kind_for_hdrezka_uses_url():
    assert resolve_kind("hdrezka", FILM_URL) == "фильм"
    assert resolve_kind("hdrezka", SERIES_URL) == "сериал"
    assert resolve_kind("hdrezka", ANIME_URL) == ANIME


def test_resolve_kind_for_anime_sources_is_always_anime():
    """У аниме-источников свои схемы путей; разбирать их URL нельзя."""
    for source in ("animego", "anilibria", "yummy-anime", "animevost"):
        assert resolve_kind(source, ANIMEGO_URL) == ANIME
        assert resolve_kind(source, FILM_URL) == ANIME


def test_resolve_kind_falls_back_to_anime_on_unknown_category():
    assert resolve_kind("hdrezka", "https://hdrezka-home.tv/чтотоновое/x.html") == ANIME


def test_resolve_kind_handles_empty_url():
    assert resolve_kind("hdrezka", "") == ANIME
```

- [ ] **Step 2: Запустить — убедиться, что падают**

Run: `python -m pytest tests/test_kinds.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'anicli_multi.kinds'`

- [ ] **Step 3: Реализовать `anicli_multi/kinds.py`**

```python
"""Тип контента: аниме, фильм, сериал, мультфильм, шоу."""

from urllib.parse import urlsplit

ANIME = "аниме"
MOVIE = "фильм"
SERIES = "сериал"
CARTOON = "мультфильм"
SHOW = "шоу"

# Первый сегмент пути в URL hdrezka -> отображаемый тип
CATEGORY_TO_KIND: dict[str, str] = {
    "animation": ANIME,
    "films": MOVIE,
    "series": SERIES,
    "cartoons": CARTOON,
    "show": SHOW,
}
KNOWN_CATEGORIES = frozenset(CATEGORY_TO_KIND)

# Источники, у которых тип определяется по URL. Для остальных тип всегда «аниме»:
# у аниме-сайтов свои схемы путей (/anime/, /release/), и случайное совпадение
# сегмента с «films» дало бы ложный тип.
CATEGORY_SOURCES = frozenset({"hdrezka"})


def category_from_url(url: str) -> str:
    """Первый сегмент пути. Пустая строка, если разобрать нечего."""
    try:
        path = urlsplit(url).path
    except ValueError:
        return ""
    parts = [part for part in path.split("/") if part]
    return parts[0] if parts else ""


def resolve_kind(source: str, url: str) -> str:
    """Тип контента для результата поиска."""
    if source not in CATEGORY_SOURCES:
        return ANIME
    return CATEGORY_TO_KIND.get(category_from_url(url), ANIME)
```

- [ ] **Step 4: Запустить — убедиться, что проходят**

Run: `python -m pytest tests/test_kinds.py -q`
Expected: PASS

- [ ] **Step 5: Коммит**

```bash
git add anicli_multi/kinds.py tests/test_kinds.py
git commit -m "feat: определение типа контента по URL"
```

---

### Task 2: Тип в ключе группировки и бейдж в выдаче

**Files:**
- Modify: `anicli_multi/grouping.py`
- Modify: `tests/test_grouping.py`

**Interfaces:**
- Consumes: `resolve_kind(source, url) -> str`, `ANIME` из Task 1.
- Produces:
  - `TitleGroup.key` меняет тип с `str` на `tuple[str, str]` — пара `(kind, нормализованное название)`.
  - `TitleGroup.kind: str` — новое поле, по умолчанию `ANIME`.
  - `group_results(per_source, priority, kind_resolver=resolve_kind)` — новый необязательный параметр.

- [ ] **Step 1: Написать падающие тесты**

Дописать в `tests/test_grouping.py`. `FakeResult` теперь должен иметь `url` — группировка читает его для определения типа.

```python
FILM_URL = "https://hdrezka-home.tv/films/drama/1-tetrad-smerti-2017.html"
HDREZKA_ANIME_URL = "https://hdrezka-home.tv/animation/x/2-tetrad-smerti-2006.html"
ANIMEGO_URL = "https://animego.me/anime/tetrad-smerti-1"


def test_movie_and_anime_with_same_title_do_not_merge():
    """Главный тест спеки: игровой фильм и аниме «Тетрадь смерти» — разные строки."""
    per_source = [
        ("animego", [FakeResult("Тетрадь смерти", ANIMEGO_URL)]),
        ("hdrezka", [FakeResult("Тетрадь смерти", FILM_URL)]),
    ]
    groups = group_results(per_source, PRIORITY)
    assert len(groups) == 2
    kinds = sorted(g.kind for g in groups)
    assert kinds == ["аниме", "фильм"]


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


def test_square_brackets_in_title_are_escaped_for_rich():
    """Названия вроде «Наруто [OVA-8]» не должны трактоваться как разметка rich."""
    per_source = [("animego", [FakeResult("Наруто [OVA-8]", ANIMEGO_URL)])]
    rendered = str(group_results(per_source, PRIORITY)[0])
    assert r"\[OVA-8]" in rendered


def test_custom_kind_resolver_is_used():
    per_source = [("animego", [FakeResult("Что-то", ANIMEGO_URL)])]
    groups = group_results(per_source, PRIORITY, kind_resolver=lambda _s, _u: "шоу")
    assert groups[0].kind == "шоу"
```

Также обновить существующий `FakeResult` в этом файле и тест, конструирующий `TitleGroup` напрямую:

```python
class FakeResult:
    """Подделка BaseSearch: нужны только .title и .url."""

    def __init__(self, title: str, url: str = "https://animego.me/anime/x"):
        self.title = title
        self.url = url
```

```python
def test_title_group_is_dataclass_with_expected_fields():
    group = TitleGroup(
        key=("аниме", "наруто"),
        title="Наруто",
        kind="аниме",
        entries=[("animego", FakeResult("Наруто"))],
    )
    assert group.sources == ["animego"]
```

- [ ] **Step 2: Запустить — убедиться, что падают**

Run: `python -m pytest tests/test_grouping.py -q`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'kind'` и несовпадение ключа.

- [ ] **Step 3: Обновить `anicli_multi/grouping.py`**

Заменить импорты и класс:

```python
"""Склейка результатов поиска разных источников в группы по одному тайтлу."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Callable

from rich.markup import escape

from .kinds import ANIME, resolve_kind
from .normalize import normalize_title

# (имя источника, объект результата поиска)
Entry = tuple[str, Any]
# (тип контента, нормализованное название)
GroupKey = tuple[str, str]
KindResolver = Callable[[str, str], str]


@dataclass
class TitleGroup:
    """Один тайтл одного типа, найденный на одном или нескольких источниках."""

    key: GroupKey
    title: str
    kind: str = ANIME
    entries: list[Entry] = field(default_factory=list)

    @property
    def sources(self) -> list[str]:
        return [source for source, _ in self.entries]

    def __str__(self) -> str:
        # render_table печатает str(result), а rich трактует [...] как разметку.
        # Название экранируем: в выдаче встречается «Наруто [OVA-8]».
        # Бейдж пишем как \[тип], чтобы rich вывел скобки буквально.
        badge = "" if self.kind == ANIME else f" \\[{self.kind}]"
        return f"{escape(self.title)}{badge} [dim]({', '.join(self.sources)})[/dim]"
```

Заменить тело `group_results`:

```python
def group_results(
    per_source: Sequence[tuple[str, Sequence[Any]]],
    priority: Sequence[str],
    kind_resolver: KindResolver = resolve_kind,
) -> list[TitleGroup]:
    """Сгруппировать результаты по паре (тип контента, нормализованное название).

    Тип входит в ключ намеренно: без него одноимённые аниме и игровой фильм
    склеились бы в одну строку (см. спеку по фильмам, §6).
    """
    groups: dict[GroupKey, TitleGroup] = {}

    for source, results in per_source:
        for result in results:
            normalized = normalize_title(result.title)
            if not normalized:
                continue
            kind = kind_resolver(source, getattr(result, "url", "") or "")
            key: GroupKey = (kind, normalized)
            group = groups.get(key)
            if group is None:
                groups[key] = TitleGroup(key=key, title=result.title, kind=kind, entries=[(source, result)])
                continue
            # один источник на группу: дубли внутри источника отбрасываем
            if source in group.sources:
                continue
            group.entries.append((source, result))

    ordered: list[TitleGroup] = []
    for group in groups.values():
        group.entries.sort(key=lambda e: _priority_index(e[0], priority))
        _, best_result = group.entries[0]
        group.title = best_result.title.strip()
        ordered.append(group)

    ordered.sort(
        key=lambda g: (
            -len(g.entries),
            _priority_index(g.entries[0][0], priority),
            g.title.lower(),
        )
    )
    return ordered
```

- [ ] **Step 4: Запустить весь набор**

Run: `python -m pytest -q`
Expected: PASS. Тест `test_group_entries_carry_their_own_source` в `tests/test_integration.py` сети требует и в обычный прогон не входит.

- [ ] **Step 5: Линтеры**

Run: `python -m ruff check . && python -m mypy anicli_multi`
Expected: без ошибок.

- [ ] **Step 6: Коммит**

```bash
git add anicli_multi/grouping.py tests/test_grouping.py
git commit -m "feat: тип контента в ключе группировки и бейдж в выдаче"
```

---

### Task 3: Экстрактор hdrezka без фильтра категорий

**Files:**
- Create: `anicli_multi/hdrezka_all.py`
- Test: `tests/test_hdrezka_all.py`

**Interfaces:**
- Consumes: `KNOWN_CATEGORIES`, `category_from_url` из Task 1.
- Produces:
  - `DEFAULT_CATEGORIES: tuple[str, ...]` — все пять, в стабильном порядке.
  - `UnfilteredPageSearch(PageSearch)`
  - `HdrezkaAllExtractor(hdrezka.Extractor)` с `__init__(self, *args, categories=None, **kwargs)`.

- [ ] **Step 1: Написать падающие тесты**

Файл `tests/test_hdrezka_all.py`. Сеть не трогаем: подставляем разобранные строки вместо HTTP.

```python
from anicli_multi.hdrezka_all import (
    DEFAULT_CATEGORIES,
    HdrezkaAllExtractor,
    UnfilteredPageSearch,
)
from anicli_multi.kinds import KNOWN_CATEGORIES

ROWS = [
    {"title": "Интерстеллар", "season": "", "thumbnail": "t1",
     "url": "https://hdrezka-home.tv/films/fiction/2259-interstellar-2014.html"},
    {"title": "Во все тяжкие", "season": "Завершен", "thumbnail": "t2",
     "url": "https://hdrezka-home.tv/series/thriller/646-vo-vse-tyazhkie.html"},
    {"title": "Армитаж", "season": "", "thumbnail": "t3",
     "url": "https://hdrezka-home.tv/animation/adventures/24686-armitazh.html"},
    {"title": "Медведи", "season": "1 сезон", "thumbnail": "t4",
     "url": "https://hdrezka-home.tv/cartoons/comedy/91389-medvedi.html"},
]


def test_default_categories_cover_all_known():
    assert set(DEFAULT_CATEGORIES) == KNOWN_CATEGORIES


def test_unfiltered_search_is_a_page_search_subclass():
    from anicli_api.source.parsers.hdrezka_parser import PageSearch

    assert issubclass(UnfilteredPageSearch, PageSearch)


def test_unfiltered_split_doc_keeps_non_animation_items():
    """Ровно то, что чинит эта фича: фильтр /animation/ снят."""
    from lxml import html

    doc = html.fromstring(
        '<div>'
        '<div class="b-content__inline_item" data-url="https://x/films/1.html"></div>'
        '<div class="b-content__inline_item" data-url="https://x/animation/2.html"></div>'
        '<div class="b-content__inline_item"></div>'
        '</div>'
    )
    items = UnfilteredPageSearch(doc)._split_doc(doc)
    urls = [i.get("data-url") for i in items]
    assert urls == ["https://x/films/1.html", "https://x/animation/2.html"]


def _extractor(categories=None):
    return HdrezkaAllExtractor(categories=categories)


def test_all_categories_by_default():
    results = _extractor()._to_results(ROWS)
    assert len(results) == 4


def test_filters_to_requested_categories():
    results = _extractor(categories=["films"])._to_results(ROWS)
    assert [r.title for r in results] == ["Интерстеллар"]


def test_animation_only_restores_old_behaviour():
    results = _extractor(categories=["animation"])._to_results(ROWS)
    assert [r.title for r in results] == ["Армитаж"]


def test_empty_categories_falls_back_to_all():
    results = _extractor(categories=[])._to_results(ROWS)
    assert len(results) == 4


def test_season_is_appended_to_title_without_trailing_space():
    results = _extractor(categories=["films"])._to_results(ROWS)
    assert results[0].title == "Интерстеллар"


def test_season_is_appended_when_present():
    results = _extractor(categories=["series"])._to_results(ROWS)
    assert results[0].title == "Во все тяжкие Завершен"


def test_results_carry_url_for_kind_resolution():
    results = _extractor(categories=["series"])._to_results(ROWS)
    assert "/series/" in results[0].url


def test_subclasses_upstream_extractor():
    from anicli_api.source import hdrezka

    assert issubclass(HdrezkaAllExtractor, hdrezka.Extractor)
```

- [ ] **Step 2: Запустить — убедиться, что падают**

Run: `python -m pytest tests/test_hdrezka_all.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'anicli_multi.hdrezka_all'`

- [ ] **Step 3: Реализовать `anicli_multi/hdrezka_all.py`**

```python
"""Экстрактор hdrezka без отсечения не-аниме категорий.

anicli-api запрашивает у hdrezka весь каталог, но при разборе оставляет только
ссылки с «/animation/» (anicli_api/source/parsers/hdrezka_parser.py). Фильмы и
сериалы приходят в том же ответе и выбрасываются. Здесь фильтр снят, а отбор по
категориям делается уже после разбора — в самом парсере это невозможно, потому
что _split_doc вызывается из classmethod-фабрики fetch/async_fetch, куда
конфигурацию экземпляра не передать.
"""

from collections.abc import Sequence
from typing import Any, Optional

from anicli_api._http import ANUBIS_BYPASS_HEADERS
from anicli_api.source import hdrezka
from anicli_api.source.parsers.hdrezka_parser import PageSearch

from .kinds import KNOWN_CATEGORIES, category_from_url

DEFAULT_CATEGORIES: tuple[str, ...] = tuple(sorted(KNOWN_CATEGORIES))

_ITEM_SELECTOR = ".b-content__inline_item"


class UnfilteredPageSearch(PageSearch):
    """PageSearch без проверки на «/animation/» в data-url."""

    def _split_doc(self, v: Any) -> list[Any]:
        return [item for item in v.cssselect(_ITEM_SELECTOR) if "data-url" in item.attrib]


class HdrezkaAllExtractor(hdrezka.Extractor):
    """hdrezka со всеми категориями каталога."""

    def __init__(self, *args: Any, categories: Optional[Sequence[str]] = None, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.categories = frozenset(categories) if categories else frozenset(DEFAULT_CATEGORIES)

    def _to_results(self, rows: Sequence[dict]) -> list[Any]:
        return [
            hdrezka.Search(
                title=f"{row['title']} {row['season']}".strip(),
                url=row["url"],
                thumbnail=row["thumbnail"],
                **self._kwargs_http,
            )
            for row in rows
            if category_from_url(row["url"]) in self.categories
        ]

    def search(self, query: str) -> list[Any]:
        page = UnfilteredPageSearch.fetch(self.http, query=query, headers=ANUBIS_BYPASS_HEADERS)
        return self._to_results(page.parse())

    async def a_search(self, query: str) -> list[Any]:
        page = await UnfilteredPageSearch.async_fetch(
            self.http_async, query=query, headers=ANUBIS_BYPASS_HEADERS
        )
        return self._to_results(page.parse())
```

- [ ] **Step 4: Запустить — убедиться, что проходят**

Run: `python -m pytest tests/test_hdrezka_all.py -q`
Expected: PASS

- [ ] **Step 5: Коммит**

```bash
git add anicli_multi/hdrezka_all.py tests/test_hdrezka_all.py
git commit -m "feat: экстрактор hdrezka со всеми категориями каталога"
```

---

### Task 4: Подключение, конфиг и проверка совместимости

**Files:**
- Modify: `anicli_multi/config.py`
- Modify: `anicli_multi/compat.py`
- Modify: `anicli_multi/commands.py`
- Modify: `tests/test_config.py`
- Modify: `tests/test_compat.py`
- Modify: `tests/test_commands.py`

**Interfaces:**
- Consumes: `HdrezkaAllExtractor`, `DEFAULT_CATEGORIES` (Task 3); `KNOWN_CATEGORIES` (Task 1).
- Produces:
  - `MultiConfig.hdrezka_categories: list[str]`
  - `check_hdrezka_override() -> list[str]` в `compat.py`
  - `build_extractors(..., hdrezka_categories: Optional[Sequence[str]] = None)`

- [ ] **Step 1: Написать падающие тесты конфига**

Дописать в `tests/test_config.py`:

```python
def test_hdrezka_categories_default_is_all(tmp_path):
    config = load_config(tmp_path / "нет.json")
    assert set(config.hdrezka_categories) == {"animation", "films", "series", "cartoons", "show"}


def test_hdrezka_categories_from_file(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"hdrezka_categories": ["films", "series"]}), encoding="utf-8")
    assert load_config(path).hdrezka_categories == ["films", "series"]


def test_unknown_hdrezka_categories_dropped(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"hdrezka_categories": ["films", "чепуха"]}), encoding="utf-8")
    assert load_config(path).hdrezka_categories == ["films"]


def test_all_unknown_hdrezka_categories_fall_back_to_default(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"hdrezka_categories": ["чепуха"]}), encoding="utf-8")
    assert set(load_config(path).hdrezka_categories) == {"animation", "films", "series", "cartoons", "show"}


def test_hdrezka_categories_default_not_shared_between_instances():
    first = MultiConfig()
    second = MultiConfig()
    first.hdrezka_categories.append("чепуха")
    assert "чепуха" not in second.hdrezka_categories
```

- [ ] **Step 2: Обновить `anicli_multi/config.py`**

Добавить импорт и поле, расширить `load_config`:

```python
from .kinds import KNOWN_CATEGORIES
```

```python
DEFAULT_HDREZKA_CATEGORIES: list[str] = ["animation", "films", "series", "cartoons", "show"]
```

В `MultiConfig`:

```python
    hdrezka_categories: list[str] = field(default_factory=lambda: list(DEFAULT_HDREZKA_CATEGORIES))
```

В `load_config`, перед `return config`:

```python
    categories = raw.get("hdrezka_categories")
    if isinstance(categories, list):
        known = [str(c) for c in categories if str(c) in KNOWN_CATEGORIES]
        if known:
            config.hdrezka_categories = known
```

- [ ] **Step 3: Запустить тесты конфига**

Run: `python -m pytest tests/test_config.py -q`
Expected: PASS

- [ ] **Step 4: Написать падающий тест проверки совместимости**

Дописать в `tests/test_compat.py`:

```python
def test_hdrezka_override_is_supported_by_installed_anicli():
    from anicli_multi.compat import check_hdrezka_override

    problems = check_hdrezka_override()
    assert problems == [], "расширенный поиск hdrezka недоступен: " + "; ".join(problems)


def test_check_hdrezka_override_returns_list():
    from anicli_multi.compat import check_hdrezka_override

    assert isinstance(check_hdrezka_override(), list)
```

- [ ] **Step 5: Добавить проверку в `anicli_multi/compat.py`**

```python
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
```

- [ ] **Step 6: Запустить тесты совместимости**

Run: `python -m pytest tests/test_compat.py -q`
Expected: PASS

- [ ] **Step 7: Написать падающие тесты подключения**

Дописать в `tests/test_commands.py`:

```python
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


def test_startup_event_passes_categories_from_context():
    import asyncio

    from anicli_multi.commands import on_start_build_extractors

    app = FakeApp(["search", "ongoing", "history", "exit"])
    install(app, MultiConfig(sources=["hdrezka"], hdrezka_categories=["series"]))
    asyncio.run(on_start_build_extractors(app.context))
    assert app.context.data["multi_extractors"]["hdrezka"].categories == frozenset({"series"})
```

- [ ] **Step 8: Обновить `anicli_multi/commands.py`**

Добавить импорты:

```python
from .compat import check_hdrezka_override
from .hdrezka_all import HdrezkaAllExtractor
```

Добавить функцию перед `build_extractors`:

```python
def _instantiate(name: str, hdrezka_categories: Optional[Sequence[str]]) -> Optional[Any]:
    """Создать экстрактор источника. None — источник недоступен."""
    if name == "hdrezka":
        problems = check_hdrezka_override()
        if problems:
            CONSOLE.print(
                "[yellow]hdrezka: расширенный поиск недоступен (" + "; ".join(problems) + "), только аниме[/yellow]"
            )
        else:
            return HdrezkaAllExtractor(categories=hdrezka_categories)
    try:
        module = dynamic_load_extractor_module(name)
    except (NameError, ImportError):
        CONSOLE.print(f"[yellow]Источник {name} недоступен, пропущен[/yellow]")
        return None
    return module.Extractor()
```

В сигнатуру `build_extractors` добавить параметр и заменить создание экстрактора:

```python
def build_extractors(
    sources: Sequence[str],
    *,
    proxy: Optional[str] = None,
    headers: Optional[dict] = None,
    cookies: Optional[Any] = None,
    timeout: Optional[float] = None,
    hdrezka_categories: Optional[Sequence[str]] = None,
) -> dict[str, Any]:
```

Тело цикла заменить на:

```python
    extractors: dict[str, Any] = {}
    for name in sources:
        extractor = _instantiate(name, hdrezka_categories)
        if extractor is None:
            continue
        extractor.http = http
        extractor.http_async = http_async
        extractors[name] = extractor
    return extractors
```

В `on_start_build_extractors` пробросить категории:

```python
    ctx.data["multi_extractors"] = build_extractors(
        sources,
        proxy=ctx.data.get("proxy"),
        headers=ctx.data.get("headers"),
        cookies=ctx.data.get("cookies"),
        timeout=ctx.data.get("timeout"),
        hdrezka_categories=ctx.data.get("multi_hdrezka_categories"),
    )
```

В `install` положить категории в контекст, рядом с существующими строками:

```python
    app.context._data["multi_hdrezka_categories"] = list(config.hdrezka_categories)
```

- [ ] **Step 9: Запустить весь набор и линтеры**

Run: `python -m pytest -q && python -m ruff check . && python -m mypy anicli_multi`
Expected: всё зелёное.

- [ ] **Step 10: Коммит**

```bash
git add anicli_multi/config.py anicli_multi/compat.py anicli_multi/commands.py tests/
git commit -m "feat: подключить расширенный поиск hdrezka с настройкой категорий"
```

---

### Task 5: Сетевые тесты, документация, версия

**Files:**
- Modify: `tests/test_integration.py`
- Modify: `README.md`
- Modify: `pyproject.toml`
- Modify: `anicli_multi/__init__.py`

**Interfaces:**
- Consumes: всё предыдущее.
- Produces: версия `0.2.0`, готовый к сборке дистрибутив.

- [ ] **Step 1: Дописать сетевые тесты**

Дописать в `tests/test_integration.py`:

```python
async def test_real_search_finds_a_movie():
    extractors = build_extractors(DEFAULT_SOURCES)
    per_source, failures = await search_all(extractors, "интерстеллар", timeout=15)
    assert per_source, f"ни один источник не ответил: {failures}"

    groups = group_results(per_source, priority=DEFAULT_SOURCES)
    films = [g for g in groups if g.kind == "фильм"]
    assert films, f"фильм не найден, типы в выдаче: {sorted({g.kind for g in groups})}"


async def test_real_search_finds_a_series():
    extractors = build_extractors(DEFAULT_SOURCES)
    per_source, failures = await search_all(extractors, "во все тяжкие", timeout=15)
    assert per_source, f"ни один источник не ответил: {failures}"

    groups = group_results(per_source, priority=DEFAULT_SOURCES)
    series = [g for g in groups if g.kind == "сериал"]
    assert series, f"сериал не найден, типы в выдаче: {sorted({g.kind for g in groups})}"


async def test_anime_search_still_groups_across_sources():
    """Регрессия: добавление типа в ключ не должно разбить склейку аниме."""
    extractors = build_extractors(DEFAULT_SOURCES)
    per_source, _ = await search_all(extractors, "наруто", timeout=15)
    groups = group_results(per_source, priority=DEFAULT_SOURCES)

    multi = [g for g in groups if len(g.sources) > 1]
    assert multi, "ожидалась хотя бы одна группа с несколькими источниками"
```

- [ ] **Step 2: Запустить сетевые тесты**

Run: `python -m pytest -m network -q`
Expected: PASS. Если фильм не найден — проверить, что `hdrezka` в `DEFAULT_SOURCES` и что `check_hdrezka_override()` пуст.

- [ ] **Step 3: Обновить README**

В разделе про то, что делает инструмент, после примера с аниме добавить:

```markdown
Ищет не только аниме — фильмы, сериалы, мультфильмы и шоу тоже:

```
~ интерстеллар

  1  Интерстеллар [фильм] (hdrezka)
  2  Наука «Интерстеллар» [фильм] (hdrezka)
```

Тип показывается бейджем у всего, что не аниме.
```

В раздел «Конфиг» добавить поле и пояснение:

```markdown
`hdrezka_categories` задаёт, какие разделы каталога hdrezka искать. Значение
`["animation"]` возвращает прежнее поведение — только аниме.
```

В «Ограничения» добавить:

```markdown
- Фильмы, сериалы, мультфильмы и шоу приходят только с `hdrezka` — остальные источники
  аниме-только. Склеивать их между источниками нечего, и если hdrezka недоступен,
  кино не найдётся вовсе.
```

- [ ] **Step 4: Поднять версию до 0.2.0**

В `pyproject.toml`: `version = "0.2.0"`.
В `anicli_multi/__init__.py`: `__version__ = "0.2.0"`.

- [ ] **Step 5: Финальная проверка**

Run: `python -m pytest -q && python -m pytest -m network -q && python -m ruff check . && python -m mypy anicli_multi`
Expected: всё зелёное.

- [ ] **Step 6: Собрать дистрибутив**

Run: `uv build`
Expected: собраны `dist/anicli_multi-0.2.0-py3-none-any.whl` и `.tar.gz`.

- [ ] **Step 7: Коммит**

```bash
git add tests/test_integration.py README.md pyproject.toml anicli_multi/__init__.py
git commit -m "feat: сетевые тесты на кино, документация, версия 0.2.0"
```

---

## Self-Review

**Покрытие спеки:**

| Раздел спеки | Задача |
|---|---|
| §4 UX и бейджи | Task 2 |
| §5 kinds.py | Task 1 |
| §5 hdrezka_all.py | Task 3 |
| §5 подключение через реестр переопределений | Task 4 |
| §6 тип в ключе группировки | Task 2 |
| §7 конфиг hdrezka_categories | Task 4 |
| §8 устойчивость и откат | Task 4 |
| §9 тесты без сети | Task 1–4 |
| §9 тесты с сетью | Task 5 |
| §10 риски (документирование ограничения) | Task 5 |

Пробелов нет.

**Согласованность имён:** `resolve_kind(source, url)` (T1) вызывается в `group_results` как
`kind_resolver` с той же сигнатурой (T2); `category_from_url` (T1) используется в
`_to_results` (T3); `KNOWN_CATEGORIES` (T1) читается в `config.load_config` (T4) и в
`DEFAULT_CATEGORIES` (T3); `check_hdrezka_override()` объявлена в T4 и там же вызывается
из `_instantiate`; `HdrezkaAllExtractor(categories=...)` объявлен в T3 и создаётся в T4 с
тем же именем параметра; ключ контекста `multi_hdrezka_categories` пишется в `install` и
читается в `on_start_build_extractors` — обе правки в T4.

**Отклонение от спеки:** спека в §5 описывала подключение как словарь
`EXTRACTOR_OVERRIDES`. План использует функцию `_instantiate` с явной веткой по имени
источника: переопределение сейчас ровно одно, и словарь фабрик был бы обобщением без
второго пользователя. Поведение идентично.
