# anicli-multi Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Инструмент `ani` — REPL поверх `anicli-ru`, который ищет аниме сразу по нескольким источникам, показывает одну строку на тайтл с перечнем источников и принимает голый текст как поисковый запрос.

**Architecture:** Отдельный дистрибутив `anicli-multi` зависит от `anicli-ru>=6.1,<7` и расширяет его штатными механизмами: свой FSM-маршрут наследованием от `BaseAnimeFSM`, свои команды через декоратор `@command`, обёртка публичного `CommandManager.execute` для голого текста. Точка входа делегирует разбор аргументов Typer-приложению upstream, поэтому прокси, куки и заголовки не дублируются.

**Tech Stack:** Python 3.9+, anicli-ru, anicli-api, prompt_toolkit, rich, typer, platformdirs, pytest, pytest-asyncio, ruff, mypy, hatchling.

## Global Constraints

- `requires-python = ">=3.9"` — совпадает с upstream. Никакого синтаксиса 3.10+ (`X | Y` в аннотациях, `match`). Использовать `typing.Optional`, `typing.List`, `typing.Dict`.
- Зависимость `anicli-ru>=6.1,<7` — верхняя граница обязательна, контракт FSM внутренний.
- Лицензия MIT. Атрибуция `anicli-ru` и `anicli-api` (обе MIT) в README и NOTICE.
- Конфиг в JSON, не TOML (`tomllib` только с 3.11).
- Имя дистрибутива `anicli-multi`, пакет `anicli_multi`, консольные команды `ani` и `anicli-multi`.
- Источники по умолчанию, в порядке приоритета: `animego`, `hdrezka`, `yummy-anime`, `anilibria`.
- Склейка результатов **только по точному совпадению нормализованного ключа**. Fuzzy-матчинг запрещён.
- Никаких изменений в файлах установленного `anicli-ru`.
- **Публикация в PyPI не выполняется.** Проект доводится до готовности, `twine upload` / `uv publish` не запускается.
- Сообщения пользователю в CLI — на русском.
- Рабочая директория: `C:\Users\sozda\Desktop\anicli`. Git-репозиторий уже инициализирован, ветка `main`.

**Отклонение от спеки (осознанное):** спека в §5 объединяла поиск и группировку в `aggregate.py`. План разносит их на `aggregate.py` (сеть, параллелизм, ошибки) и `grouping.py` (чистая логика склейки), потому что у них разная природа и разный способ тестирования — группировка тестируется без сети.

---

### Task 1: Каркас проекта и нормализация названий

**Files:**
- Create: `pyproject.toml`
- Create: `anicli_multi/__init__.py`
- Create: `anicli_multi/normalize.py`
- Create: `tests/__init__.py`
- Test: `tests/test_normalize.py`

**Interfaces:**
- Consumes: ничего
- Produces: `normalize_title(raw: str) -> str` — ключ группировки.

- [ ] **Step 1: Создать `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "anicli-multi"
version = "0.1.0"
description = "Мультиисточниковый поиск аниме поверх anicli-ru"
readme = "README.md"
requires-python = ">=3.9"
license = {text = "MIT"}
authors = [{name = "sozda"}]
keywords = ["anime", "cli", "anicli", "mpv"]
classifiers = [
    "Environment :: Console",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
]
dependencies = [
    "anicli-ru>=6.1,<7",
    "platformdirs>=3.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "ruff>=0.6",
    "mypy>=1.8",
]

[project.scripts]
ani = "anicli_multi.cli:main"
anicli-multi = "anicli_multi.cli:main"

[project.urls]
Source = "https://github.com/sozda/anicli-multi"

[tool.hatch.build.targets.wheel]
packages = ["anicli_multi"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
markers = ["network: требует доступа в интернет (не запускается по умолчанию)"]
addopts = "-m 'not network'"

[tool.ruff]
line-length = 120
target-version = "py39"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]

[tool.mypy]
python_version = "3.9"
ignore_missing_imports = true
```

- [ ] **Step 2: Создать пустые `anicli_multi/__init__.py` и `tests/__init__.py`**

`anicli_multi/__init__.py`:

```python
__version__ = "0.1.0"
```

`tests/__init__.py` — пустой файл.

- [ ] **Step 3: Написать падающие тесты нормализации**

Файл `tests/test_normalize.py`. Тесты закрывают главный риск проекта: разные тайтлы не должны склеиваться.

```python
import pytest

from anicli_multi.normalize import normalize_title


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Наруто", "наруто"),
        ("  Наруто  ", "наруто"),
        ("НАРУТО", "наруто"),
        ("Ёжик", "ежик"),
        ("Наруто / Naruto [1-220 из 220]", "наруто"),
        ("Наруто OVA-1 / Naruto OVA-1 [1 из 1]", "наруто ova 1"),
        ("Наруто: Ураганные хроники", "наруто ураганные хроники"),
        ("Наруто Ураганные хроники", "наруто ураганные хроники"),
        ("Наруто [OVA-8] / Пылающий Экзамен", "наруто ova 8"),
    ],
)
def test_normalize_title(raw, expected):
    assert normalize_title(raw) == expected


def test_same_title_different_sources_merge():
    """Одинаковый тайтл с разных источников даёт один ключ."""
    animevost = "Наруто / Naruto [1-220 из 220]"
    hdrezka = "Наруто "
    assert normalize_title(animevost) == normalize_title(hdrezka)


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("Наруто", "Наруто: Ураганные хроники"),
        ("Наруто [OVA-8] / Пылающий Экзамен", "Наруто [OVA-5] / Пересечение путей"),
        ("Наруто", "Боруто: Новое поколение Наруто"),
        ("Наруто OVA-1 / Naruto OVA-1 [1 из 1]", "Наруто OVA-2 / Naruto OVA-2 [1 из 1]"),
    ],
)
def test_different_titles_do_not_merge(left, right):
    """Главная защита от «каши»: разные тайтлы должны давать разные ключи."""
    assert normalize_title(left) != normalize_title(right)


def test_empty_and_garbage_input():
    assert normalize_title("") == ""
    assert normalize_title("   ") == ""
    assert normalize_title("!!!") == ""
```

- [ ] **Step 4: Запустить тесты — убедиться, что падают**

Run: `python -m pytest tests/test_normalize.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'anicli_multi.normalize'`

- [ ] **Step 5: Реализовать `anicli_multi/normalize.py`**

Порядок операций важен: сначала отбрасываем альтернативное название после `/`, затем убираем **только** технические счётчики серий в скобках (`[1-220 из 220]`), и лишь потом чистим пунктуацию. Содержимое скобок вида `[OVA-8]` сохраняется — иначе разные OVA склеятся в одну строку.

