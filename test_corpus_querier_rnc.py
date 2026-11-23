import json
import unittest
from pathlib import Path

from rnc_provider import (
    RNCError,
    SubcorpusFilters,
    build_subcorpus,
    canonicalize_formula,
    decode_regex,
    encode_regex,
    filter_form_counts,
    parse_concordance_response,
)


class ProviderTests(unittest.TestCase):
    def test_regex_roundtrip(self):
        self.assertEqual(decode_regex(encode_regex(".*ние")), ".*ние")

    def test_formula_spacing(self):
        self.assertEqual(
            canonicalize_formula("(S)& -(gen | gen2)"),
            "(S) & -(gen|gen2)",
        )

    def test_subcorpus_metadata(self):
        result = build_subcorpus(SubcorpusFilters(
            created_from=1990,
            created_to=2000,
            author_sex="male",
            category="non-fiction",
            topic="дом и домашнее хозяйство",
            text_type="доклад|лекция",
        ))
        conditions = result["sectionValues"][0]["conditionValues"]
        self.assertIn({"fieldName": "sex", "text": {"v": "муж"}}, conditions)
        self.assertIn(
            {"fieldName": "pri_cat:нехудожественная", "check": {"v": True}},
            conditions,
        )
        self.assertIn(
            {"fieldName": "type:нехудожественная", "text": {"v": "доклад | лекция"}},
            conditions,
        )
        date = next(item["dateRange"] for item in conditions if item["fieldName"] == "created")
        self.assertEqual(date["begin"]["year"], 1990)
        self.assertEqual(date["end"]["year"], 2000)

    def test_form_filter_can_merge_case(self):
        self.assertEqual(
            filter_form_counts({"Папа": 2, "папа": 3, "папы": 1}, minimum=2, ignore_case=True),
            {"папа": 5},
        )

    def test_explicit_zero_count_is_a_success(self):
        result = parse_concordance_response({
            "queryStats": {"wordUsageCount": 0, "textCount": 0},
            "groups": [],
            "pagination": {"totalPageCount": 0, "maxAvailablePage": 0},
        })
        self.assertEqual(result.total_occurrences, 0)
        self.assertEqual(result.matching_texts, 0)

    def test_confirmed_empty_response_without_count_is_zero(self):
        result = parse_concordance_response({
            "queryStats": {"textCount": 0},
            "groups": [],
            "pagination": {"totalPageCount": 0, "maxAvailablePage": 0},
        })
        self.assertEqual(result.total_occurrences, 0)

    def test_missing_count_without_empty_evidence_is_an_error(self):
        with self.assertRaises(RNCError):
            parse_concordance_response({
                "queryStats": {},
                "groups": [],
                "pagination": {},
            })

    def test_nonempty_groups_without_count_is_an_error(self):
        with self.assertRaises(RNCError):
            parse_concordance_response({
                "queryStats": {"textCount": 0},
                "groups": [{"docs": []}],
                "pagination": {"totalPageCount": 0},
            })

    def test_saved_real_response(self):
        fixture = Path(__file__).with_name("upload") / "rnc-response-pretty.json"
        if not fixture.exists():
            self.skipTest("RNC response fixture is not present")
        result = parse_concordance_response(json.loads(fixture.read_text(encoding="utf-8")))
        self.assertEqual(result.total_occurrences, 56897)
        self.assertEqual(result.matching_texts, 7887)
        self.assertEqual(result.total_pages, 789)
        self.assertGreater(len(result.examples), 0)
        self.assertIn("папа", {form.casefold() for form in result.sampled_form_counts})


if __name__ == "__main__":
    unittest.main()
