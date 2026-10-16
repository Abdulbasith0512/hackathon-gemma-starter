"""Thin wrapper around the Google GenAI SDK for Gemma 4.

This is the only file that talks to the model provider. To swap models or
providers later, keep the two public functions (generate_text,
generate_multimodal) and change what happens inside.

It is task-agnostic: it sends whatever prompt and system instruction the caller
supplies and returns the raw text. It knows nothing about tasks or output schemas.

Latency and reliability settings (thinking level, image size, timeout, retries)
live here too, so the rest of the app does not need to know about them.
"""

import io
import logging
import os

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types
from PIL import Image

load_dotenv()

logger = logging.getLogger(__name__)

# Gemma 4 IDs served by the Gemini API (from Google's "Run Gemma with the Gemini
# API" docs): "gemma-4-26b-a4b-it" and "gemma-4-31b-it". Override with GEMMA_MODEL.
DEFAULT_MODEL = "gemma-4-26b-a4b-it"

_PLACEHOLDER_KEY = "your_api_key_here"

# Thinking. Gemma 4 "thinks" before it answers, which was about 80% of the request
# time in measurements. GEMMA_THINKING is one of THINKING_LEVELS, or "default" to
# send no setting and let the model decide (slowest). Models differ in which levels
# they accept; if one is rejected the request is repeated without it (see _generate).
THINKING_LEVELS = ("minimal", "low", "medium", "high")
DEFAULT_THINKING = "minimal"

# Images. Larger images are scaled down to this many pixels on the longest side.
# Trade-off: small text in a very large screenshot can become hard to read; crop to
# the relevant area first, or raise this value.
MAX_IMAGE_DIMENSION = 1536
JPEG_QUALITY = 90
# Send JPEG only when it is under this fraction of the lossless PNG size. That is
# true for photos but not for screenshots, diagrams or text, which stay lossless.
JPEG_MAX_SIZE_RATIO = 0.5

# Network. The timeout applies to each attempt; keep it at 10 s or more, because the
# API rejects shorter deadlines. These statuses are transient; others (400 invalid
# request or unsupported setting, 401/403 bad key, 404 unknown model) will not
# succeed on a second try, so they are not retried.
REQUEST_TIMEOUT_MS = 60_000
MAX_ATTEMPTS = 3
RETRY_STATUS_CODES = (408, 429, 500, 502, 503, 504)

# (model, level) pairs the API rejected, so later requests skip the rejected setting.
_THINKING_REJECTED: set[tuple[str, str]] = set()


class GemmaError(Exception):
    """Raised for any configuration or API failure, with a user-readable message."""


def get_model() -> str:
    model = os.getenv("GEMMA_MODEL", "").strip()
    if not model or model.startswith("your_"):
        return DEFAULT_MODEL
    return model


def get_thinking() -> str:
    """The GEMMA_THINKING setting: one of THINKING_LEVELS, or "default" (send nothing)."""
    value = os.getenv("GEMMA_THINKING", "").strip().lower()
    if not value:
        return DEFAULT_THINKING
    if value != "default" and value not in THINKING_LEVELS:
        raise GemmaError(
            f"GEMMA_THINKING='{value}' is not valid. "
            f"Use one of: {', '.join(THINKING_LEVELS)}, default."
        )
    return value


def _http_options() -> types.HttpOptions:
    """Timeout and retry policy. The SDK's retry is the only retry layer in the app."""
    return types.HttpOptions(
        timeout=REQUEST_TIMEOUT_MS,
        retry_options=types.HttpRetryOptions(
            attempts=MAX_ATTEMPTS,  # total tries, including the first
            http_status_codes=list(RETRY_STATUS_CODES),
        ),
    )


def get_client() -> genai.Client:
    """Build a client from GOOGLE_API_KEY. Raises GemmaError if it is missing."""
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key or api_key == _PLACEHOLDER_KEY:
        raise GemmaError(
            "GOOGLE_API_KEY is not set. Copy .env.example to .env and add your key "
            "(get one at https://aistudio.google.com/apikey)."
        )
    return genai.Client(api_key=api_key, http_options=_http_options())


def _thinking_config(model: str, level: str) -> types.ThinkingConfig | None:
    if level == "default" or (model, level) in _THINKING_REJECTED:
        return None
    return types.ThinkingConfig(thinking_level=types.ThinkingLevel[level.upper()])


def _is_thinking_rejection(error: errors.APIError) -> bool:
    """True for the 400 the API returns when a model does not support a thinking setting."""
    return error.code == 400 and "thinking" in (error.message or "").lower()


def _send(client, model, contents, system_instruction, thinking):
    config = types.GenerateContentConfig(
        system_instruction=system_instruction, thinking_config=thinking
    )
    return client.models.generate_content(model=model, contents=contents, config=config)


def _generate(contents: list, system_instruction: str | None) -> str:
    client = get_client()
    model = get_model()
    level = get_thinking()
    thinking = _thinking_config(model, level)
    try:
        try:
            response = _send(client, model, contents, system_instruction, thinking)
        except errors.APIError as e:
            if thinking is None or not _is_thinking_rejection(e):
                raise
            # Only this specific error is handled here: the model does not support the
            # configured thinking level. Warn, remember it, and repeat the request once
            # without the setting. Every other error propagates unchanged.
            logger.warning(
                "Model '%s' does not support GEMMA_THINKING=%s; using the model's default "
                "thinking instead (slower). Set GEMMA_THINKING=default to silence this.",
                model,
                level,
            )
            _THINKING_REJECTED.add((model, level))
            response = _send(client, model, contents, system_instruction, None)
    except errors.APIError as e:
        raise GemmaError(f"Gemma API error (model '{model}'): {e.code} {e.message}") from e
    except Exception as e:  # network errors, SDK validation errors, etc.
        raise GemmaError(f"Request to Gemma failed: {type(e).__name__}: {e}") from e

    text = response.text
    if not text or not text.strip():
        reason = response.candidates[0].finish_reason if response.candidates else "no candidates"
        raise GemmaError(f"Gemma returned an empty response (finish reason: {reason}).")
    return text


def _encode(image: Image.Image, fmt: str, **options) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format=fmt, **options)
    return buffer.getvalue()


def _to_image_part(image: Image.Image) -> types.Part:
    """PIL image -> inline image part, sized and encoded to keep the upload small.

    Images over MAX_IMAGE_DIMENSION are scaled down (never up) with the aspect ratio
    kept. The encoding is lossless PNG unless JPEG is under JPEG_MAX_SIZE_RATIO of its
    size, so photos shrink a lot while screenshots, diagrams and text are not degraded.
    """
    image = image.convert("RGB")  # always a copy, so the caller's image is not modified
    image.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), Image.Resampling.LANCZOS)
    png = _encode(image, "PNG")
    jpeg = _encode(image, "JPEG", quality=JPEG_QUALITY)
    if len(jpeg) < len(png) * JPEG_MAX_SIZE_RATIO:
        return types.Part.from_bytes(data=jpeg, mime_type="image/jpeg")
    return types.Part.from_bytes(data=png, mime_type="image/png")


def generate_text(prompt: str, system_instruction: str | None = None) -> str:
    """Text in -> text out."""
    return _generate([prompt], system_instruction)


def generate_multimodal(
    prompt: str, image: Image.Image, system_instruction: str | None = None
) -> str:
    """Image (+ text) in -> text out. `image` is a PIL image."""
    return _generate([_to_image_part(image), prompt], system_instruction)
