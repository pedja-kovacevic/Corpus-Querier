"""Backend utilities for the Russian National Corpus public API.

The functions in this module do not depend on Tkinter.  They deliberately keep
query construction, HTTP access, and response parsing separate so they can be
unit-tested and reused by the desktop application.
"""

from __future__ import annotations

import base64
import copy
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Iterable

try:
    import requests
except ModuleNotFoundError:  # Pure parsing/query-building tests need no HTTP client.
    requests = None  # type: ignore[assignment]


API_ROOT = "https://ruscorpora.ru/api/v1"
CONCORDANCE_URL = f"{API_ROOT}/lex-gramm/concordance"
AUTH_CHECK_URL = f"{API_ROOT}/auth/check-authenticated/"
ATTR_URL = f"{API_ROOT}/attrs"


class RNCError(RuntimeError):
    """Raised for invalid requests or unexpected RNC responses."""


def encode_regex(expression: str) -> str:
    """Encode an RNC regular expression as Base64 UTF-8."""

    if not isinstance(expression, str) or not expression:
        raise ValueError("A regular expression is required.")
    return base64.b64encode(expression.encode("utf-8")).decode("ascii")


def decode_regex(value: str) -> str:
    """Decode an RNC Base64 UTF-8 regular expression."""

    return base64.b64decode(value).decode("utf-8")


def canonicalize_formula(formula: str) -> str:
    """Format an RNC attribute formula without changing its grouping.

    Empirical tests against the RNC interface showed that grammar alternatives
    must not contain whitespace around ``|`` while ``&`` is safely represented
    with one space on either side.
    """

    result = formula.strip()
    result = re.sub(r"\s*\|\s*", "|", result)
    result = re.sub(r"\s*&\s*", " & ", result)
    result = re.sub(r"-\s+", "-", result)
    result = re.sub(r"\s+", " ", result)
    return result


def text_condition(field_name: str, value: str) -> dict[str, Any]:
    return {"fieldName": field_name, "text": {"v": value}}


def regex_condition(field_name: str, expression: str) -> dict[str, Any]:
    if field_name not in {"lex_regexp", "form_regexp"}:
        raise ValueError(f"Unsupported RNC regex field: {field_name}")
    return text_condition(field_name, encode_regex(expression))


@dataclass(frozen=True)
class SubcorpusFilters:
    """Common Main Corpus metadata filters exposed by the desktop UI."""

    created_from: int | None = None
    created_to: int | None = None
    author: str = ""
    author_sex: str = ""  # any, male, female, or a native RNC value
    category: str = ""  # any, fiction, non-fiction, or native RNC value
    sphere: str = ""
    topic: str = ""
    text_type: str = ""
    genre: str = ""
    chronotope: str = ""
    extra_text_fields: tuple[tuple[str, str], ...] = field(default_factory=tuple)


_SEX_VALUES = {
    "": "",
    "any": "",
    "male": "муж",
    "female": "жен",
    "муж": "муж",
    "жен": "жен",
}

_CATEGORY_VALUES = {
    "": "",
    "any": "",
    "fiction": "художественная",
    "non-fiction": "нехудожественная",
    "nonfiction": "нехудожественная",
    "художественная": "художественная",
    "нехудожественная": "нехудожественная",
}


def _clean_multi_value(value: str) -> str:
    """Canonicalize subcorpus multi-selection using spaced pipes."""

    items = [item.strip() for item in value.split("|") if item.strip()]
    return " | ".join(items)


def build_subcorpus(filters: SubcorpusFilters) -> dict[str, Any] | None:
    """Build an official RNC subcorpus object from common metadata filters."""

    conditions: list[dict[str, Any]] = []

    if filters.created_from is not None or filters.created_to is not None:
        begin = (
            {"year": int(filters.created_from), "month": 1, "day": 1}
            if filters.created_from is not None
            else None
        )
        end = (
            {"year": int(filters.created_to), "month": 12, "day": 31}
            if filters.created_to is not None
            else None
        )
        if begin and end and begin["year"] > end["year"]:
            raise ValueError("Creation-year start must not exceed the end year.")
        conditions.append({
            "fieldName": "created",
            "dateRange": {
                "begin": begin,
                "end": end,
                "matching": "INT_RANGE_INTERSECT",
            },
        })

    if filters.author.strip():
        conditions.append(text_condition("author", filters.author.strip()))

    sex_key = filters.author_sex.strip().lower()
    sex = _SEX_VALUES.get(sex_key, filters.author_sex.strip())
    if sex:
        conditions.append(text_condition("sex", sex))

    category_key = filters.category.strip().lower()
    category = _CATEGORY_VALUES.get(category_key, filters.category.strip())
    if category:
        conditions.append({
            "fieldName": f"pri_cat:{category}",
            "check": {"v": True},
        })

    if filters.sphere.strip():
        # The Main Corpus exposes functional sphere for non-fiction texts.
        conditions.append(text_condition(
            "sphere:нехудожественная",
            _clean_multi_value(filters.sphere),
        ))
    if filters.topic.strip():
        conditions.append(text_condition("topic", _clean_multi_value(filters.topic)))
    if filters.text_type.strip():
        if not category:
            raise ValueError("Choose Fiction or Non-fiction before selecting a text type.")
        conditions.append(text_condition(
            f"type:{category}",
            _clean_multi_value(filters.text_type),
        ))
    if filters.genre.strip():
        conditions.append(text_condition(
            "genre:художественная",
            _clean_multi_value(filters.genre),
        ))
    if filters.chronotope.strip():
        conditions.append(text_condition(
            "chronotop:художественная",
            _clean_multi_value(filters.chronotope),
        ))

    for field_name, value in filters.extra_text_fields:
        field_name = field_name.strip()
        value = value.strip()
        if field_name and value:
            conditions.append(text_condition(field_name, _clean_multi_value(value)))

    if not conditions:
        return None
    return {"sectionValues": [{"conditionValues": conditions}]}


