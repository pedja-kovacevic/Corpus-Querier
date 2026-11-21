import unittest

from rnc_cql_translator import TranslationError, translate_cql
from rnc_provider import decode_regex


def token_conditions(query, token=0):
    payload = translate_cql(query).payload
    return payload["lexGramm"]["sectionValues"][0]["subsectionValues"][token][
        "conditionValues"
    ]


class TranslatorTests(unittest.TestCase):
    def test_literal_lemma_uses_lex(self):
        self.assertEqual(
            token_conditions('[lemma="папа"]')[0],
            {"fieldName": "lex", "text": {"v": "папа"}},
        )

    def test_literal_word_uses_form(self):
        self.assertEqual(
            token_conditions('[word="папа"]')[0],
            {"fieldName": "form", "text": {"v": "папа"}},
        )

    def test_lemma_regex_is_base64_encoded(self):
        condition = token_conditions('[lemma=".*ние"]')[0]
        self.assertEqual(condition["fieldName"], "lex_regexp")
        self.assertEqual(decode_regex(condition["text"]["v"]), ".*ние")

    def test_explicit_word_regex(self):
        condition = token_conditions('[word_regex=".*ого"]')[0]
        self.assertEqual(condition["fieldName"], "form_regexp")
        self.assertEqual(decode_regex(condition["text"]["v"]), ".*ого")

    def test_grammar_formula_spacing(self):
        conditions = token_conditions('[lemma="папа" & tag="(S) & -(gen | gen2)"]')
        self.assertEqual(
            conditions[1],
            {"fieldName": "gramm", "text": {"v": "(S) & -(gen|gen2)"}},
        )

    def test_same_attribute_or_becomes_regex(self):
        condition = token_conditions('[lemma="папа" | lemma="мама"]')[0]
        self.assertEqual(condition["fieldName"], "lex_regexp")
        self.assertEqual(decode_regex(condition["text"]["v"]), "(папа|мама)")

    def test_grammar_boolean_tree(self):
        condition = token_conditions('[gramm="S" & (gramm="gen" | gramm="gen2")]')[0]
        self.assertEqual(condition["text"]["v"], "(S & (gen|gen2))")

    def test_grammar_negation(self):
        condition = token_conditions('[gramm="S" & gramm!="gen | gen2"]')[0]
        self.assertEqual(condition["text"]["v"], "(S & -(gen|gen2))")

    def test_multiple_tokens_default_to_adjacency(self):
        conditions = token_conditions('[lemma="синий"] [lemma="мяч"]', 1)
        self.assertIn(
            {"fieldName": "dist", "intRange": {"begin": 1, "end": 1}},
            conditions,
        )

    def test_explicit_distance(self):
        conditions = token_conditions('[lemma="синий"] [lemma="мяч" & dist="1:3"]', 1)
        self.assertIn(
            {"fieldName": "dist", "intRange": {"begin": 1, "end": 3}},
            conditions,
        )

    def test_cross_attribute_or_is_rejected(self):
        with self.assertRaisesRegex(TranslationError, "different attributes"):
            translate_cql('[lemma="папа" | word="папа"]')

    def test_lexical_negation_is_rejected(self):
        with self.assertRaisesRegex(TranslationError, "Lexical negation"):
            translate_cql('[lemma!="папа"]')

    def test_repetition_is_rejected(self):
        with self.assertRaisesRegex(TranslationError, "outside a token"):
            translate_cql('[lemma="очень"]{1,3}')

    def test_unknown_attribute_is_rejected(self):
        with self.assertRaisesRegex(TranslationError, "Unsupported attribute"):
            translate_cql('[sem="person"]')


if __name__ == "__main__":
    unittest.main()
