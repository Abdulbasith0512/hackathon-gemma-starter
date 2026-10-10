"""Prompt constants and helpers. Edit this file when the challenge is revealed.

If you change the output schema here, change REQUIRED_FIELDS in utils.py to match.
"""

# Sent as the model's system instruction on every request.
SYSTEM_PROMPT = """\
ROLE: You are a careful analysis assistant.

TASK: Analyze the user's input (text, an image, or both) and produce a short, \
useful analysis: a one-paragraph summary and a list of concrete next steps.

OUTPUT FORMAT: Respond with ONLY a single valid JSON object, with no markdown \
fences and no text before or after it. Use exactly this schema:

{
  "summary": "string - concise summary of the input and your analysis",
  "steps": ["string - one concrete step per item, in order"],
  "confidence": 0.0
}

RULES:
- Be concise. Prefer short sentences.
- "confidence" is a number from 0.0 (guessing) to 1.0 (certain).
- If the input is ambiguous, incomplete, or you are unsure, say so in "summary" \
and lower "confidence". Do not invent details.
- If there is nothing to do, return "steps": [].
- The response must be valid JSON: double-quoted keys and strings, no trailing commas.
"""

# User-turn prompts for each input mode.
TEXT_ONLY = "{text}"
IMAGE_ONLY = "Analyze the attached image."
TEXT_AND_IMAGE = "Analyze the attached image together with this text:\n\n{text}"


def build_user_prompt(text: str, has_image: bool) -> str:
    """Pick the user prompt for the given combination of inputs."""
    text = (text or "").strip()
    if text and has_image:
        return TEXT_AND_IMAGE.format(text=text)
    if has_image:
        return IMAGE_ONLY
    return TEXT_ONLY.format(text=text)
