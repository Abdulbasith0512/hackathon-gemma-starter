"""Shared test helpers: a stub for the google-genai client, so no test calls the real API."""

from types import SimpleNamespace
from unittest import mock

from PIL import Image


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


def tiny_image():
    return Image.new("RGB", (8, 8), "red")
