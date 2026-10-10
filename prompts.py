"""Generic prompt building. Task-specific content lives in task.py, not here."""

import json

DEFAULT_ROLE = "You are a careful analysis assistant."

INPUT_NOTE = (
    "The user's message may contain text, an image, or both. "
    "Base your answer only on what is provided."
)

# Rules that apply to every task. Task-specific rules belong in the task instructions.
RULES = """\
- Be concise. Prefer short sentences.
- Use exactly the keys shown in the schema. Do not add, rename, or drop keys.
- If the input is ambiguous, incomplete, or you are unsure, say so plainly. Do not invent details.
- The response must be valid JSON: double-quoted keys and strings, no trailing commas."""


def build_prompt(
    task_instructions: str,
    output_schema: dict,
    example: dict | None = None,
    role: str = DEFAULT_ROLE,
) -> str:
    """Assemble the system prompt: role, task, input, output format, rules, example.

    `example`, if given, is {"input": ..., "output": ...}.
    """
    if not task_instructions or not task_instructions.strip():
        raise ValueError("task_instructions must not be empty.")
    if not isinstance(output_schema, dict) or not output_schema:
        raise ValueError("output_schema must be a non-empty dict.")

    parts = [
        f"ROLE: {role}",
        f"TASK: {task_instructions.strip()}",
        f"INPUT: {INPUT_NOTE}",
        "OUTPUT FORMAT: Respond with ONLY a single valid JSON object, with no markdown "
        "fences and no text before or after it. Use exactly this schema:\n\n"
        + json.dumps(output_schema, indent=2),
        f"RULES:\n{RULES}",
    ]
    if example is not None:
        if not (isinstance(example, dict) and {"input", "output"} <= example.keys()):
            raise ValueError("example must be a dict with 'input' and 'output' keys.")
        out = example["output"]
        out_text = out if isinstance(out, str) else json.dumps(out, indent=2)
        parts.append(f"EXAMPLE:\nInput: {example['input']}\nOutput:\n{out_text}")
    return "\n\n".join(parts) + "\n"


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
