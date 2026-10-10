"""THE task configuration. Edit this file when the hackathon challenge is revealed.

Change the constants below; gemma.py, utils.py, prompts.py and app.py should not
need to change. The output schema is used twice: it is shown to the model in the
prompt, and it is what the model's JSON reply is validated against.
"""

from dataclasses import dataclass

# Shown in the UI so you can see which task is active.
TASK_NAME = "Generic Multimodal Analyzer"

# What the model should do. Plain prose; task-specific rules go here too.
TASK_INSTRUCTIONS = """\
Analyze the provided text and/or image and produce a short, useful analysis: a \
one-paragraph summary and a list of concrete next steps.

- "confidence" is a number from 0.0 (guessing) to 1.0 (certain). Lower it when \
the input is ambiguous or incomplete.
- If there is nothing to do, return "steps": [].
"""

# The JSON the model must return. Each value shows the expected type:
#   a string (any text, so it can double as a description) -> str
#   a number such as 0.0 or 0                              -> int or float
#   true / false                                           -> bool
#   a list with one sample item, e.g. ["string"]           -> list whose items match the sample
#   an object                                              -> nested object, checked the same way
# A numeric field named "confidence" must be between 0.0 and 1.0.
OUTPUT_SCHEMA = {
    "summary": "string - concise summary of the input and your analysis",
    "steps": ["string - one concrete step per item, in order"],
    "confidence": 0.0,
}

# Optional worked example, shown to the model. Set to None to omit it. Shape:
# EXAMPLE = {
#     "input": "My laptop fan is loud and the machine is hot.",
#     "output": {"summary": "...", "steps": ["..."], "confidence": 0.8},
# }
EXAMPLE = None


@dataclass(frozen=True)
class Task:
    name: str
    instructions: str
    output_schema: dict
    example: dict | None = None

    def __post_init__(self):
        if not self.name.strip():
            raise ValueError("Task name must not be empty.")
        if not self.instructions.strip():
            raise ValueError("Task instructions must not be empty.")
        if not isinstance(self.output_schema, dict) or not self.output_schema:
            raise ValueError("Task output_schema must be a non-empty dict.")
        if self.example is not None and not (
            isinstance(self.example, dict) and {"input", "output"} <= self.example.keys()
        ):
            raise ValueError("Task example must be a dict with 'input' and 'output' keys.")


# The active task, used by the app. (Tests build their own Task objects.)
TASK = Task(
    name=TASK_NAME,
    instructions=TASK_INSTRUCTIONS,
    output_schema=OUTPUT_SCHEMA,
    example=EXAMPLE,
)
