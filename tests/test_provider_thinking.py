"""GEMMA_THINKING: the default, configuring it, and a model that rejects the setting."""

import os
import unittest
from unittest import mock

from google.genai import types
from PIL import Image

import gemma
from tests.helpers import FakeApi, FakeClient, ProviderTestCase, patch_api, patch_client, tiny_image

REJECTION = (400, "Thinking level is not supported for this model.")


def thinking(value):
    """Set GEMMA_THINKING for a `with` block."""
    return mock.patch.dict(os.environ, {"GEMMA_THINKING": value})


class ThinkingSettingTests(ProviderTestCase):
    def test_default_is_minimal(self):
        self.assertEqual(gemma.DEFAULT_THINKING, "minimal")
        with thinking(""):
            self.assertEqual(gemma.get_thinking(), "minimal")

    def test_unset_variable_is_minimal(self):
        with mock.patch.dict(os.environ):
            os.environ.pop("GEMMA_THINKING", None)
            self.assertEqual(gemma.get_thinking(), "minimal")

    def test_every_documented_value_is_accepted(self):
        for value in (*gemma.THINKING_LEVELS, "default"):
            with thinking(value):
                self.assertEqual(gemma.get_thinking(), value)

    def test_case_and_surrounding_spaces_are_ignored(self):
        with thinking("  HIGH "):
            self.assertEqual(gemma.get_thinking(), "high")

    def test_unknown_value_gives_a_clear_error(self):
        with thinking("mimimal"):
            with self.assertRaises(gemma.GemmaError) as ctx:
                gemma.get_thinking()
        message = str(ctx.exception)
        self.assertIn("GEMMA_THINKING='mimimal'", message)
        self.assertIn("minimal, low, medium, high, default", message)

    def test_every_level_exists_in_the_installed_sdk(self):
        for level in gemma.THINKING_LEVELS:
            self.assertIn(level.upper(), types.ThinkingLevel.__members__)


class ThinkingConfigSentTests(ProviderTestCase):
    def sent_config(self, setting, call):
        client = FakeClient("ok")
        with thinking(setting), patch_client(client):
            call()
        return client.calls[0].config.thinking_config

    def test_minimal_is_sent_by_default(self):
        config = self.sent_config("", lambda: gemma.generate_text("hi"))
        self.assertEqual(config.thinking_level, types.ThinkingLevel.MINIMAL)

    def test_configured_level_is_sent(self):
        config = self.sent_config("high", lambda: gemma.generate_text("hi"))
        self.assertEqual(config.thinking_level, types.ThinkingLevel.HIGH)

    def test_default_sends_no_thinking_setting(self):
        self.assertIsNone(self.sent_config("default", lambda: gemma.generate_text("hi")))

    def test_applies_to_image_requests_too(self):
        config = self.sent_config("", lambda: gemma.generate_multimodal("p", tiny_image()))
        self.assertEqual(config.thinking_level, types.ThinkingLevel.MINIMAL)

    def test_invalid_setting_fails_before_any_request(self):
        client = FakeClient("ok")
        with thinking("bogus"), patch_client(client), self.assertRaises(gemma.GemmaError):
            gemma.generate_text("hi")
        self.assertEqual(client.calls, [])

    def test_wire_format(self):
        for setting, expected in (("", "MINIMAL"), ("high", "HIGH"), ("default", None)):
            api = FakeApi(200)
            with thinking(setting), patch_api(api):
                gemma.generate_text("hi")
            self.assertEqual(api.thinking_level(0), expected, setting)


