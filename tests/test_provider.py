"""The provider (gemma.py) must work for any prompt and know nothing about the task."""

import ast
import os
import unittest
from pathlib import Path
from unittest import mock

from google.genai import errors

import gemma
from tests.helpers import FakeClient, patch_client, tiny_image

GEMMA_SOURCE = Path(gemma.__file__)


class ProviderSeparationTests(unittest.TestCase):
    def test_provider_does_not_import_task_layers(self):
        tree = ast.parse(GEMMA_SOURCE.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertFalse(imported & {"task", "prompts", "utils", "app"}, imported)

    def test_provider_source_has_no_task_specific_terms(self):
        source = GEMMA_SOURCE.read_text(encoding="utf-8").lower()
        for term in ("summary", "steps", "confidence", "internship", "qubit", "resume", "hazard"):
            self.assertNotIn(term, source)


class ProviderRequestTests(unittest.TestCase):
    def test_text_request_passes_arbitrary_prompt_through(self):
        client = FakeClient("hello back")
        with patch_client(client):
            out = gemma.generate_text("any prompt at all: 42?", "any system text")
        self.assertEqual(out, "hello back")
        (call,) = client.calls
        self.assertEqual(call.contents, ["any prompt at all: 42?"])
        self.assertEqual(call.config.system_instruction, "any system text")
        self.assertEqual(call.model, gemma.get_model())

    def test_text_request_without_system_instruction(self):
        client = FakeClient("ok")
        with patch_client(client):
            gemma.generate_text("hi")
        self.assertIsNone(client.calls[0].config.system_instruction)

    def test_multimodal_request_sends_png_then_prompt(self):
        client = FakeClient("seen")
        with patch_client(client):
            out = gemma.generate_multimodal("what is this?", tiny_image(), "sys")
        self.assertEqual(out, "seen")
        image_part, prompt = client.calls[0].contents
        self.assertEqual(image_part.inline_data.mime_type, "image/png")
        self.assertTrue(image_part.inline_data.data.startswith(b"\x89PNG"))
        self.assertEqual(prompt, "what is this?")
        self.assertEqual(client.calls[0].config.system_instruction, "sys")

    def test_multimodal_accepts_non_rgb_images(self):
        from PIL import Image

        client = FakeClient("ok")
        with patch_client(client):
            gemma.generate_multimodal("p", Image.new("RGBA", (4, 4), (0, 0, 0, 0)))
        self.assertEqual(client.calls[0].contents[0].inline_data.mime_type, "image/png")


class ProviderErrorTests(unittest.TestCase):
    def test_api_error_becomes_gemma_error(self):
        client = FakeClient()
        client.generate_content = mock.Mock(
            side_effect=errors.APIError(429, {"error": {"message": "quota hit", "status": "X"}})
        )
        with patch_client(client), self.assertRaisesRegex(gemma.GemmaError, "429 quota hit"):
            gemma.generate_text("hi")

    def test_unexpected_exception_becomes_gemma_error(self):
        client = FakeClient()
        client.generate_content = mock.Mock(side_effect=ConnectionError("down"))
        with patch_client(client), self.assertRaisesRegex(gemma.GemmaError, "ConnectionError"):
            gemma.generate_text("hi")

    def test_empty_response_becomes_gemma_error(self):
        with patch_client(FakeClient("   ")), self.assertRaisesRegex(gemma.GemmaError, "empty"):
            gemma.generate_text("hi")

    def test_missing_or_placeholder_key(self):
        for value in ("", "your_api_key_here"):
            with mock.patch.dict(os.environ, {"GOOGLE_API_KEY": value}):
                with self.assertRaisesRegex(gemma.GemmaError, "GOOGLE_API_KEY"):
                    gemma.get_client()


class ModelConfigTests(unittest.TestCase):
    def test_model_default_and_override(self):
        with mock.patch.dict(os.environ, {"GEMMA_MODEL": ""}):
            self.assertEqual(gemma.get_model(), gemma.DEFAULT_MODEL)
        with mock.patch.dict(os.environ, {"GEMMA_MODEL": "your_model_here"}):
            self.assertEqual(gemma.get_model(), gemma.DEFAULT_MODEL)
        with mock.patch.dict(os.environ, {"GEMMA_MODEL": "gemma-4-31b-it"}):
            self.assertEqual(gemma.get_model(), "gemma-4-31b-it")


if __name__ == "__main__":
    unittest.main()