```python
"""Нормализация названий тайтлов для группировки между источниками."""

import re

# Счётчик серий: [1-220 из 220], [1 из 1], (12 of 12)
_EPISODE_COUNT_RE = re.compile(
    r"[\[\(]\s*\d+\s*[-–—]?\s*\d*\s*(?:из|of)\s*\d+\s*[\]\)]",
    re.IGNORECASE,
)
_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)
_SPACE_RE = re.compile(r"\s+")


def normalize_title(raw: str) -> str:
    """Привести название к ключу группировки.

    Разные написания одного тайтла должны давать одинаковый ключ, разные
    тайтлы — разный. При сомнении выбирается разделение, а не склейка.
    """
    text = raw.lower().replace("ё", "е")
    # альтернативное название после "/" отбрасываем: "Наруто / Naruto" -> "Наруто"
    text = text.split("/")[0]
    text = _EPISODE_COUNT_RE.sub(" ", text)
    text = _PUNCT_RE.sub(" ", text)
    return _SPACE_RE.sub(" ", text).strip()
```

- [ ] **Step 6: Запустить тесты — убедиться, что проходят**

Run: `python -m pytest tests/test_normalize.py -v`
Expected: PASS, все тесты зелёные.

- [ ] **Step 7: Создать venv и установить проект в dev-режиме**

Создать окружение:

```bash
uv venv --python 3.10
```

Активировать (PowerShell на Windows):

```bash
.venv\Scripts\Activate.ps1
```

На Linux и macOS вместо этого `source .venv/bin/activate`.

Установить:

```bash
uv pip install -e ".[dev]"
```

Все последующие команды `python -m pytest` / `ruff` / `mypy` в этом плане выполняются
**внутри активированного venv** — иначе они возьмут системный Python, где пакет не установлен.

Run: `python -c "import anicli_multi, anicli; print(anicli_multi.__version__, anicli.__version__)"`
Expected: печатаются две версии — значит и наш пакет, и anicli-ru видны из venv.

- [ ] **Step 8: Прогнать линтеры**

Run: `python -m ruff check . && python -m mypy anicli_multi`
Expected: без ошибок.

- [ ] **Step 9: Коммит**

```bash
git add pyproject.toml anicli_multi/ tests/
git commit -m "feat: каркас проекта и нормализация названий"
```

---

### Task 2: Группировка результатов по тайтлам

**Files:**
- Create: `anicli_multi/grouping.py`
- Test: `tests/test_grouping.py`

**Interfaces:**
- Consumes: `normalize_title(raw: str) -> str` из Task 1.
- Produces:
  - `TitleGroup` — датакласс с полями `key: str`, `title: str`, `entries: List[Tuple[str, Any]]`; свойство `sources: List[str]`; `__str__` возвращает строку для `render_table`.
  - `group_results(per_source: Sequence[Tuple[str, Sequence[Any]]], priority: Sequence[str]) -> List[TitleGroup]`.

`per_source` — список пар `(имя_источника, результаты_поиска)`. Каждый результат поиска — объект `anicli_api` с атрибутом `.title`.

- [ ] **Step 1: Написать падающие тесты**

Файл `tests/test_grouping.py`:

```python
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
```

- [ ] **Step 2: Запустить тесты — убедиться, что падают**

Run: `python -m pytest tests/test_grouping.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'anicli_multi.grouping'`

- [ ] **Step 3: Реализовать `anicli_multi/grouping.py`**

```python
"""Склейка результатов поиска разных источников в группы по одному тайтлу."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence, Tuple

from .normalize import normalize_title

# (имя источника, объект результата поиска)
Entry = Tuple[str, Any]


@dataclass
class TitleGroup:
    """Один тайтл, найденный на одном или нескольких источниках."""

    key: str
    title: str
    entries: List[Entry] = field(default_factory=list)

    @property
    def sources(self) -> List[str]:
        return [source for source, _ in self.entries]

    def __str__(self) -> str:
        # render_table из anicli-ru печатает str(result); rich-разметка тут допустима
        return f"{self.title} [dim]({', '.join(self.sources)})[/dim]"


def _priority_index(source: str, priority: Sequence[str]) -> int:
    """Позиция источника в приоритете; неизвестный источник уходит в конец."""
    try:
        return priority.index(source)
    except ValueError:
        return len(priority)


def group_results(
    per_source: Sequence[Tuple[str, Sequence[Any]]],
    priority: Sequence[str],
) -> List[TitleGroup]:
    """Сгруппировать результаты по нормализованному названию.

    Склейка только по точному совпадению ключа — см. спеку §6.
    Внутри группы источники упорядочены по приоритету, отображаемое название
    берётся у источника с наивысшим приоритетом.
    """
    groups: Dict[str, TitleGroup] = {}

    for source, results in per_source:
        for result in results:
            key = normalize_title(result.title)
            if not key:
                continue
            group = groups.get(key)
            if group is None:
                groups[key] = TitleGroup(key=key, title=result.title, entries=[(source, result)])
                continue
            # один источник на группу: дубли внутри источника отбрасываем
            if source in group.sources:
                continue
            group.entries.append((source, result))

    ordered: List[TitleGroup] = []
    for group in groups.values():
        group.entries.sort(key=lambda e: _priority_index(e[0], priority))
        best_source, best_result = group.entries[0]
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

- [ ] **Step 4: Запустить тесты — убедиться, что проходят**

Run: `python -m pytest tests/test_grouping.py -v`
Expected: PASS.

- [ ] **Step 5: Прогнать весь набор и линтеры**

Run: `python -m pytest -v && python -m ruff check . && python -m mypy anicli_multi`
Expected: всё зелёное.

- [ ] **Step 6: Коммит**

```bash
git add anicli_multi/grouping.py tests/test_grouping.py
git commit -m "feat: группировка результатов по нормализованному названию"
```

---

### Task 3: Параллельный поиск по источникам

**Files:**
- Create: `anicli_multi/aggregate.py`
- Test: `tests/test_aggregate.py`

**Interfaces:**
- Consumes: ничего из предыдущих задач.
- Produces:
  - `SourceFailure` — датакласс `source: str`, `reason: str`.
  - `async search_all(extractors: Dict[str, Any], query: str, timeout: float) -> Tuple[List[Tuple[str, List[Any]]], List[SourceFailure]]`.

`extractors` — словарь `{имя_источника: экземпляр Extractor}`. У экземпляра вызывается `await extractor.a_search(query)`. Порядок результата совпадает с порядком ключей `extractors`.

- [ ] **Step 1: Написать падающие тесты**

Файл `tests/test_aggregate.py`:

```python
import asyncio

import pytest

from anicli_multi.aggregate import SourceFailure, search_all


class FakeResult:
    def __init__(self, title: str):
        self.title = title


class FakeExtractor:
    def __init__(self, titles=None, *, delay=0.0, error=None):
        self._titles = titles or []
        self._delay = delay
        self._error = error

    async def a_search(self, query):
        if self._delay:
            await asyncio.sleep(self._delay)
        if self._error:
            raise self._error
        return [FakeResult(t) for t in self._titles]


