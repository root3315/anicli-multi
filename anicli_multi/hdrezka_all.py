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
        page = await UnfilteredPageSearch.async_fetch(self.http_async, query=query, headers=ANUBIS_BYPASS_HEADERS)
        return self._to_results(page.parse())
