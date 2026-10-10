# Gemma 4 + Gradio Hackathon Starter

A small, reusable starting point for building with **Gemma 4** through the Gemini API. It is infrastructure only: clone it, add your key, and spend the hackathon on the idea instead of on setup.

## Features

- Text -> Gemma 4 -> response
- Image -> Gemma 4 -> response
- Text + image -> Gemma 4 -> response
- Structured JSON output (prompted, then parsed and validated)
- One task file (`task.py`): change the task, prompt, and expected output without touching the provider or UI
- Clear errors for a missing API key, API failures, and malformed model output
- Loading state in the UI (status line, button disabled while the request runs)
- API key and model ID come from environment variables

## Architecture

```
task.py      THE task configuration: name, instructions, output schema, optional example.
app.py       Gradio UI. Reads the task, builds the prompt, calls gemma.py, parses the result.
prompts.py   Generic prompt builder (role, task, input, output format, rules, example).
gemma.py     The only file that talks to the provider (google-genai). Task-agnostic.
utils.py     Extract / parse / validate JSON against a schema; error formatting. Task-agnostic.
tests/       Unit tests with a stubbed client (no network, no API key needed).
```

Flow: Gradio (`app.py`) -> task (`task.py`) -> prompt builder (`prompts.py`) -> provider (`gemma.py`) -> JSON parser (`utils.py`) -> UI.

Only `task.py` is specific to the hackathon challenge.

## Requirements

- Python 3.10 or newer (developed on 3.11)
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)

Dependencies (see `requirements.txt`): `google-genai`, `gradio`, `python-dotenv`, `Pillow`.

## Installation

```bash
git clone <your-repo-url>
cd hackathon-gemma-starter
python -m venv .venv            # optional but recommended
# activate it: .venv\Scripts\activate (Windows) or source .venv/bin/activate (macOS/Linux)
pip install -r requirements.txt
```

## Environment setup

```bash
cp .env.example .env            # on Windows PowerShell, `cp` works too
```

Then edit `.env`:

| Variable | Required | Meaning |
| --- | --- | --- |
| `GOOGLE_API_KEY` | yes | Your Gemini API key. |
| `GEMMA_MODEL` | no | Model ID. Defaults to `gemma-4-26b-a4b-it`. The other Gemma 4 ID served by the Gemini API is `gemma-4-31b-it`. |

`.env` is git-ignored. Never commit a real key. If `GOOGLE_API_KEY` is missing, the app exits at startup with a clear message.

## Running the application

```bash
python app.py
```

Gradio prints a local URL (by default <http://127.0.0.1:7860>; it picks the next free port if 7860 is taken). Open it in a browser. The heading shows the active task (`Task: ...`).

## Example usage

1. **Text only:** type `My laptop fan is loud and the machine is hot. What should I check?` and click **Analyze**.
2. **Image only:** upload a photo or screenshot and click **Analyze**.
3. **Text + image:** upload an image and add a question about it.

Each run returns JSON in this shape (the generic schema defined in `task.py`):

```json
{
  "summary": "...",
  "steps": ["...", "..."],
  "confidence": 0.7
}
```

If the model answers with something that is not valid JSON or does not match the schema, the status box shows the problem and the **Raw model response** panel shows what the model actually said.

## How the text / image / multimodal flow works

`app.py` looks at which inputs were provided:

| Inputs | User prompt built by | Provider call |
| --- | --- | --- |
| text only | `prompts.TEXT_ONLY` | `gemma.generate_text` |
| image only | `prompts.IMAGE_ONLY` | `gemma.generate_multimodal` |
| text + image | `prompts.TEXT_AND_IMAGE` | `gemma.generate_multimodal` |

In all three cases the system instruction is `prompts.build_prompt(...)`, built from the task in `task.py`. For image requests, `gemma.py` converts the PIL image to PNG bytes and sends it as an inline image part followed by the text prompt. The response text is then passed to `utils.parse_model_json`, which strips a ```` ```json ```` fence if the model added one, parses the JSON, and checks it against the task's output schema.

JSON output is requested through the prompt only. This starter does not use the API's JSON mode / response schema, because Google's Gemma 4 docs do not document it.

## Changing the Hackathon Task

1. **Where it lives:** `task.py`. The active task is `TASK`, assembled from the constants at the top of the file.
2. **Task instructions:** edit `TASK_INSTRUCTIONS` (and `TASK_NAME`, which the UI shows as `Task: ...`). Put task-specific rules here too.
3. **Expected JSON:** edit `OUTPUT_SCHEMA`. It is shown to the model *and* used to validate the reply, so there is nothing else to keep in sync. Each value shows the expected type: a string means text, a number means a number, `["string"]` means a list of strings, and nested objects work too. A numeric `confidence` field must be 0.0-1.0.
4. **Optional example:** set `EXAMPLE = {"input": "...", "output": {...}}` to show the model a worked answer.
5. **`gemma.py` should normally not need changes.** It only sends a prompt (plus an optional image) and returns the raw text. The same goes for `utils.py`, `prompts.py`, and `app.py`, unless you need different input widgets.
6. **Run it:** save `task.py`, restart with `python app.py`, and check the `Task: ...` line in the page heading.

Other changes:

- **Different inputs:** edit `build_user_prompt` in `prompts.py` and the components in `app.py`.
- **Different model:** set `GEMMA_MODEL` in `.env`. To use another provider, keep `generate_text` and `generate_multimodal` in `gemma.py` and replace what happens inside them.

## Tests

```bash
python -m unittest discover -v
```

The tests use a stubbed client, so they need no network or API key.

## License

MIT. See [LICENSE](LICENSE).