async def test_collects_results_from_all_sources():
    extractors = {
        "animego": FakeExtractor(["Наруто"]),
        "hdrezka": FakeExtractor(["Наруто", "Боруто"]),
    }
    per_source, failures = await search_all(extractors, "наруто", timeout=5)
    assert failures == []
    assert [name for name, _ in per_source] == ["animego", "hdrezka"]
    assert len(dict(per_source)["hdrezka"]) == 2


async def test_slow_source_times_out_without_killing_others():
    extractors = {
        "animego": FakeExtractor(["Наруто"]),
        "hdrezka": FakeExtractor(["Боруто"], delay=5),
    }
    per_source, failures = await search_all(extractors, "наруто", timeout=0.1)
    assert dict(per_source).keys() == {"animego"}
    assert len(failures) == 1
    assert failures[0].source == "hdrezka"
    assert "таймаут" in failures[0].reason.lower()


async def test_failing_source_is_reported_not_raised():
    extractors = {
        "animego": FakeExtractor(["Наруто"]),
        "hdrezka": FakeExtractor(error=RuntimeError("500 Server Error")),
    }
    per_source, failures = await search_all(extractors, "наруто", timeout=5)
    assert dict(per_source).keys() == {"animego"}
    assert len(failures) == 1
    assert failures[0].source == "hdrezka"
    assert "500 Server Error" in failures[0].reason


async def test_all_sources_fail_returns_empty_without_raising():
    extractors = {
        "animego": FakeExtractor(error=RuntimeError("boom")),
        "hdrezka": FakeExtractor(error=RuntimeError("boom")),
    }
    per_source, failures = await search_all(extractors, "наруто", timeout=5)
    assert per_source == []
    assert len(failures) == 2


async def test_empty_result_is_not_a_failure():
    extractors = {"animego": FakeExtractor([])}
    per_source, failures = await search_all(extractors, "нет такого", timeout=5)
    assert per_source == []
    assert failures == []


async def test_searches_run_concurrently_not_sequentially():
    extractors = {
        "a": FakeExtractor(["x"], delay=0.2),
        "b": FakeExtractor(["y"], delay=0.2),
        "c": FakeExtractor(["z"], delay=0.2),
    }
    loop = asyncio.get_running_loop()
    started = loop.time()
    per_source, failures = await search_all(extractors, "q", timeout=5)
    elapsed = loop.time() - started
    assert len(per_source) == 3
    assert elapsed < 0.5, f"источники опрашивались последовательно: {elapsed:.2f}s"


def test_source_failure_fields():
    failure = SourceFailure(source="hdrezka", reason="таймаут")
    assert failure.source == "hdrezka"
    assert failure.reason == "таймаут"
```

- [ ] **Step 2: Запустить тесты — убедиться, что падают**

Run: `python -m pytest tests/test_aggregate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'anicli_multi.aggregate'`

- [ ] **Step 3: Реализовать `anicli_multi/aggregate.py`**

```python
"""Параллельный опрос источников с индивидуальным таймаутом."""

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

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
) -> Tuple[str, Optional[List[Any]], Optional[SourceFailure]]:
    try:
        results = await asyncio.wait_for(extractor.a_search(query), timeout=timeout)
    except asyncio.TimeoutError:
        return source, None, SourceFailure(source=source, reason=f"таймаут {timeout:g}с")
    except Exception as exc:  # noqa: BLE001 — падение источника не должно ронять поиск
        reason = str(exc).strip() or type(exc).__name__
        return source, None, SourceFailure(source=source, reason=reason)
    return source, list(results), None


async def search_all(
    extractors: Dict[str, Any],
    query: str,
    timeout: float = DEFAULT_TIMEOUT,
) -> Tuple[List[Tuple[str, List[Any]]], List[SourceFailure]]:
    """Опросить все источники параллельно.

    Возвращает пары (источник, результаты) только для источников с непустой
    выдачей, и список отказов. Порядок соответствует порядку ключей extractors.
    Пустая выдача — не отказ.
    """
    if not extractors:
        return [], []

    names: Sequence[str] = list(extractors)
    outcomes = await asyncio.gather(
        *(_search_one(name, extractors[name], query, timeout) for name in names)
    )

    per_source: List[Tuple[str, List[Any]]] = []
    failures: List[SourceFailure] = []
    for source, results, failure in outcomes:
        if failure is not None:
            failures.append(failure)
        elif results:
            per_source.append((source, results))
    return per_source, failures
```

- [ ] **Step 4: Запустить тесты — убедиться, что проходят**

Run: `python -m pytest tests/test_aggregate.py -v`
Expected: PASS.

- [ ] **Step 5: Коммит**

```bash
git add anicli_multi/aggregate.py tests/test_aggregate.py
git commit -m "feat: параллельный поиск по источникам с таймаутом и мягкой деградацией"
```

---

### Task 4: Конфиг

**Files:**
- Create: `anicli_multi/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: ничего.
- Produces:
  - `DEFAULT_SOURCES: List[str]` = `["animego", "hdrezka", "yummy-anime", "anilibria"]`
  - `MultiConfig` — датакласс: `sources: List[str]`, `timeout: float`, `bare_text_search: bool`.
  - `config_path() -> pathlib.Path`
  - `load_config(path: Optional[Path] = None) -> MultiConfig`
  - `save_config(config: MultiConfig, path: Optional[Path] = None) -> None`

- [ ] **Step 1: Написать падающие тесты**

Файл `tests/test_config.py`:

```python
import json

from anicli_multi.config import (
    DEFAULT_SOURCES,
    MultiConfig,
    config_path,
    load_config,
    save_config,
)


def test_defaults_when_file_missing(tmp_path):
    config = load_config(tmp_path / "нет.json")
    assert config.sources == DEFAULT_SOURCES
    assert config.timeout == 10.0
    assert config.bare_text_search is True


def test_default_sources_exact_order():
    assert DEFAULT_SOURCES == ["animego", "hdrezka", "yummy-anime", "anilibria"]


def test_roundtrip(tmp_path):
    path = tmp_path / "config.json"
    save_config(MultiConfig(sources=["animego"], timeout=3.5, bare_text_search=False), path)
    loaded = load_config(path)
    assert loaded.sources == ["animego"]
    assert loaded.timeout == 3.5
    assert loaded.bare_text_search is False


def test_partial_config_fills_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"timeout": 2}), encoding="utf-8")
    config = load_config(path)
    assert config.timeout == 2
    assert config.sources == DEFAULT_SOURCES


def test_broken_json_falls_back_to_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{ это не json", encoding="utf-8")
    config = load_config(path)
    assert config.sources == DEFAULT_SOURCES


def test_unknown_keys_ignored(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"такого_поля_нет": 1}), encoding="utf-8")
    assert load_config(path).sources == DEFAULT_SOURCES


def test_save_creates_parent_directory(tmp_path):
    path = tmp_path / "вложено" / "config.json"
    save_config(MultiConfig(), path)
    assert path.exists()


def test_config_path_mentions_app_name():
    assert "anicli-multi" in str(config_path())
```