class ThinkingRejectionTests(ProviderTestCase):
    """A model that does not support the chosen level: fall back, but only for that error."""

    def test_rejected_level_falls_back_to_the_model_default(self):
        api = FakeApi(REJECTION, 200, reply="fallback ok")
        with thinking("low"), patch_api(api), self.assertLogs("gemma", "WARNING") as logs:
            out = gemma.generate_text("hi", "sys")
        self.assertEqual(out, "fallback ok")
        self.assertEqual(len(api.requests), 2)
        self.assertEqual(api.thinking_level(0), "LOW")
        self.assertIsNone(api.thinking_config(1))
        self.assertIn("GEMMA_THINKING=low", logs.output[0])
        self.assertIn(gemma.get_model(), logs.output[0])

    def test_budget_style_rejection_is_handled_the_same_way(self):
        api = FakeApi((400, "Thinking budget is not supported for this model."), 200)
        with thinking("medium"), patch_api(api), self.assertLogs("gemma", "WARNING"):
            self.assertEqual(gemma.generate_text("hi"), "hello")
        self.assertEqual(len(api.requests), 2)

    def test_the_repeat_request_is_otherwise_identical(self):
        api = FakeApi(REJECTION, 200)
        with thinking("low"), patch_api(api), self.assertLogs("gemma", "WARNING"):
            gemma.generate_multimodal("what is this?", tiny_image(), "the system text")
        first, second = api.bodies
        self.assertEqual(first["contents"], second["contents"])
        self.assertEqual(first["systemInstruction"], second["systemInstruction"])
        self.assertIn("inlineData", first["contents"][0]["parts"][0])

    def test_rejection_is_remembered_and_warned_about_once(self):
        api = FakeApi(REJECTION, 200)
        with thinking("low"), patch_api(api):
            with self.assertLogs("gemma", "WARNING"):
                gemma.generate_text("first")
            with self.assertNoLogs("gemma", "WARNING"):
                gemma.generate_text("second")
        self.assertEqual(len(api.requests), 3)  # 2 for the first call, 1 for the second
        self.assertIsNone(api.thinking_config(2))

    def test_other_levels_are_not_affected_by_a_rejection(self):
        api = FakeApi(REJECTION, 200, 200)
        with patch_api(api), self.assertLogs("gemma", "WARNING"):
            with thinking("low"):
                gemma.generate_text("one")
            with thinking("minimal"):
                gemma.generate_text("two")
        self.assertEqual(api.thinking_level(2), "MINIMAL")

    def test_other_models_are_not_affected_by_a_rejection(self):
        api = FakeApi(REJECTION, 200, 200)
        with thinking("low"), patch_api(api), self.assertLogs("gemma", "WARNING"):
            gemma.generate_text("one")
            with mock.patch.dict(os.environ, {"GEMMA_MODEL": "some-other-model"}):
                gemma.generate_text("two")
        self.assertEqual(api.thinking_level(2), "LOW")

    def test_unrelated_400_is_not_hidden(self):
        api = FakeApi((400, "API key not valid. Please pass a valid API key."))
        with patch_api(api), self.assertNoLogs("gemma", "WARNING"):
            with self.assertRaisesRegex(gemma.GemmaError, "400 API key not valid"):
                gemma.generate_text("hi")
        self.assertEqual(len(api.requests), 1)
        self.assertEqual(gemma._THINKING_REJECTED, set())

    def test_other_status_codes_are_not_treated_as_a_rejection(self):
        # Even if the message mentions thinking, only a 400 means "unsupported setting".
        api = FakeApi((500, "thinking service unavailable"))
        with patch_api(api), self.assertRaisesRegex(gemma.GemmaError, "500 thinking service"):
            gemma.generate_text("hi")
        self.assertEqual(len(api.requests), gemma.MAX_ATTEMPTS)
        self.assertTrue(all(api.thinking_config(i) for i in range(len(api.requests))))

    def test_no_fallback_when_no_thinking_setting_was_sent(self):
        api = FakeApi(REJECTION)
        with thinking("default"), patch_api(api):
            with self.assertRaisesRegex(gemma.GemmaError, "400 Thinking level"):
                gemma.generate_text("hi")
        self.assertEqual(len(api.requests), 1)

    def test_error_from_the_repeat_request_is_reported(self):
        api = FakeApi(REJECTION, (400, "Request payload is invalid."))
        with thinking("low"), patch_api(api), self.assertLogs("gemma", "WARNING"):
            with self.assertRaisesRegex(gemma.GemmaError, "400 Request payload is invalid"):
                gemma.generate_text("hi")
        self.assertEqual(len(api.requests), 2)

    def test_works_with_non_rgb_images_after_a_rejection(self):
        api = FakeApi(REJECTION, 200)
        with thinking("low"), patch_api(api), self.assertLogs("gemma", "WARNING"):
            out = gemma.generate_multimodal("p", Image.new("RGBA", (4, 4)))
        self.assertEqual(out, "hello")


if __name__ == "__main__":
    unittest.main()
