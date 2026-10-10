import json
import unittest

import prompts
import task
from utils import validate

SCHEMA = {"label": "string", "score": 0.0, "tags": ["string"]}
EXAMPLE = {
    "input": "a photo of a cat",
    "output": {"label": "cat", "score": 0.9, "tags": ["animal"]},
}


class BuildPromptTests(unittest.TestCase):
    def test_task_instructions_appear(self):
        out = prompts.build_prompt("Count the widgets.", SCHEMA)
        self.assertIn("Count the widgets.", out)

    def test_output_schema_appears(self):
        out = prompts.build_prompt("x", SCHEMA)
        self.assertIn(json.dumps(SCHEMA, indent=2), out)

    def test_example_appears_when_provided(self):
        out = prompts.build_prompt("x", SCHEMA, EXAMPLE)
        self.assertIn("EXAMPLE:", out)
        self.assertIn("a photo of a cat", out)
        self.assertIn(json.dumps(EXAMPLE["output"], indent=2), out)

    def test_no_example_section_without_example(self):
        self.assertNotIn("EXAMPLE:", prompts.build_prompt("x", SCHEMA))

    def test_json_only_instruction_appears(self):
        out = prompts.build_prompt("x", SCHEMA)
        self.assertIn("ONLY a single valid JSON object", out)
        self.assertIn("no markdown fences", out)

    def test_all_sections_present_in_order(self):
        out = prompts.build_prompt("x", SCHEMA, EXAMPLE)
        positions = [out.index(s) for s in ("ROLE:", "TASK:", "INPUT:", "OUTPUT FORMAT:", "RULES:", "EXAMPLE:")]
        self.assertEqual(positions, sorted(positions))

    def test_bad_arguments_are_rejected(self):
        with self.assertRaises(ValueError):
            prompts.build_prompt("  ", SCHEMA)
        with self.assertRaises(ValueError):
            prompts.build_prompt("x", {})
        with self.assertRaises(ValueError):
            prompts.build_prompt("x", SCHEMA, example={"input": "no output key"})

    def test_active_task_prompt_is_built_from_task_config(self):
        t = task.TASK
        out = prompts.build_prompt(t.instructions, t.output_schema, t.example)
        self.assertIn(t.instructions.strip(), out)
        for key in t.output_schema:
            self.assertIn(f'"{key}"', out)

    def test_task_example_matches_its_own_schema(self):
        if task.TASK.example is not None:
            validate(task.TASK.example["output"], task.TASK.output_schema)


class UserPromptTests(unittest.TestCase):
    """M0 behavior: the per-mode user prompt."""

    def test_modes(self):
        self.assertEqual(prompts.build_user_prompt("hello", has_image=False), "hello")
        self.assertEqual(prompts.build_user_prompt("", has_image=True), prompts.IMAGE_ONLY)
        both = prompts.build_user_prompt("what is this?", has_image=True)
        self.assertIn("what is this?", both)
        self.assertIn("attached image", both)


if __name__ == "__main__":
    unittest.main()