- [ ] **Step 2: Запустить тесты — убедиться, что падают**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'anicli_multi.config'`

- [ ] **Step 3: Реализовать `anicli_multi/config.py`**

```python
"""Пользовательский конфиг в платформенной директории. Формат — JSON (см. спеку §8)."""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional

from platformdirs import user_config_dir

APP_NAME = "anicli-multi"

DEFAULT_SOURCES: List[str] = ["animego", "hdrezka", "yummy-anime", "anilibria"]
DEFAULT_TIMEOUT = 10.0


@dataclass
class MultiConfig:
    sources: List[str] = field(default_factory=lambda: list(DEFAULT_SOURCES))
    timeout: float = DEFAULT_TIMEOUT
    bare_text_search: bool = True


def config_path() -> Path:
    return Path(user_config_dir(APP_NAME, appauthor=False)) / "config.json"


def load_config(path: Optional[Path] = None) -> MultiConfig:
    """Прочитать конфиг. Отсутствие или поломка файла — не ошибка, берутся дефолты."""
    target = path or config_path()
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return MultiConfig()
    if not isinstance(raw, dict):
        return MultiConfig()

    config = MultiConfig()
    sources = raw.get("sources")
    if isinstance(sources, list) and sources:
        config.sources = [str(s) for s in sources]
    timeout = raw.get("timeout")
    if isinstance(timeout, (int, float)) and timeout > 0:
        config.timeout = float(timeout)
    bare = raw.get("bare_text_search")
    if isinstance(bare, bool):
        config.bare_text_search = bare
    return config