def merge_subcorpus(payload: dict[str, Any], subcorpus: dict[str, Any] | None) -> dict[str, Any]:
    """Merge global metadata filters into an existing request payload."""

    result = copy.deepcopy(payload)
    if not subcorpus:
        return result

    incoming = (
        subcorpus.get("sectionValues", [{}])[0].get("conditionValues", [])
        if isinstance(subcorpus, dict)
        else []
    )
    if not incoming:
        return result

    current = result.setdefault("subcorpus", {}).setdefault(
        "sectionValues", [{"conditionValues": []}]
    )
    if not current:
        current.append({"conditionValues": []})
    current[0].setdefault("conditionValues", []).extend(copy.deepcopy(incoming))
    return result


@dataclass(frozen=True)
class ConcordanceExample:
    text: str
    hits: tuple[str, ...]
    metadata: dict[str, str]
    document_id: str = ""


@dataclass(frozen=True)
class ConcordanceResult:
    total_occurrences: int
    matching_texts: int
    total_pages: int
    max_available_page: int
    examples: tuple[ConcordanceExample, ...]
    sampled_form_counts: dict[str, int]
    corpus_stats: dict[str, int]
    subcorpus_stats: dict[str, int]


def _attr_value_to_text(value: Any) -> str:
    if not isinstance(value, dict):
        return str(value)
    for key in ("valString", "valInt"):
        inner = value.get(key)
        if isinstance(inner, dict) and "v" in inner:
            return str(inner["v"])
    return ""


def _document_metadata(document: dict[str, Any]) -> dict[str, str]:
    metadata: dict[str, str] = {}
    info = document.get("info", {})
    if info.get("title"):
        metadata["title"] = str(info["title"])
    items = info.get("docExplainInfo", {}).get("items", [])
    for item in items:
        for field_info in item.get("parsingFields", []):
            values = [
                _attr_value_to_text(value)
                for value in field_info.get("value", [])
            ]
            values = [value for value in values if value]
            if values:
                metadata[str(field_info.get("name", ""))] = "; ".join(values)
    return metadata


def _is_confirmed_empty_result(data: dict[str, Any], stats: dict[str, Any]) -> bool:
    """Recognize a successful empty concordance without masking malformed data.

    The RNC may omit ``wordUsageCount`` for a genuine no-match response. We
    accept that omission as zero when a successful concordance response has an
    explicitly empty ``groups`` list.  This is the stable empty-result marker
    used by the API even though its pagination/statistics fields are not
    consistent across zero-hit queries.  Transport errors and HTTP failures are
    handled before this parser; a merely missing field without ``groups: []``
    remains an error.
    """

    if data.get("groups") != []:
        return False
    if any(data.get(key) for key in ("error", "errors", "exception")):
        return False
    return isinstance(stats, dict)


