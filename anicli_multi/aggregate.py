"""Параллельный опрос источников с индивидуальным таймаутом."""

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Optional

DEFAULT_TIMEOUT = 10.0


@dataclass(frozen=True)
class SourceFailure:
    """Источник не ответил: таймаут или исключение."""

    source: str
    reason: str


async def _search_one(
    source: str,
    extractor: Any,
    query: str,
    timeout: float,
) -> tuple[str, Optional[list[Any]], Optional[SourceFailure]]:
    try:
        results = await asyncio.wait_for(extractor.a_search(query), timeout=timeout)
    except asyncio.TimeoutError:
        return source, None, SourceFailure(source=source, reason=f"таймаут {timeout:g}с")
    except Exception as exc:  # noqa: BLE001 — падение источника не должно ронять поиск
        reason = str(exc).strip() or type(exc).__name__
        return source, None, SourceFailure(source=source, reason=reason)
    return source, list(results), None


async def search_all(
    extractors: dict[str, Any],
    query: str,
    timeout: float = DEFAULT_TIMEOUT,
) -> tuple[list[tuple[str, list[Any]]], list[SourceFailure]]:
    """Опросить все источники параллельно.

    Возвращает пары (источник, результаты) только для источников с непустой
    выдачей, и список отказов. Порядок соответствует порядку ключей extractors.
    Пустая выдача — не отказ.
    """
    if not extractors:
        return [], []

    names: Sequence[str] = list(extractors)
    outcomes = await asyncio.gather(*(_search_one(name, extractors[name], query, timeout) for name in names))

    per_source: list[tuple[str, list[Any]]] = []
    failures: list[SourceFailure] = []
    for source, results, failure in outcomes:
        if failure is not None:
            failures.append(failure)
        elif results:
            per_source.append((source, results))
    return per_source, failures