def save_config(config: MultiConfig, path: Optional[Path] = None) -> None:
    target = path or config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(asdict(config), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
```

- [ ] **Step 4: Запустить тесты — убедиться, что проходят**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS.

- [ ] **Step 5: Коммит**

```bash
git add anicli_multi/config.py tests/test_config.py
git commit -m "feat: конфиг в JSON с мягкой деградацией к дефолтам"
```

---

### Task 5: Проверка совместимости с anicli-ru

**Files:**
- Create: `anicli_multi/compat.py`
- Test: `tests/test_compat.py`

**Interfaces:**
- Consumes: ничего.
- Produces:
  - `REQUIRED_CONTEXT_KEYS: Tuple[str, ...]` — ключи контекста FSM, на которые мы опираемся.
  - `check_compat() -> List[str]` — список человекочитаемых проблем; пустой список означает совместимость.
  - `CompatError(RuntimeError)`
  - `assert_compat() -> None` — бросает `CompatError` с внятным текстом, если `check_compat()` непуст.

Это тот самый тест, который ловит поломку после обновления upstream (спека §9, §11).

- [ ] **Step 1: Написать падающие тесты**

Файл `tests/test_compat.py`:

```python
import pytest

from anicli_multi.compat import (
    REQUIRED_CONTEXT_KEYS,
    CompatError,
    assert_compat,
    check_compat,
)


def test_installed_anicli_is_compatible():
    """Smoke: фактически установленный anicli-ru предоставляет ожидаемый контракт."""
    problems = check_compat()
    assert problems == [], "контракт anicli-ru изменился: " + "; ".join(problems)


def test_assert_compat_passes_on_current_install():
    assert_compat()


def test_required_context_keys_are_declared():
    for key in ("results", "anime", "episodes", "extractor_name", "result_num"):
        assert key in REQUIRED_CONTEXT_KEYS


def test_compat_error_is_runtime_error():
    assert issubclass(CompatError, RuntimeError)


def test_assert_compat_raises_when_problems(monkeypatch):
    monkeypatch.setattr("anicli_multi.compat.check_compat", lambda: ["всё сломалось"])
    with pytest.raises(CompatError) as exc:
        assert_compat()
    assert "всё сломалось" in str(exc.value)
```

- [ ] **Step 2: Запустить тесты — убедиться, что падают**

Run: `python -m pytest tests/test_compat.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'anicli_multi.compat'`

- [ ] **Step 3: Реализовать `anicli_multi/compat.py`**

```python
"""Проверка, что установленный anicli-ru предоставляет нужный нам контракт.

Мы наследуемся от внутреннего FSM anicli-ru и опираемся на набор ключей его
контекста. Это единственная существенная связанность проекта (спека §5).
Здесь она проверяется явно, чтобы после обновления upstream пользователь получил
внятное сообщение вместо трейсбэка.
"""

from typing import List, Tuple

REQUIRED_CONTEXT_KEYS: Tuple[str, ...] = (
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


class CompatError(RuntimeError):
    """Установленная версия anicli-ru несовместима с anicli-multi."""


def check_compat() -> List[str]:
    """Вернуть список проблем совместимости. Пустой список — всё в порядке."""
    problems: List[str] = []

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
        if getattr(BaseAnimeFSM, state, None) is None:
            problems.append(f"у BaseAnimeFSM нет состояния {state}")

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
        "anicli-multi несовместим с установленной версией anicli-ru "
        f"({version}).\n"
        + "\n".join(f"  - {p}" for p in problems)
        + "\nПереустановите совместимую версию: pip install 'anicli-ru>=6.1,<7'"
    )
    raise CompatError(msg)
```

- [ ] **Step 4: Запустить тесты — убедиться, что проходят**

Run: `python -m pytest tests/test_compat.py -v`
Expected: PASS. Если `test_installed_anicli_is_compatible` падает — контракт upstream отличается от ожидаемого, и дальнейшие задачи опираются на неверные допущения. В этом случае остановиться и сверить `REQUIRED_CONTEXT_KEYS` с `anicli/cli/contexts.py`.

- [ ] **Step 5: Коммит**

```bash
git add anicli_multi/compat.py tests/test_compat.py
git commit -m "feat: проверка совместимости контракта anicli-ru"
```

---

### Task 6: FSM мультипоиска

**Files:**
- Create: `anicli_multi/fsm.py`
- Test: `tests/test_fsm.py`

**Interfaces:**
- Consumes: `TitleGroup` из Task 2.
- Produces:
  - `MultiSearchFSM` — FSMRoute с ключом `"multi"`, состояния `step_1`, `step_1_source`; `step_2`, `step_3`, `step_3_batched` наследуются от `BaseAnimeFSM`.
  - `SourceRow` — обёртка над именем источника, у которой `__str__` возвращает имя (нужна для `render_table`).

**Контекст FSM `"multi"`** (передаётся из Task 7): ключи `Context` из anicli-ru плюс `groups: List[TitleGroup]`, `group_entries: List[Tuple[str, Any]]`, `query: str`.

- [ ] **Step 1: Написать падающие тесты**

Файл `tests/test_fsm.py`. Тестируем чистую логику разрешения группы в источник — сетевые вызовы и prompt_toolkit не поднимаем.

```python
import pytest

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
```

- [ ] **Step 2: Запустить тесты — убедиться, что падают**

Run: `python -m pytest tests/test_fsm.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'anicli_multi.fsm'`

- [ ] **Step 3: Реализовать `anicli_multi/fsm.py`**

`@fsm_route` возвращает объект `FSMRoute` с атрибутами `key`, `states`, `initial_state`, `fsm_class` — поэтому `MultiSearchFSM` после декорирования это `FSMRoute`, а не класс. Начальное состояние выбирается первым по `dir(cls)` в алфавитном порядке: `step_1` < `step_1_source` < `step_2`, так что `step_1` становится начальным.

```python
"""FSM мультипоиска: свой выбор тайтла и источника, дальше — штатные шаги anicli-ru."""

from typing import Any, List, Optional, Sequence, Tuple, Union

from anicli.cli.contexts import Context
from anicli.cli.fsm import BaseAnimeFSM
from anicli.cli.helpers.render import render_table
from anicli.cli.helpers.validator import validate_prompt_index
from anicli.cli.ptk_lib import fsm_route, fsm_state

from .grouping import TitleGroup


class MultiContext(Context, total=False):
    """Контекст FSM мультипоиска: контракт anicli-ru плюс наши поля."""

    query: str
    groups: List[TitleGroup]
    group_entries: List[Tuple[str, Any]]


class SourceRow:
    """Строка таблицы выбора источника. render_table печатает str(элемент)."""

    __slots__ = ("name",)

    def __init__(self, name: str):
        self.name = name

    def __str__(self) -> str:
        return self.name


def resolve_entry(group: TitleGroup) -> Optional[Tuple[str, Any]]:
    """Вернуть единственную пару (источник, результат) или None, если выбор неоднозначен."""
    if len(group.entries) == 1:
        return group.entries[0]
    return None


@fsm_route("multi")
class MultiSearchFSM(BaseAnimeFSM[MultiContext]):
    ROUTE_NAME = "multi"

    def _get_user_dynamic_validator(self, state_name: str, user_input: str) -> Union[bool, str]:
        if state_name == "step_1":
            return validate_prompt_index(self.ctx.get("groups", []), user_input)
        if state_name == "step_1_source":
            return validate_prompt_index(self.ctx.get("group_entries", []), user_input)
        return super()._get_user_dynamic_validator(state_name, user_input)

    def _get_user_dynamic_completions(
        self, state_name: str, current_text: str
    ) -> Union[List[str], List[Tuple[str, str]]]:
        if state_name == "step_1":
            groups: Sequence[TitleGroup] = self.ctx.get("groups", [])
            return [(str(i), g.title) for i, g in enumerate(groups, 1)]
        if state_name == "step_1_source":
            entries = self.ctx.get("group_entries", [])
            return [(str(i), source) for i, (source, _) in enumerate(entries, 1)]
        return super()._get_user_dynamic_completions(state_name, current_text)

    @fsm_state("step_1", prompt_message="~/{ROUTE_NAME} ")
    async def step_1(self, user_input: str):
        """Выбран тайтл. Один источник — идём дальше, несколько — спрашиваем источник."""
        groups: List[TitleGroup] = self.ctx["groups"]  # type: ignore[typeddict-item]
        group = groups[int(user_input) - 1]

        entry = resolve_entry(group)
        if entry is not None:
            await self._open_anime(*entry)
            return

        self.ctx["group_entries"] = group.entries  # type: ignore[typeddict-unknown-key]
        render_table(group.title, [SourceRow(source) for source, _ in group.entries])
        await self.next_state("step_1_source")

    @fsm_state("step_1_source", prompt_message="~/{ROUTE_NAME}/source ")
    async def step_1_source(self, user_input: str):
        """Выбран источник для тайтла, найденного на нескольких сайтах."""
        entries: List[Tuple[str, Any]] = self.ctx["group_entries"]  # type: ignore[typeddict-item]
        source, result = entries[int(user_input) - 1]
        await self._open_anime(source, result)

    async def _open_anime(self, source: str, result: Any) -> None:
        """Подготовить контекст под наследуемый step_2 и перейти в него.

        extractor_name проставляется здесь, после выбора источника — благодаря
        этому история просмотров пишется с корректным источником (спека §5).
        """
        self.ctx["extractor_name"] = source
        self.ctx["results"] = [result]
        self.ctx["result_num"] = 0

        anime = await result.a_get_anime()
        episodes = await anime.a_get_episodes()
        self.ctx["anime"] = anime
        self.ctx["episodes"] = episodes

        self.set_prompt_var("result", anime.title)
        render_table(anime.title, episodes)
        await self.next_state("step_2")
```

- [ ] **Step 4: Запустить тесты — убедиться, что проходят**

Run: `python -m pytest tests/test_fsm.py -v`
Expected: PASS.

- [ ] **Step 5: Коммит**

```bash
git add anicli_multi/fsm.py tests/test_fsm.py
git commit -m "feat: FSM мультипоиска с выбором тайтла и источника"
```

---

### Task 7: Команды, алиасы и голый текст как поиск

**Files:**
- Create: `anicli_multi/commands.py`
- Test: `tests/test_commands.py`

**Interfaces:**
- Consumes: `search_all`, `SourceFailure` (Task 3); `group_results` (Task 2); `MultiSearchFSM` (Task 6); `load_config`, `MultiConfig` (Task 4).
- Produces:
  - `build_extractors(sources: Sequence[str]) -> Dict[str, Any]`
  - `multi_search_command` — CommandRoute с ключом `"search"` (переопределяет штатный).
  - `install_bare_text_search(app: Any) -> None` — оборачивает `app.command_manager.execute`.
  - `install(app: Any, config: MultiConfig) -> None` — регистрирует всё на переданном APP; идемпотентна.

- [ ] **Step 1: Написать падающие тесты**

Файл `tests/test_commands.py`:

```python
import pytest

from anicli_multi.commands import build_extractors, install_bare_text_search


class FakeRoute:
    def __init__(self, key):
        self.key = key


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


class FakeApp:
    def __init__(self, keys):
        self.command_manager = FakeCommandManager(keys)
        self.fsm_manager = FakeFsmManager()


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


def test_install_is_idempotent():
    """Повторный install() не должен падать на уже зарегистрированных алиасах."""
    from anicli_multi.commands import install
    from anicli_multi.config import MultiConfig

    app = FakeApp(["search", "ongoing", "history", "exit"])
    config = MultiConfig()
    install(app, config)
    install(app, config)  # не должно бросить ValueError

    assert app.command_manager.get_command("s") is not None
    assert app.command_manager.get_command("o") is not None


def test_install_registers_multi_fsm():
    from anicli_multi.commands import install
    from anicli_multi.config import MultiConfig

    app = FakeApp(["search", "ongoing", "history", "exit"])
    install(app, MultiConfig())
    assert [r.key for r in app.fsm_manager.registered] == ["multi"]


def test_install_respects_bare_text_search_disabled():
    from anicli_multi.commands import install
    from anicli_multi.config import MultiConfig

    app = FakeApp(["search", "ongoing", "history", "exit"])
    original = app.command_manager.execute
    install(app, MultiConfig(bare_text_search=False))
    assert app.command_manager.execute is original
```

- [ ] **Step 2: Запустить тесты — убедиться, что падают**

Run: `python -m pytest tests/test_commands.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'anicli_multi.commands'`

- [ ] **Step 3: Реализовать `anicli_multi/commands.py`**

Алиасы `o`, `h`, `q` регистрируются отдельными командами-делегатами, а не правкой существующих маршрутов: `CommandManager.register` бросает `ValueError`, если алиас уже занят, а делегат использует только публичный `execute`.

```python
"""Команды поверх APP из anicli-ru: мультипоиск, алиасы, голый текст как запрос."""

from typing import Any, Dict, List, Sequence, Tuple

from anicli.cli.contexts import AnicliContext
from anicli.cli.helpers.render import render_table
from anicli.cli.ptk_lib import CommandContext, command
from anicli.common.extractors import dynamic_load_extractor_module
from rich import get_console

from .aggregate import SourceFailure, search_all
from .config import MultiConfig
from .fsm import MultiSearchFSM
from .grouping import group_results

CONSOLE = get_console()


def build_extractors(sources: Sequence[str]) -> Dict[str, Any]:
    """Создать по экземпляру Extractor на источник. Неизвестные источники пропускаются."""
    extractors: Dict[str, Any] = {}
    for name in sources:
        try:
            module = dynamic_load_extractor_module(name)
        except (NameError, ImportError):
            CONSOLE.print(f"[yellow]Источник {name} недоступен, пропущен[/yellow]")
            continue
        extractors[name] = module.Extractor()
    return extractors


def _print_failures(failures: Sequence[SourceFailure]) -> None:
    for failure in failures:
        CONSOLE.print(f"[yellow]⚠ {failure.source}: {failure.reason}[/yellow]")


@command("search", help="поиск по нескольким источникам сразу")
async def multi_search_command(query: str, ctx: CommandContext[AnicliContext]):
    query = query.strip()
    if not query:
        CONSOLE.print("[yellow]Нужен запрос: просто наберите название[/yellow]")
        return

    extractors: Dict[str, Any] = ctx.data.get("multi_extractors") or {}
    timeout: float = ctx.data.get("multi_timeout", 10.0)
    if not extractors:
        CONSOLE.print("[red]Ни один источник не доступен[/red]")
        return

    with CONSOLE.status(f"Ищу «{query}» на {len(extractors)} источниках…"):
        per_source, failures = await search_all(extractors, query, timeout=timeout)

    groups = group_results(per_source, priority=list(extractors))
    if not groups:
        CONSOLE.print("Ничего не найдено")
        _print_failures(failures)
        return

    render_table(f"Результаты: {query}", groups)
    _print_failures(failures)

    await ctx.app.start_fsm(
        "multi",
        "step_1",
        context={
            "query": query,
            "groups": groups,
            "extractor_name": groups[0].entries[0][0],
            "default_quality": ctx.data.get("quality", 2060),
            "mpv_opts": ctx.data.get("mpv_opts", ""),
            "m3u_size": ctx.data.get("m3u_size", 6),
        },
    )


def _make_alias(alias: str, target: str, help_text: str):
    @command(alias, help=help_text)
    async def _delegate(args: str, ctx: CommandContext[AnicliContext]):
        await ctx.app.command_manager.execute(target, args)

    return _delegate


def install_bare_text_search(app: Any) -> None:
    """Неизвестная команда трактуется как поисковый запрос.

    Оборачивается публичный CommandManager.execute; Application._handle_global_input
    вызывает его через self.command_manager, поэтому подмена атрибута экземпляра
    перехватывает весь ввод главного меню.
    """
    manager = app.command_manager
    original_execute = manager.execute

    async def execute(cmd_key: str, raw_args: str) -> None:
        if manager.get_command(cmd_key) is None:
            query = f"{cmd_key} {raw_args}".strip()
            await original_execute("search", query)
            return
        await original_execute(cmd_key, raw_args)

    manager.execute = execute


def install(app: Any, config: MultiConfig) -> None:
    """Зарегистрировать всё на APP из anicli-ru."""
    # переопределяет штатный search: register перезаписывает маршрут по тому же ключу
    app.command_manager.register(multi_search_command)
    app.fsm_manager.register(MultiSearchFSM)

    # Алиасы — отдельные команды-делегаты, а не поле aliases= на маршруте.
    # register() бросает ValueError, если alias уже занят, поэтому повторный
    # вызов install() ронял бы приложение. Делегаты идемпотентны за счёт проверки.
    aliases: List[Tuple[str, str, str]] = [
        ("s", "search", "то же, что search"),
        ("o", "ongoing", "то же, что ongoing"),
        ("h", "history", "то же, что history"),
        ("q", "exit", "то же, что exit"),
    ]
    for alias, target, help_text in aliases:
        if app.command_manager.get_command(alias) is None:
            app.command_manager.register(_make_alias(alias, target, help_text))

    if config.bare_text_search:
        install_bare_text_search(app)
```

- [ ] **Step 4: Запустить тесты — убедиться, что проходят**

Run: `python -m pytest tests/test_commands.py -v`
Expected: PASS.

- [ ] **Step 5: Коммит**

```bash
git add anicli_multi/commands.py tests/test_commands.py
git commit -m "feat: мультипоиск как команда search, алиасы и голый текст как запрос"
```

---

### Task 8: Точка входа `ani`

**Files:**
- Create: `anicli_multi/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `load_config` (Task 4), `assert_compat` (Task 5), `install`, `build_extractors` (Task 7).
- Produces:
  - `split_own_args(argv: List[str]) -> Tuple[Optional[str], List[str]]` — вынимает `--sources animego,hdrezka` из argv.
  - `build_upstream_argv(argv: List[str], primary: str) -> List[str]` — превращает аргументы `ani` в аргументы `anicli-ru cli`.
  - `main() -> None` — console_script.

`ani` делегирует разбор аргументов Typer-приложению `anicli.main.app`, поэтому `--proxy`, `--cookies`, `-H`, `-q` и прочее работают без дублирования кода.

- [ ] **Step 1: Написать падающие тесты**

Файл `tests/test_cli.py`:

```python
from anicli_multi.cli import build_upstream_argv, split_own_args


def test_split_own_args_extracts_sources():
    sources, rest = split_own_args(["--sources", "animego,hdrezka", "наруто"])
    assert sources == "animego,hdrezka"
    assert rest == ["наруто"]


def test_split_own_args_supports_equals_form():
    sources, rest = split_own_args(["--sources=animego", "наруто"])
    assert sources == "animego"
    assert rest == ["наруто"]


def test_split_own_args_without_flag():
    sources, rest = split_own_args(["наруто"])
    assert sources is None
    assert rest == ["наруто"]


def test_build_upstream_argv_no_args_starts_repl():
    assert build_upstream_argv([], "animego") == ["cli", "-s", "animego"]


def test_build_upstream_argv_bare_query_becomes_search():
    argv = build_upstream_argv(["наруто"], "animego")
    assert argv == ["cli", "-s", "animego", "--search", "наруто"]


def test_build_upstream_argv_multiword_query_joined():
    argv = build_upstream_argv(["атака", "титанов"], "animego")
    assert argv == ["cli", "-s", "animego", "--search", "атака титанов"]


def test_build_upstream_argv_passes_through_flags():
    argv = build_upstream_argv(["-q", "1080", "--proxy", "http://x"], "animego")
    assert argv == ["cli", "-s", "animego", "-q", "1080", "--proxy", "http://x"]


def test_build_upstream_argv_flags_with_query():
    argv = build_upstream_argv(["-q", "1080", "наруто"], "animego")
    assert argv[:3] == ["cli", "-s", "animego"]
    assert "--search" in argv
    assert argv[-1] == "наруто"


def test_boolean_flag_does_not_swallow_query():
    """`ani --ongoing` — булев флаг, следующее слово это запрос, а не его значение."""
    argv = build_upstream_argv(["--ongoing"], "animego")
    assert argv == ["cli", "-s", "animego", "--ongoing"]


def test_boolean_flag_followed_by_word_keeps_word_as_query():
    argv = build_upstream_argv(["--ongoing", "наруто"], "animego")
    assert argv == ["cli", "-s", "animego", "--ongoing", "--search", "наруто"]


def test_build_upstream_argv_respects_explicit_source():
    argv = build_upstream_argv(["-s", "hdrezka"], "animego")
    assert argv.count("-s") == 1
    assert "hdrezka" in argv
    assert "animego" not in argv
```

- [ ] **Step 2: Запустить тесты — убедиться, что падают**

Run: `python -m pytest tests/test_cli.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'anicli_multi.cli'`

- [ ] **Step 3: Реализовать `anicli_multi/cli.py`**

```python
"""Точка входа `ani`: настраивает APP из anicli-ru и делегирует ему разбор аргументов."""

import sys
from typing import List, Optional, Tuple

from .compat import CompatError, assert_compat
from .config import MultiConfig, load_config

_SOURCES_FLAG = "--sources"

# Флаги upstream, не принимающие значения. Без этого списка `ani --ongoing наруто`
# проглотил бы «наруто» как значение --ongoing вместо поискового запроса.
_BOOLEAN_FLAGS = frozenset({"--ongoing", "--force", "--help", "--install-completion", "--show-completion"})


def split_own_args(argv: List[str]) -> Tuple[Optional[str], List[str]]:
    """Вынуть наш собственный --sources из argv; остальное уходит upstream как есть."""
    sources: Optional[str] = None
    rest: List[str] = []
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == _SOURCES_FLAG and index + 1 < len(argv):
            sources = argv[index + 1]
            index += 2
            continue
        if arg.startswith(_SOURCES_FLAG + "="):
            sources = arg.split("=", 1)[1]
            index += 1
            continue
        rest.append(arg)
        index += 1
    return sources, rest


def build_upstream_argv(argv: List[str], primary: str) -> List[str]:
    """Собрать аргументы для `anicli-ru cli`.

    Позиционные слова склеиваются в один поисковый запрос и уходят в --search.
    Явный -s/--source пользователя имеет приоритет над источником по умолчанию.
    """
    flags: List[str] = []
    words: List[str] = []
    index = 0
    has_explicit_source = False

    while index < len(argv):
        arg = argv[index]
        if arg.startswith("-"):
            if arg in ("-s", "--source") or arg.startswith("--source="):
                has_explicit_source = True
            flags.append(arg)
            takes_value = arg not in _BOOLEAN_FLAGS and "=" not in arg
            # значение следующим токеном: пробрасываем, не считая его запросом
            if takes_value and index + 1 < len(argv) and not argv[index + 1].startswith("-"):
                flags.append(argv[index + 1])
                index += 2
                continue
            index += 1
            continue
        words.append(arg)
        index += 1

    result = ["cli"]
    if not has_explicit_source:
        result += ["-s", primary]
    result += flags
    if words:
        result += ["--search", " ".join(words)]
    return result


def main() -> None:
    try:
        assert_compat()
    except CompatError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc

    from anicli.cli.main import APP
    from anicli.main import app as upstream_app

    from .commands import build_extractors, install

    raw_sources, argv = split_own_args(sys.argv[1:])
    config: MultiConfig = load_config()
    if raw_sources:
        config.sources = [s.strip() for s in raw_sources.split(",") if s.strip()]

    install(APP, config)

    extractors = build_extractors(config.sources)
    APP.context._data["multi_extractors"] = extractors
    APP.context._data["multi_timeout"] = config.timeout

    primary = config.sources[0] if config.sources else "animego"
    upstream_app(args=build_upstream_argv(argv, primary), prog_name="ani")
```

- [ ] **Step 4: Запустить тесты — убедиться, что проходят**

Run: `python -m pytest tests/test_cli.py -v`
Expected: PASS.

- [ ] **Step 5: Проверить, что Typer-приложение вызывается программно**

`upstream_app(args=..., prog_name=...)` — единственное место, где мы полагаемся на поведение Typer/Click при программном вызове. Проверить отдельно:

Run: `python -c "from anicli.main import app; app(args=['version'], prog_name='ani', standalone_mode=False)"`
Expected: печатается панель с версиями, без трейсбэка.

Если вызов падает — заменить в `main()` на `upstream_app(args=..., prog_name="ani", standalone_mode=True)` и повторить проверку.

- [ ] **Step 6: Живая проверка на реальном поиске**

Run: `ani наруто`
Expected: таблица с одной строкой на тайтл и перечнем источников в скобках; выбор строки ведёт к выбору источника либо сразу к списку серий.

Затем в REPL проверить голый текст:

Run (внутри REPL): `боруто`
Expected: запускается поиск, не «Unknown command».

- [ ] **Step 7: Коммит**

```bash
git add anicli_multi/cli.py tests/test_cli.py
git commit -m "feat: точка входа ani с делегированием аргументов upstream"
```

---

### Task 9: Документация, интеграционный тест и CI

**Files:**
- Create: `README.md`
- Create: `NOTICE`
- Create: `LICENSE`
- Create: `tests/test_integration.py`
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: всё предыдущее.
- Produces: готовый к публикации дистрибутив (публикация не выполняется).

- [ ] **Step 1: Написать интеграционный тест с сетью**

Файл `tests/test_integration.py`. Помечен `network`, из обычного прогона исключён через `addopts` в `pyproject.toml`.

```python
import pytest

from anicli_multi.aggregate import search_all
from anicli_multi.commands import build_extractors
from anicli_multi.config import DEFAULT_SOURCES
from anicli_multi.grouping import group_results

pytestmark = pytest.mark.network


async def test_real_search_returns_grouped_results():
    extractors = build_extractors(DEFAULT_SOURCES)
    per_source, failures = await search_all(extractors, "наруто", timeout=15)
    assert per_source, f"ни один источник не ответил: {failures}"

    groups = group_results(per_source, priority=DEFAULT_SOURCES)
    assert groups

    keys = [g.key for g in groups]
    assert len(keys) == len(set(keys)), "в выдаче есть дубли групп"


async def test_multi_source_title_is_grouped_once():
    """«Наруто» есть минимум на двух источниках — должна быть одна строка."""
    extractors = build_extractors(DEFAULT_SOURCES)
    per_source, _ = await search_all(extractors, "наруто", timeout=15)
    groups = group_results(per_source, priority=DEFAULT_SOURCES)

    multi = [g for g in groups if len(g.sources) > 1]
    assert multi, "ожидалась хотя бы одна группа с несколькими источниками"
    for group in multi:
        assert len(group.sources) == len(set(group.sources))
```

- [ ] **Step 2: Запустить интеграционный тест явно**

Run: `python -m pytest tests/test_integration.py -m network -v`
Expected: PASS. Если падает по сети — это не повод менять код группировки; перепроверить доступность источников.

- [ ] **Step 3: Убедиться, что обычный прогон сеть не трогает**

Run: `python -m pytest -v`
Expected: тесты из `test_integration.py` пропущены (deselected), остальные проходят.

- [ ] **Step 4: Создать `LICENSE` (MIT) и `NOTICE`**

`LICENSE` — стандартный текст MIT, правообладатель `sozda`, год 2026.

`NOTICE`:

```
anicli-multi

Этот проект построен поверх следующих проектов, распространяемых по лицензии MIT:

  anicli-ru   — https://github.com/vypivshiy/ani-cli-ru
  anicli-api  — https://github.com/vypivshiy/anicli-api

Copyright (c) vypivshiy

Вся логика получения данных с источников и воспроизведения видео принадлежит
этим проектам. anicli-multi добавляет поверх них поиск по нескольким источникам
одновременно и группировку результатов.
```

- [ ] **Step 5: Написать `README.md`**

```markdown
# anicli-multi

Поиск аниме сразу по нескольким источникам поверх [anicli-ru](https://github.com/vypivshiy/ani-cli-ru).

Обычный `anicli-ru` ищет в одном источнике, выбранном при запуске. Если тайтла там нет,
приходится перезапускаться с другим `-s`. `anicli-multi` опрашивает несколько источников
параллельно и показывает **одну строку на тайтл** с пометкой, где он доступен.

## Установка

Нужен [mpv](https://mpv.io/) в PATH и Python 3.9+.

```
pipx install anicli-multi
```

или

```
uv tool install anicli-multi
```

## Использование

```
ani                      запустить REPL
ani наруто               запустить и сразу искать
ani --sources animego,hdrezka
```

В REPL достаточно набрать название — слово `search` не нужно:

```
~ наруто

  1  Наруто: Ураганные хроники (animego, hdrezka, anilibria)
  2  Боруто: Новое поколение Наруто (animego, hdrezka)

~/multi 1
```

Команды: `s`/`search`, `o`/`ongoing`, `h`/`history`, `config`, `help`, `q`/`exit`.

## Конфиг

`%APPDATA%\anicli-multi\config.json` на Windows, `~/.config/anicli-multi/config.json` на Linux:

```json
{
  "sources": ["animego", "hdrezka", "yummy-anime", "anilibria"],
  "timeout": 10.0,
  "bare_text_search": true
}
```

`bare_text_search: false` вернёт строгий режим, где голый текст даёт «Unknown command».

## Ограничения

- Тайтлы склеиваются только при точном совпадении названия после нормализации.
  Один тайтл под русским и ромадзи-названием на разных источниках останется двумя строками.
  Это осознанный размен: fuzzy-матчинг склеивал бы разные тайтлы.
- Опечатка в команде (`sarch наруто`) уйдёт в поиск. Отключается `bare_text_search: false`.

## Лицензия

MIT. См. `NOTICE` — проект построен на `anicli-ru` и `anicli-api` (обе MIT).
```

- [ ] **Step 6: Создать `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest]
        python-version: ["3.9", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install
        run: pip install -e ".[dev]"
      - name: Lint
        run: python -m ruff check .
      - name: Types
        run: python -m mypy anicli_multi
      - name: Tests
        run: python -m pytest -v
```

Матрица 3.9 и 3.13 — нижняя и верхняя граница поддержки; промежуточные версии не дают
дополнительного сигнала при таком объёме кода.

- [ ] **Step 7: Собрать дистрибутив и проверить его**

```bash
uv build
```

Run: `python -m pip install --force-reinstall dist/anicli_multi-0.1.0-py3-none-any.whl && ani --help`
Expected: собираются `.whl` и `.tar.gz`, установка проходит, `ani --help` печатает справку upstream.

- [ ] **Step 8: Финальный прогон и коммит**

Run: `python -m pytest -v && python -m ruff check . && python -m mypy anicli_multi`
Expected: всё зелёное.

```bash
git add README.md NOTICE LICENSE tests/test_integration.py .github/
git commit -m "docs: README, лицензия, атрибуция; интеграционный тест и CI"
```

- [ ] **Step 9: Остановиться**

Публикация в PyPI **не выполняется**. Сообщить владельцу, что дистрибутив собран и готов,
и что имя `anicli-multi` на PyPI свободно, но занимать его — его решение.

---

## Self-Review

**Покрытие спеки:**

| Раздел спеки | Задача |
|---|---|
| §2.1 поиск по нескольким источникам | Task 3 |
| §2.2 одна строка на тайтл | Task 2 |
| §2.3 голый текст как запрос | Task 7 |
| §2.4 установка на Windows/Linux/macOS | Task 1 (pyproject), Task 9 (CI, сборка) |
| §4 UX, алиасы, запуск | Task 7, Task 8 |
| §5 архитектура и модули | Task 1–8 |
| §6 нормализация и группировка | Task 1, Task 2 |
| §7 источники по умолчанию | Task 4 |
| §8 конфиг | Task 4 |
| §9 ошибки и устойчивость | Task 3 (отказы источников), Task 5 (совместимость) |
| §10 упаковка | Task 1, Task 9 |
| §11 тесты | во всех задачах, интеграционные — Task 9 |

Пробелов не осталось.

**Согласованность имён между задачами:** `normalize_title` (T1) → используется в `grouping.py` (T2);
`TitleGroup.entries` (T2) → читается в `fsm.py` (T6) и `commands.py` (T7); `search_all` возвращает
`Tuple[List[Tuple[str, List[Any]]], List[SourceFailure]]` (T3) → `group_results` принимает ровно
`Sequence[Tuple[str, Sequence[Any]]]` (T2), совпадает; `MultiSearchFSM` регистрируется как FSMRoute
с ключом `"multi"` (T6) → `start_fsm("multi", "step_1", ...)` в T7, совпадает; `build_extractors`
и `install` объявлены в T7 и импортируются в T8 под теми же именами.
