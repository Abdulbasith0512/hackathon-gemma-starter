# Gemma 4 + Gradio Hackathon Starter

A small, reusable starting point for building with **Gemma 4** through the Gemini API. It is infrastructure only: clone it, add your key, and spend the hackathon on the idea instead of on setup.

## Features

- Text -> Gemma 4 -> response
- Image -> Gemma 4 -> response
- Text + image -> Gemma 4 -> response
- Structured JSON output (prompted, then parsed and validated)
- Clear errors for a missing API key, API failures, and malformed model output
- Loading state in the UI (status line, button disabled while the request runs)
- API key and model ID come from environment variables

## Architecture

```
app.py       Gradio UI. Calls gemma.py, then parses the result.
gemma.py     The only file that talks to the provider (google-genai).
prompts.py   System prompt (role, task, JSON schema) and per-mode user prompts.
utils.py     Extract / parse / validate JSON from a model response; error formatting.
```

Flow: `app.py` -> `prompts.py` (build prompt) -> `gemma.py` (call model) -> `utils.py` (parse + validate) -> UI.

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

Gradio prints a local URL (by default <http://127.0.0.1:7860>). Open it in a browser.

## Example usage

1. **Text only:** type `My laptop fan is loud and the machine is hot. What should I check?` and click **Analyze**.
2. **Image only:** upload a photo or screenshot and click **Analyze**.
3. **Text + image:** upload an image and add a question about it.

Each run returns JSON in this shape (the generic schema defined in `prompts.py`):

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

| Inputs | Prompt built by | Provider call |
| --- | --- | --- |
| text only | `prompts.TEXT_ONLY` | `gemma.generate_text` |
| image only | `prompts.IMAGE_ONLY` | `gemma.generate_multimodal` |
| text + image | `prompts.TEXT_AND_IMAGE` | `gemma.generate_multimodal` |

In all three cases `prompts.SYSTEM_PROMPT` is sent as the system instruction. For image requests, `gemma.py` converts the PIL image to PNG bytes and sends it as an inline image part followed by the text prompt. The response text is then passed to `utils.parse_model_json`, which strips a ```` ```json ```` fence if the model added one, parses the JSON, and checks it against `REQUIRED_FIELDS`.

JSON output is requested through the prompt only. This starter does not use the API's JSON mode / response schema, because Google's Gemma 4 docs do not document it.

## Adapting it for the actual challenge

1. **Change the task:** edit `SYSTEM_PROMPT` in `prompts.py`. Keep its four parts: the role, the task, the exact output schema, and the rules (concise, state uncertainty, valid JSON only).
2. **Change the schema:** edit the JSON example in `SYSTEM_PROMPT` *and* `REQUIRED_FIELDS` in `utils.py` so the validator matches what you now ask for.
3. **Change the inputs:** edit `build_user_prompt` in `prompts.py` and the components in `app.py`.
4. **Change the model:** set `GEMMA_MODEL` in `.env`. To use a different provider, keep `generate_text` and `generate_multimodal` in `gemma.py` and replace what happens inside them.

## License

MIT. See [LICENSE](LICENSE).
