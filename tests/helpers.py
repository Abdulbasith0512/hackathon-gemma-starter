"""Shared test helpers. No test calls the real API.

Two ways to fake the provider:
- FakeClient / patch_client: replaces the whole google-genai client (simple, fast).
- FakeApi / patch_api: replaces only the HTTP layer, so the real SDK code runs
  (request bodies, timeouts, retries) against a scripted fake endpoint.
"""

import functools
import io
import json
import unittest
from contextlib import contextmanager
from types import SimpleNamespace
from unittest import mock

import httpx
from PIL import Image, ImageChops, ImageDraw

import gemma


class FakeClient:
    """Stands in for genai.Client. Records every call; replies with `reply` (str or callable)."""

    def __init__(self, reply="{}"):
        self.reply = reply
        self.calls = []
        self.models = self  # client.models.generate_content(...)

    def generate_content(self, model, contents, config):
        self.calls.append(SimpleNamespace(model=model, contents=contents, config=config))
        text = self.reply(self.calls[-1]) if callable(self.reply) else self.reply
        return SimpleNamespace(text=text, candidates=[])


def patch_client(client):
    """Make gemma.get_client() return `client` for the duration of a `with` block."""
    return mock.patch("gemma.get_client", return_value=client)


class FakeApi:
    """A scripted fake of the Gemini HTTP endpoint, driven through the real SDK.

    Request N gets script[N] (the last item repeats). An item is:
      - 200                      -> a normal response whose text is `reply`
      - an int status            -> an error response with that status
      - (status, "message")      -> an error response with that status and message
      - an Exception instance    -> raised, like a network failure
    Every request is kept in `.requests`; `.bodies` has their decoded JSON.
    """

    def __init__(self, *script, reply="hello"):
        self.script = list(script) or [200]
        self.reply = reply
        self.requests = []
        self.sleep = None  # set by patch_api: the mock that replaced time.sleep

    def __call__(self, request: httpx.Request) -> httpx.Response:
        step = self.script[min(len(self.requests), len(self.script) - 1)]
        self.requests.append(request)
        if isinstance(step, Exception):
            raise step
        if step == 200:
            return httpx.Response(
                200,
                json={
                    "candidates": [
                        {
                            "content": {"role": "model", "parts": [{"text": self.reply}]},
                            "finishReason": "STOP",
                        }
                    ],
                    "usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 1},
                },
            )
        status, message = step if isinstance(step, tuple) else (step, f"fake error {step}")
        body = {"error": {"code": status, "message": message, "status": "FAKE"}}
        return httpx.Response(status, json=body)

    @property
    def bodies(self):
        return [json.loads(r.content) for r in self.requests]

    def thinking_config(self, index=0):
        """The thinkingConfig dict sent in request `index`, or None if there was none."""
        return self.bodies[index].get("generationConfig", {}).get("thinkingConfig")

    def thinking_level(self, index=0):
        """The thinking level string sent in request `index` (e.g. "MINIMAL"), or None."""
        config = self.thinking_config(index)
        return config and (config.get("thinking_level") or config.get("thinkingLevel"))


_active = SimpleNamespace(api=None, client=None)


def _sdk_client():
    """One real SDK client, built by gemma.get_client() with gemma's own timeout and retry
    options, but talking to whichever FakeApi is active instead of the network.

    Built once and shared: constructing an SDK client takes ~0.4s (it loads CA certificates).
    """
    if _active.client is None:
        transport = httpx.MockTransport(lambda request: _active.api(request))
        options = gemma._http_options().model_copy(
            update={"httpx_client": httpx.Client(transport=transport)}
        )
        with mock.patch.object(gemma, "_http_options", return_value=options):
            _active.client = gemma.get_client()
    return _active.client


@contextmanager
def patch_api(api: FakeApi):
    """Run gemma against `api` through the real SDK (request building, timeout, retries).

    time.sleep is mocked, so retry backoff is instant; the mock is available as `api.sleep`.
    """
    previous, _active.api = _active.api, api
    try:
        with patch_client(_sdk_client()), mock.patch("time.sleep") as sleep:
            api.sleep = sleep
            yield api
    finally:
        _active.api = previous


class ProviderTestCase(unittest.TestCase):
    """Base class for provider tests: forget which thinking levels a model rejected."""

    def setUp(self):
        gemma._THINKING_REJECTED.clear()
        self.addCleanup(gemma._THINKING_REJECTED.clear)


def tiny_image():
    return Image.new("RGB", (8, 8), "red")


@functools.lru_cache(maxsize=None)
def photo_like(width, height):
    """Smooth colour blobs plus sensor-like noise, like a photo: JPEG is far smaller than PNG.

    Cached because generating noise is slow; treat the result as read-only.
    """
    blobs = Image.effect_noise((24, 18), 80).convert("RGB")  # any smooth-ish base
    base = blobs.resize((width, height), Image.Resampling.BICUBIC)
    noise = Image.merge("RGB", [Image.effect_noise((width, height), 6) for _ in range(3)])
    return ImageChops.add(base, noise, scale=1.0, offset=-128)


def screenshot_like(width, height):
    """White page, thin boxes and small text: tiny as PNG, so it must not be sent as lossy JPEG."""
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    for top in range(10, height - 30, 30):
        draw.rectangle([20, top, width // 2, top + 20], outline="black")
        draw.text((26, top + 4), f"row {top}: small text 0123456789", fill="black")
    return image


def decode_part(part) -> Image.Image:
    """The PIL image inside an inline image part (what the model would receive)."""
    return Image.open(io.BytesIO(part.inline_data.data))
