"""Structured-output parser: M0 regression behavior + schema-driven validation (M1)."""

import json
import unittest

from task import OUTPUT_SCHEMA
from utils import extract_json_text, format_error, parse_model_json

GOOD = {"summary": "ok", "steps": ["a", "b"], "confidence": 0.7}


def parse(text):
    return parse_model_json(text, OUTPUT_SCHEMA)


class ExtractionTests(unittest.TestCase):  # M0 behavior
    def test_bare_json(self):
        self.assertEqual(parse(json.dumps(GOOD)), GOOD)

    def test_fenced_json(self):
        self.assertEqual(parse(f"```json\n{json.dumps(GOOD)}\n```"), GOOD)
        self.assertEqual(parse(f"```\n{json.dumps(GOOD)}\n```"), GOOD)

    def test_json_surrounded_by_prose(self):
        self.assertEqual(parse(f"Sure! Here you go:\n{json.dumps(GOOD)}\nHope that helps."), GOOD)

    def test_extract_json_text(self):
        self.assertEqual(extract_json_text('  {"a": 1}  '), '{"a": 1}')


class M0ValidationTests(unittest.TestCase):  # M0 behavior, via the default task schema
    def assertRejects(self, data, pattern):
        with self.assertRaisesRegex(ValueError, pattern):
            parse(json.dumps(data))

    def test_invalid_json(self):
        with self.assertRaisesRegex(ValueError, "not valid JSON"):
            parse("this is not json")
        with self.assertRaisesRegex(ValueError, "not valid JSON"):
            parse('{"summary": "x",}')

    def test_empty_response(self):
        with self.assertRaisesRegex(ValueError, "not valid JSON"):
            parse("")

    def test_not_an_object(self):
        with self.assertRaisesRegex(ValueError, "Expected a JSON object"):
            parse_model_json("[1, 2]", OUTPUT_SCHEMA)

    def test_missing_fields(self):
        self.assertRejects({"summary": "x"}, "Missing required field.*steps, confidence")

    def test_wrong_types(self):
        self.assertRejects({**GOOD, "summary": 5}, "'summary' has the wrong type \\(int\\)")
        self.assertRejects({**GOOD, "steps": "a"}, "'steps' has the wrong type \\(str\\)")
        self.assertRejects({**GOOD, "confidence": "high"}, "'confidence' has the wrong type")

    def test_bool_is_not_a_number(self):
        self.assertRejects({**GOOD, "confidence": True}, "'confidence' has the wrong type \\(bool\\)")

    def test_confidence_range(self):
        self.assertRejects({**GOOD, "confidence": 1.5}, "between 0.0 and 1.0")
        self.assertRejects({**GOOD, "confidence": -0.1}, "between 0.0 and 1.0")
        for ok in (0, 1, 0.0, 1.0):
            self.assertEqual(parse(json.dumps({**GOOD, "confidence": ok}))["confidence"], ok)

    def test_empty_steps_allowed(self):
        self.assertEqual(parse(json.dumps({**GOOD, "steps": []}))["steps"], [])

    def test_format_error(self):
        self.assertEqual(format_error(ValueError("boom")), "ValueError: boom")


class SchemaDrivenTests(unittest.TestCase):  # M1: the schema comes from the caller
    def test_custom_schema(self):
        schema = {"label": "string", "count": 0, "ok": False}
        good = {"label": "x", "count": 3, "ok": True}
        self.assertEqual(parse_model_json(json.dumps(good), schema), good)
        with self.assertRaisesRegex(ValueError, "'ok' has the wrong type"):
            parse_model_json(json.dumps({**good, "ok": "yes"}), schema)

    def test_extra_keys_are_allowed(self):
        data = {**GOOD, "extra": 1}
        self.assertEqual(parse(json.dumps(data)), data)

    def test_list_items_checked_against_sample(self):
        with self.assertRaisesRegex(ValueError, r"'steps\[1\]' has the wrong type \(int\)"):
            parse(json.dumps({**GOOD, "steps": ["a", 2]}))

    def test_nested_objects_and_lists_of_objects(self):
        schema = {"hazards": [{"name": "string", "severity": 0}], "meta": {"source": "string"}}
        good = {"hazards": [{"name": "wire", "severity": 2}], "meta": {"source": "image"}}
        self.assertEqual(parse_model_json(json.dumps(good), schema), good)
        with self.assertRaisesRegex(ValueError, r"hazards\[0\]\.severity"):
            parse_model_json(json.dumps({**good, "hazards": [{"name": "w", "severity": "high"}]}), schema)
        with self.assertRaisesRegex(ValueError, "meta.source"):
            parse_model_json(json.dumps({**good, "meta": {}}), schema)

    def test_no_schema_only_requires_an_object(self):
        self.assertEqual(parse_model_json('{"anything": [1]}'), {"anything": [1]})
        with self.assertRaises(ValueError):
            parse_model_json("[1]")

    def test_confidence_range_applies_to_any_schema_with_that_key(self):
        with self.assertRaisesRegex(ValueError, "between 0.0 and 1.0"):
            parse_model_json('{"label": "x", "confidence": 2}', {"label": "string", "confidence": 0.0})


if __name__ == "__main__":
    unittest.main()
