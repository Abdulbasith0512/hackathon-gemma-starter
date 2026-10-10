"""Thin wrapper around the Google GenAI SDK for Gemma 4.

This is the only file that talks to the model provider. To swap models or
providers later, keep the two public functions (generate_text,
generate_multimodal) and change what happens inside.

It is task-agnostic: it sends whatever prompt and system instruction the caller
supplies and returns the raw text. It knows nothing about tasks or output schemas.
"""

import io
import os

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types
from PIL import Image

load_dotenv()

# Gemma 4 IDs served by the Gemini API (from Google's "Run Gemma with the Gemini
# API" docs): "gemma-4-26b-a4b-it" and "gemma-4-31b-it". Override with GEMMA_MODEL.
DEFAULT_MODEL = "gemma-4-26b-a4b-it"

_PLACEHOLDER_KEY = "your_api_key_here"


class GemmaError(Exception):
    """Raised for any configuration or API failure, with a user-readable message."""


def get_model() -> str:
    model = os.getenv("GEMMA_MODEL", "").strip()
    if not model or model.startswith("your_"):
        return DEFAULT_MODEL
    return model


def get_client() -> genai.Client:
    """Build a client from GOOGLE_API_KEY. Raises GemmaError if it is missing."""
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key or api_key == _PLACEHOLDER_KEY:
        raise GemmaError(
            "GOOGLE_API_KEY is not set. Copy .env.example to .env and add your key "
            "(get one at https://aistudio.google.com/apikey)."
        )
    return genai.Client(api_key=api_key)


def _generate(contents: list, system_instruction: str | None) -> str:
    client = get_client()
    model = get_model()
    config = types.GenerateContentConfig(system_instruction=system_instruction)
    try:
        response = client.models.generate_content(
            model=model, contents=contents, config=config
        )
    except errors.APIError as e:
        raise GemmaError(f"Gemma API error (model '{model}'): {e.code} {e.message}") from e
    except Exception as e:  # network errors, SDK validation errors, etc.
        raise GemmaError(f"Request to Gemma failed: {type(e).__name__}: {e}") from e

    text = response.text
    if not text or not text.strip():
        reason = response.candidates[0].finish_reason if response.candidates else "no candidates"
        raise GemmaError(f"Gemma returned an empty response (finish reason: {reason}).")
    return text


def _to_png_part(image: Image.Image) -> types.Part:
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="PNG")
    return types.Part.from_bytes(data=buffer.getvalue(), mime_type="image/png")


def generate_text(prompt: str, system_instruction: str | None = None) -> str:
    """Text in -> text out."""
    return _generate([prompt], system_instruction)


def generate_multimodal(
    prompt: str, image: Image.Image, system_instruction: str | None = None
) -> str:
    """Image (+ text) in -> text out. `image` is a PIL image."""
    return _generate([_to_png_part(image), prompt], system_instruction)
