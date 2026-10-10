"""Hackathon task swap: the same provider / prompt builder / parser / UI handler run two
different tasks, and only the Task configuration differs."""

import json
import unittest
from unittest import mock

import app
import prompts
from task import Task
from tests.helpers import FakeClient, patch_client, tiny_image
from utils import parse_model_json

TASK_A = Task(
    name="Main Object Finder",
    instructions="Analyze an image and identify the main object.",
    output_schema={"main_object": "string", "confidence": 0.0},
)
REPLY_A = {"main_object": "red square", "confidence": 0.9}

TASK_B = Task(
    name="Safety Hazard Spotter",
    instructions="Analyze an image and identify potential safety hazards.",
    output_schema={"hazards": ["string"], "risk_level": "string", "confidence": 0.0},
    example={
        "input": "a wet floor",
        "output": {"hazards": ["slip risk"], "risk_level": "medium", "confidence": 0.8},
    },
)
REPLY_B = {"hazards": ["trip hazard"], "risk_level": "low", "confidence": 0.6}


def reply_by_system_prompt(call):
    """A fake 'model' that answers whichever task its system prompt describes."""
    system = call.config.system_instruction
    if "safety hazards" in system:
        return json.dumps(REPLY_B)
    if "main object" in system:
        return json.dumps(REPLY_A)
    return "unexpected system prompt"


def final_yield(gen):
    last = None
    for last in gen:
        pass
    return last


class TaskSwapTests(unittest.TestCase):
    def run_ui(self, task, text="", image=None):
        client = FakeClient(reply_by_system_prompt)
        with patch_client(client), mock.patch.object(app, "TASK", task):
            status, result, raw, _ = final_yield(app.analyze(text, image))
        return client, status, result, raw

    def test_same_infrastructure_runs_task_a_and_task_b(self):
        client_a, status_a, result_a, _ = self.run_ui(TASK_A, image=tiny_image())
        client_b, status_b, result_b, _ = self.run_ui(TASK_B, image=tiny_image())

        self.assertEqual((status_a, result_a), ("Done.", REPLY_A))
        self.assertEqual((status_b, result_b), ("Done.", REPLY_B))

        # Each task's own instructions and schema reached the provider...
        system_a = client_a.calls[0].config.system_instruction
        system_b = client_b.calls[0].config.system_instruction
        self.assertIn(TASK_A.instructions, system_a)
        self.assertIn('"main_object"', system_a)
        self.assertNotIn("hazards", system_a)
        self.assertIn(TASK_B.instructions, system_b)
        self.assertIn('"risk_level"', system_b)
        self.assertIn("EXAMPLE:", system_b)
        self.assertNotIn("main_object", system_b)

        # ...through the same provider path (image -> PNG part + user prompt).
        for client in (client_a, client_b):
            image_part, _prompt = client.calls[0].contents
            self.assertEqual(image_part.inline_data.mime_type, "image/png")

    def test_each_task_is_validated_against_its_own_schema(self):
        # Task A's reply is a valid Task A answer but not a valid Task B answer.
        client = FakeClient(json.dumps(REPLY_A))
        for task, expect_ok in ((TASK_A, True), (TASK_B, False)):
            with patch_client(client), mock.patch.object(app, "TASK", task):
                status, result, raw, _ = final_yield(app.analyze("x", None))
            self.assertEqual(status == "Done.", expect_ok, status)
            self.assertEqual(result is not None, expect_ok)
            self.assertEqual(raw, json.dumps(REPLY_A))  # raw is always available for inspection
        self.assertIn("Missing required field(s): hazards, risk_level", status)

    def test_text_path_works_for_both_tasks(self):
        for task, reply in ((TASK_A, REPLY_A), (TASK_B, REPLY_B)):
            client, status, result, _ = self.run_ui(task, text="describe the scene")
            self.assertEqual((status, result), ("Done.", reply))
            self.assertEqual(client.calls[0].contents, ["describe the scene"])

    def test_text_plus_image_path_works_for_both_tasks(self):
        for task, reply in ((TASK_A, REPLY_A), (TASK_B, REPLY_B)):
            client, status, result, _ = self.run_ui(task, text="what is it?", image=tiny_image())
            self.assertEqual((status, result), ("Done.", reply))
            self.assertIn("what is it?", client.calls[0].contents[1])

    def test_swap_needs_no_provider_or_ui_changes(self):
        """The only per-task input to the pipeline is the Task object."""
        for task in (TASK_A, TASK_B):
            system = prompts.build_prompt(task.instructions, task.output_schema, task.example)
            raw = json.dumps(REPLY_A if task is TASK_A else REPLY_B)
            self.assertEqual(parse_model_json(raw, task.output_schema), json.loads(raw))
            self.assertIn(task.instructions, system)


class UiWiringTests(unittest.TestCase):
    def test_task_name_is_shown_in_ui(self):
        import gradio as gr

        texts = [b.value for b in app.demo.blocks.values() if isinstance(b, gr.Markdown)]
        self.assertTrue(any(f"Task: {app.TASK.name}" in (t or "") for t in texts), texts)

    def test_empty_input_is_rejected_without_calling_the_model(self):
        client = FakeClient("{}")
        with patch_client(client):
            status, result, _raw, _ = final_yield(app.analyze("  ", None))
        self.assertTrue(status.startswith("Error"))
        self.assertIsNone(result)
        self.assertEqual(client.calls, [])

    def test_loading_state_then_done(self):
        client = FakeClient(json.dumps({"summary": "s", "steps": [], "confidence": 0.5}))
        with patch_client(client):
            states = list(app.analyze("hello", None))
        self.assertTrue(states[0][0].startswith("Working"))
        self.assertEqual(states[-1][0], "Done.")

    def test_provider_error_is_reported_not_raised(self):
        import gemma

        with mock.patch("gemma.get_client", side_effect=gemma.GemmaError("no key")):
            status, result, _raw, _ = final_yield(app.analyze("hello", None))
        self.assertIn("no key", status)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
