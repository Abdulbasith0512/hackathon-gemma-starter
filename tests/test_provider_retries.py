"""Timeout and retries: transient failures are retried (by the SDK, once), permanent ones are not."""

import ast
import unittest
from pathlib import Path
from unittest import mock

import httpx
from google import genai

import gemma
from tests.helpers import FakeApi, ProviderTestCase, patch_api, tiny_image

TRANSIENT = (408, 429, 500, 502, 503, 504)
PERMANENT = (400, 401, 403, 404)


class PolicyTests(ProviderTestCase):
    def test_timeout_and_attempts(self):
        options = gemma._http_options()
        self.assertEqual(options.timeout, 60_000)  # milliseconds, per attempt
        self.assertEqual(options.retry_options.attempts, 3)  # total tries, first included

    def test_only_transient_statuses_are_retried(self):
        codes = set(gemma._http_options().retry_options.http_status_codes)
        self.assertEqual(codes, set(TRANSIENT))
        self.assertFalse(codes & set(PERMANENT))

    def test_client_is_built_with_the_policy(self):
        with mock.patch.object(gemma.genai, "Client") as client_class:
            gemma.get_client()
        kwargs = client_class.call_args.kwargs
        self.assertEqual(kwargs["api_key"], "test-key")
        self.assertEqual(kwargs["http_options"].timeout, 60_000)
        self.assertEqual(kwargs["http_options"].retry_options.attempts, 3)

    def test_timeout_reaches_the_wire(self):
        api = FakeApi(200)
        with patch_api(api):
            gemma.generate_text("hi")
        self.assertEqual(api.requests[0].headers["x-server-timeout"], "60")

    def test_real_client_object_is_still_returned(self):
        self.assertIsInstance(gemma.get_client(), genai.Client)


class TransientFailureTests(ProviderTestCase):
    def test_each_transient_status_is_retried_then_succeeds(self):
        for code in TRANSIENT:
            api = FakeApi(code, 200, reply="recovered")
            with patch_api(api):
                self.assertEqual(gemma.generate_text("hi"), "recovered", code)
            self.assertEqual(len(api.requests), 2, code)

    def test_two_failures_then_success(self):
        api = FakeApi(503, 503, 200)
        with patch_api(api):
            self.assertEqual(gemma.generate_text("hi"), "hello")
        self.assertEqual(len(api.requests), 3)
        self.assertEqual(api.sleep.call_count, 2)  # backoff before each retry

    def test_backoff_waits_before_retrying(self):
        api = FakeApi(503, 503, 200)
        with patch_api(api):
            gemma.generate_text("hi")
        waits = [call.args[0] for call in api.sleep.call_args_list]
        self.assertTrue(all(w >= 1.0 for w in waits), waits)
        self.assertLess(waits[0], waits[1] + 1)

    def test_gives_up_after_three_attempts(self):
        api = FakeApi(503)
        with patch_api(api), self.assertRaisesRegex(gemma.GemmaError, "503"):
            gemma.generate_text("hi")
        self.assertEqual(len(api.requests), 3)

    def test_connection_error_is_retried(self):
        api = FakeApi(httpx.ConnectError("getaddrinfo failed"), 200)
        with patch_api(api):
            self.assertEqual(gemma.generate_text("hi"), "hello")
        self.assertEqual(len(api.requests), 2)

    def test_timeout_is_retried_and_then_reported(self):
        api = FakeApi(httpx.ReadTimeout("slow"))
        with patch_api(api), self.assertRaisesRegex(gemma.GemmaError, "ReadTimeout"):
            gemma.generate_text("hi")
        self.assertEqual(len(api.requests), 3)

    def test_image_requests_are_retried_too(self):
        api = FakeApi(502, 200)
        with patch_api(api):
            self.assertEqual(gemma.generate_multimodal("p", tiny_image()), "hello")
        self.assertEqual(len(api.requests), 2)


class PermanentFailureTests(ProviderTestCase):
    def test_permanent_errors_are_tried_once(self):
        for code in PERMANENT:
            api = FakeApi(code)
            with patch_api(api), self.assertRaisesRegex(gemma.GemmaError, str(code)):
                gemma.generate_text("hi")
            self.assertEqual(len(api.requests), 1, code)
            self.assertEqual(api.sleep.call_count, 0, code)

    def test_invalid_api_key_is_not_retried(self):
        api = FakeApi((400, "API key not valid. Please pass a valid API key."))
        with patch_api(api), self.assertRaisesRegex(gemma.GemmaError, "API key not valid"):
            gemma.generate_text("hi")
        self.assertEqual(len(api.requests), 1)

    def test_unknown_model_is_not_retried(self):
        api = FakeApi((404, "models/nope is not found"))
        with patch_api(api), self.assertRaisesRegex(gemma.GemmaError, "404"):
            gemma.generate_text("hi")
        self.assertEqual(len(api.requests), 1)


class NoNestedRetryTests(ProviderTestCase):
    """The SDK is the only retry layer, so a failure costs at most MAX_ATTEMPTS requests."""

    def test_failing_text_request_makes_exactly_max_attempts_requests(self):
        api = FakeApi(500)
        with patch_api(api), self.assertRaises(gemma.GemmaError):
            gemma.generate_text("hi")
        self.assertEqual(len(api.requests), gemma.MAX_ATTEMPTS)

    def test_failing_image_request_makes_exactly_max_attempts_requests(self):
        api = FakeApi(500)
        with patch_api(api), self.assertRaises(gemma.GemmaError):
            gemma.generate_multimodal("p", tiny_image())
        self.assertEqual(len(api.requests), gemma.MAX_ATTEMPTS)

    def test_thinking_fallback_adds_one_request_not_a_second_round_of_retries(self):
        rejection = (400, "Thinking level is not supported for this model.")
        api = FakeApi(rejection, 503)
        with mock.patch.dict("os.environ", {"GEMMA_THINKING": "low"}), patch_api(api):
            with self.assertLogs("gemma", "WARNING"), self.assertRaisesRegex(gemma.GemmaError, "503"):
                gemma.generate_text("hi")
        # 1 rejected request + the repeat request retried up to MAX_ATTEMPTS times.
        self.assertEqual(len(api.requests), 1 + gemma.MAX_ATTEMPTS)

    def test_provider_has_no_retry_loop_of_its_own(self):
        # A tripwire: gemma.py has no loops and never sleeps, so any retry comes from the SDK.
        tree = ast.parse(Path(gemma.__file__).read_text(encoding="utf-8"))
        loops = [n for n in ast.walk(tree) if isinstance(n, (ast.For, ast.While))]
        sleeps = [n for n in ast.walk(tree) if isinstance(n, ast.Attribute) and n.attr == "sleep"]
        self.assertEqual(loops, [])
        self.assertEqual(sleeps, [])


class KnownLimitationTests(ProviderTestCase):
    def test_server_disconnect_is_not_retried_by_the_sdk(self):
        # The SDK's retry covers HTTP statuses, timeouts and connection errors, but not a
        # server that drops the connection mid-request. It is reported straight away.
        # If a future SDK retries this, update the README note on retries.
        api = FakeApi(httpx.RemoteProtocolError("Server disconnected without sending a response."))
        with patch_api(api), self.assertRaisesRegex(gemma.GemmaError, "RemoteProtocolError"):
            gemma.generate_text("hi")
        self.assertEqual(len(api.requests), 1)


if __name__ == "__main__":
    unittest.main()
