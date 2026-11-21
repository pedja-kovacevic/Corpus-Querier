"""Translate a practical CQL-like subset to RNC lex-gramm requests.

This is deliberately a syntax adapter, not a tagset translator. Values of
``tag``/``gramm`` must already be valid RNC formulas for the selected corpus.
Unsupported constructs raise :class:`TranslationError` rather than being
guessed.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import TypeAlias

from rnc_provider import canonicalize_formula, regex_condition, text_condition


class TranslationError(ValueError):
    """Raised when equivalent RNC request semantics cannot be guaranteed."""


@dataclass(frozen=True)
class CQLCondition:
    attribute: str
    operator: str
    value: str


@dataclass(frozen=True)
class BooleanExpression:
    operator: str
    left: "Expression"
    right: "Expression"


Expression: TypeAlias = CQLCondition | BooleanExpression


@dataclass(frozen=True)
class CQLToken:
    expression: Expression


@dataclass(frozen=True)
class TranslationReport:
    source_cql: str
    corpus: str
    payload: dict
    warnings: tuple[str, ...]

    def as_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.payload, ensure_ascii=False, indent=indent)


_ALIASES = {
    "lemma": "lex", "lex": "lex",
    "word": "form", "form": "form",
    "tag": "gramm", "gramm": "gramm",
    "lemma_regex": "lex_regexp", "lex_regex": "lex_regexp",
    "lex_regexp": "lex_regexp",
    "word_regex": "form_regexp", "form_regex": "form_regexp",
    "form_regexp": "form_regexp",
    "dist": "dist",
}
_REGEX_META = re.compile(r"(?<!\\)[.*+?{}|()]|\\[AbBdDsSwWZ]")
_LEAF = re.compile(
    r"(?P<attribute>[A-Za-z_][A-Za-z0-9_-]*)\s*"
    r"(?P<operator>!=|=)\s*"
    r"(?P<quote>['\"])(?P<value>(?:\\.|(?!\3).)*)(?P=quote)",
    re.DOTALL,
)


class _TokenParser:
    def __init__(self, source: str, number: int):
        self.source = source
        self.number = number
        self.position = 0

    def parse(self) -> Expression:
        expression = self._parse_or()
        self._skip_space()
        if self.position != len(self.source):
            raise self._error("Unexpected material")
        return expression

    def _parse_or(self) -> Expression:
        expression = self._parse_and()
        while True:
            self._skip_space()
            if not self._consume("|"):
                return expression
            expression = BooleanExpression("|", expression, self._parse_and())

    def _parse_and(self) -> Expression:
        expression = self._parse_primary()
        while True:
            self._skip_space()
            if not self._consume("&"):
                return expression
            expression = BooleanExpression("&", expression, self._parse_primary())

    def _parse_primary(self) -> Expression:
        self._skip_space()
        if self._consume("("):
            expression = self._parse_or()
            self._skip_space()
            if not self._consume(")"):
                raise self._error("Missing closing parenthesis")
            return expression

        match = _LEAF.match(self.source, self.position)
        if not match:
            raise self._error("Expected a quoted condition")
        self.position = match.end()
        raw_attribute = match.group("attribute").lower()
        if raw_attribute not in _ALIASES:
            supported = ", ".join(sorted(_ALIASES))
            raise TranslationError(
                f"Unsupported attribute {raw_attribute!r} in token {self.number}. "
                f"Supported attributes: {supported}."
            )
        value = re.sub(r"\\([\\\"'])", r"\1", match.group("value"))
        return CQLCondition(_ALIASES[raw_attribute], match.group("operator"), value)

    def _skip_space(self) -> None:
        while self.position < len(self.source) and self.source[self.position].isspace():
            self.position += 1

    def _consume(self, value: str) -> bool:
        if self.source.startswith(value, self.position):
            self.position += len(value)
            return True
        return False

    def _error(self, message: str) -> TranslationError:
        remainder = self.source[self.position:self.position + 50]
        return TranslationError(f"{message} in token {self.number} near {remainder!r}.")


def _extract_token_bodies(cql: str) -> list[str]:
    bodies: list[str] = []
    position = 0
    while position < len(cql):
        while position < len(cql) and cql[position].isspace():
            position += 1
        if position >= len(cql):
            break
        if cql[position] != "[":
            raise TranslationError(
                f"Unsupported material outside a token at character {position + 1}. "
                "Token repetition and structural constraints are not supported."
            )
        start = position + 1
        position = start
        quote: str | None = None
        escaped = False
        while position < len(cql):
            character = cql[position]
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif quote:
                if character == quote:
                    quote = None
            elif character in {'"', "'"}:
                quote = character
            elif character == "]":
                break
            position += 1
        if position >= len(cql):
            raise TranslationError("Unclosed CQL token.")
        bodies.append(cql[start:position])
        position += 1
    if not bodies:
        raise TranslationError("The query contains no tokens.")
    return bodies


def parse_supported_cql(cql: str) -> tuple[CQLToken, ...]:
    """Parse the supported CQL-like syntax."""

    if not isinstance(cql, str) or not cql.strip():
        raise TranslationError("The query is empty.")
    return tuple(
        CQLToken(_TokenParser(body, number).parse())
        for number, body in enumerate(_extract_token_bodies(cql.strip()), 1)
    )


def _flatten(expression: Expression, operator: str) -> list[Expression]:
    if isinstance(expression, BooleanExpression) and expression.operator == operator:
        return _flatten(expression.left, operator) + _flatten(expression.right, operator)
    return [expression]


def _pure_attribute(expression: Expression) -> str | None:
    if isinstance(expression, CQLCondition):
        return expression.attribute
    left = _pure_attribute(expression.left)
    right = _pure_attribute(expression.right)
    return left if left and left == right else None


def _grammar_formula(expression: Expression) -> str:
    if isinstance(expression, CQLCondition):
        if expression.attribute != "gramm":
            raise TranslationError("A grammatical formula contains a non-grammar condition.")
        value = canonicalize_formula(expression.value)
        if not value:
            raise TranslationError("A grammar condition is empty.")
        return f"-({value})" if expression.operator == "!=" else value
    left = _grammar_formula(expression.left)
    right = _grammar_formula(expression.right)
    joiner = " & " if expression.operator == "&" else "|"
    return f"({left}{joiner}{right})"


def _lexical_condition(expression: Expression) -> dict:
    leaves = _flatten(expression, "|")
    if any(not isinstance(leaf, CQLCondition) for leaf in leaves):
        raise TranslationError("AND between values of one lexical attribute is unsupported.")
    typed = [leaf for leaf in leaves if isinstance(leaf, CQLCondition)]
    if any(leaf.operator != "=" for leaf in typed):
        raise TranslationError(
            "Lexical negation is not translated because an equivalent RNC request "
            "has not been verified."
        )
    attributes = {leaf.attribute for leaf in typed}
    if len(attributes) != 1:
        raise TranslationError("OR may only join alternatives of the same attribute.")
    attribute = typed[0].attribute
    explicit_regex = attribute.endswith("_regexp")
    plain_field = attribute.removesuffix("_regexp")
    regex_needed = explicit_regex or len(typed) > 1 or any(
        _REGEX_META.search(leaf.value) for leaf in typed
    )
    if not regex_needed:
        return text_condition(plain_field, typed[0].value)
    patterns = [
        leaf.value if explicit_regex or _REGEX_META.search(leaf.value) else re.escape(leaf.value)
        for leaf in typed
    ]
    pattern = patterns[0] if len(patterns) == 1 else f"({'|'.join(patterns)})"
    return regex_condition(f"{plain_field}_regexp", pattern)


def _compile_token(expression: Expression, token_number: int) -> tuple[list[dict], tuple[int, int] | None]:
    components = _flatten(expression, "&")
    conditions: list[dict] = []
    distance: tuple[int, int] | None = None
    grammar_parts: list[Expression] = []
    seen_lexical: set[str] = set()

    for component in components:
        attribute = _pure_attribute(component)
        if attribute is None:
            raise TranslationError(
                f"Token {token_number} contains OR across different attributes. "
                "That cannot be represented safely in one RNC word position."
            )
        if attribute == "gramm":
            grammar_parts.append(component)
            continue
        if attribute == "dist":
            if not isinstance(component, CQLCondition) or component.operator != "=":
                raise TranslationError("Distance must be a quoted equality such as dist=\"1:3\".")
            match = re.fullmatch(r"\s*(-?\d+)\s*:\s*(-?\d+)\s*", component.value)
            if not match:
                raise TranslationError("Distance must have MIN:MAX form, for example \"1:3\".")
            distance = (int(match.group(1)), int(match.group(2)))
            if distance[0] > distance[1]:
                raise TranslationError("Distance minimum must not exceed its maximum.")
            continue
        plain = attribute.removesuffix("_regexp")
        if plain in seen_lexical:
            raise TranslationError(
                f"Token {token_number} repeats {plain!r} in separate AND clauses."
            )
        seen_lexical.add(plain)
        conditions.append(_lexical_condition(component))

    if grammar_parts:
        grammar_expression = grammar_parts[0]
        for item in grammar_parts[1:]:
            grammar_expression = BooleanExpression("&", grammar_expression, item)
        formula = canonicalize_formula(_grammar_formula(grammar_expression))
        conditions.append(text_condition("gramm", formula))
    if not conditions:
        raise TranslationError(f"Token {token_number} has no lexical or grammar condition.")
    return conditions, distance


def translate_cql(cql: str, corpus: str = "MAIN") -> TranslationReport:
    """Translate supported compact notation to an RNC concordance payload."""

    corpus = corpus.strip().upper()
    if not corpus:
        raise TranslationError("An RNC corpus identifier is required.")
    tokens = parse_supported_cql(cql)
    subsections: list[dict] = []
    warnings: list[str] = []

    for index, token in enumerate(tokens):
        conditions, explicit_distance = _compile_token(token.expression, index + 1)
        if index:
            begin, end = explicit_distance or (1, 1)
            conditions.append({
                "fieldName": "dist",
                "intRange": {"begin": begin, "end": end},
            })
        elif explicit_distance is not None:
            raise TranslationError("Distance is meaningful only on the second or later token.")
        conditions.append(text_condition("sem-mod", "sem|semx"))
        subsections.append({"conditionValues": conditions})

    if re.search(r"\btag\s*!?=", cql, re.IGNORECASE):
        warnings.append(
            "tag values are passed as native RNC gramm formulas; no tagset "
            "translation is performed."
        )

    payload = {
        "lexGramm": {
            "sectionValues": [{
                "conditionValues": [
                    text_condition("disambmod", "main"),
                    text_condition("distmod", "no_zeros"),
                ],
                "subsectionValues": subsections,
            }]
        },
        "params": {
            "pageParams": {
                "page": "0", "docsPerPage": "10",
                "snippetsPerPage": "50", "snippetsPerDoc": "10",
            },
            "collocationThreshold": "5", "sampling": "0", "noDiacritic": False,
        },
        "corpus": {"type": corpus},
    }
    return TranslationReport(cql, corpus, payload, tuple(warnings))