def parse_concordance_response(data: dict[str, Any]) -> ConcordanceResult:
    """Parse totals, examples, hit forms, and metadata from an RNC response."""

    if not isinstance(data, dict):
        raise RNCError("The RNC response is not a JSON object.")
    stats = data.get("queryStats")
    if not isinstance(stats, dict):
        raise RNCError("The RNC response does not contain queryStats.")
    count = stats.get("wordUsageCount")
    if count is None:
        if _is_confirmed_empty_result(data, stats):
            count = 0
        else:
            raise RNCError(
                "The RNC response does not contain wordUsageCount and does not "
                "explicitly identify an empty result."
            )
    if isinstance(count, bool):
        raise RNCError("The RNC wordUsageCount value is not numeric.")
    try:
        total_occurrences = int(count)
    except (TypeError, ValueError) as error:
        raise RNCError("The RNC wordUsageCount value is not numeric.") from error
    if total_occurrences < 0:
        raise RNCError("The RNC wordUsageCount value is negative.")

    examples: list[ConcordanceExample] = []
    forms: Counter[str] = Counter()

    for group in data.get("groups", []):
        for document in group.get("docs", []):
            metadata = _document_metadata(document)
            info = document.get("info", {})
            document_id = str(info.get("source", {}).get("docId", ""))
            for snippet_group in document.get("snippetGroups", []):
                for snippet in snippet_group.get("snippets", []):
                    text_parts: list[str] = []
                    hits: list[str] = []
                    for sequence in snippet.get("sequences", []):
                        for word in sequence.get("words", []):
                            text = str(word.get("text", ""))
                            text_parts.append(text)
                            if word.get("displayParams", {}).get("hit") is True:
                                hits.append(text)
                                forms[text] += 1
                    examples.append(ConcordanceExample(
                        text="".join(text_parts).strip(),
                        hits=tuple(hits),
                        metadata=dict(metadata),
                        document_id=document_id,
                    ))

    pagination = data.get("pagination") or {}
    return ConcordanceResult(
        total_occurrences=total_occurrences,
        matching_texts=int(stats.get("textCount") or 0),
        total_pages=int(pagination.get("totalPageCount") or 0),
        max_available_page=int(pagination.get("maxAvailablePage") or 0),
        examples=tuple(examples),
        sampled_form_counts=dict(forms),
        corpus_stats={
            key: int(value)
            for key, value in (data.get("corpusStats") or {}).items()
            if isinstance(value, (int, float))
        },
        subcorpus_stats={
            key: int(value)
            for key, value in (data.get("subcorpStats") or {}).items()
            if isinstance(value, (int, float))
        },
    )


def casefold_counts(counts: dict[str, int]) -> dict[str, int]:
    combined: Counter[str] = Counter()
    display: dict[str, str] = {}
    for form, count in counts.items():
        key = form.casefold()
        display.setdefault(key, form.lower())
        combined[key] += int(count)
    return {display[key]: value for key, value in combined.items()}


def filter_form_counts(
    counts: dict[str, int],
    *,
    minimum: int = 1,
    ignore_case: bool = False,
) -> dict[str, int]:
    result = casefold_counts(counts) if ignore_case else dict(counts)
    return {
        form: count
        for form, count in sorted(result.items(), key=lambda item: (-item[1], item[0]))
        if count >= minimum
    }


def flatten_attribute_values(data: Any) -> list[str]:
    """Collect selectable RNC attribute values from a recursive schema response."""

    found: list[str] = []

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            if isinstance(value.get("value"), str):
                found.append(value["value"])
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(data)
    return list(dict.fromkeys(item for item in found if item))


class RNCClient:
    """Small authenticated client for the official RNC API."""

    def __init__(self, token: str, *, timeout: float = 60, session: requests.Session | None = None):
        if requests is None:
            raise RuntimeError("The 'requests' package is required for RNC API access.")
        token = token.strip()
        if not token:
            raise ValueError("Enter an RNC API token.")
        self.timeout = timeout
        self.session = session or requests.Session()
        self._owns_session = session is None
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "Corpus-Querier-RNC/3.3.1",
        })

    def close(self) -> None:
        if self._owns_session:
            self.session.close()

    def _check(self, response: requests.Response) -> None:
        if response.status_code == 401:
            raise RNCError("Authentication failed. Check or regenerate the RNC API token.")
        if response.status_code == 429:
            raise RNCError("RNC request limit reached. Wait before retrying.")
        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            detail = response.text.strip()
            raise RNCError(detail or str(error)) from error

    def test_connection(self) -> bool:
        response = self.session.get(AUTH_CHECK_URL, timeout=self.timeout)
        self._check(response)
        return response.json() is True

    def concordance(self, payload: dict[str, Any]) -> ConcordanceResult:
        response = self.session.post(CONCORDANCE_URL, json=payload, timeout=self.timeout)
        self._check(response)
        return parse_concordance_response(response.json())

    def attribute_values(self, corpus: str, attribute: str) -> list[str]:
        response = self.session.get(
            f"{ATTR_URL}/{attribute}",
            params={"corpus": f'{{"type":"{corpus.upper()}"}}'},
            timeout=self.timeout,
        )
        self._check(response)
        return flatten_attribute_values(response.json())


def set_page(payload: dict[str, Any], page: int, *, docs_per_page: int | None = None) -> dict[str, Any]:
    result = copy.deepcopy(payload)
    params = result.setdefault("params", {})
    page_params = params.setdefault("pageParams", {})
    page_params["page"] = int(page)
    if docs_per_page is not None:
        page_params["docsPerPage"] = int(docs_per_page)
    return result

