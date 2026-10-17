# Asset Intelligence Copilot

An evidence-first chat copilot for oil-well operations, built for the FlytBase **Asset Intelligence Copilot** challenge (Hacktoberfest 2026 Hack Day). Operators ask plain-English questions about wells, inspections, repairs, regulator events, notes, manuals and SOPs. Every answer is calculated by code, shown with the right visual, and cites the records and manual passages behind it.

It is built on the Gemma 4 starter that comes after this section (provider, retries, thinking level, image handling). The starter's 124 tests are unchanged and still pass; `gemma.py` only gained an optional tool-calling path (`generate_with_tools`), and its existing functions behave as before.

## Run it

```powershell
# 1. Put the official dataset in data/sample-data (git-ignored, never committed).
#    Clone it OUTSIDE this folder so the clone cannot be committed by accident:
git clone https://github.com/FlytBaseAILabs/flytbase-ahc-swe-asset-intelligence-dataset ..\flytbase-ahc-swe-asset-intelligence-dataset
xcopy /E /I ..\flytbase-ahc-swe-asset-intelligence-dataset\sample-data data\sample-data

# 2. Add your key to .env (copy .env.example): GOOGLE_API_KEY=...

# 3. Start the copilot
.venv\Scripts\python.exe -m ahc          # http://127.0.0.1:8000
```

First start ingests the dataset into SQLite (about 2 s, then cached). Pick a user at the top right; each user has private chats, while corrections and notes are shared.

**Loading a second dataset (the final test data):** list every root, separated by `;`. Later roots extend or override earlier ones by record ID, and nothing in the code names a well, area, user or answer.

```powershell
$env:AHC_DATA_DIRS = "data\sample-data;data\test-data"    # either the sample-data folder or its parent
$env:AHC_AS_OF = "2026-10-16"                              # the reference "today"; also editable in the UI header
.venv\Scripts\python.exe -m ahc
```

| Setting | Meaning |
| --- | --- |
| `AHC_DATA_DIRS` | Dataset roots (default `data/sample-data`). |
| `AHC_AS_OF` | Reference date for "today", "right now" and relative periods (default `2026-10-16`, the official sample date). |
| `AHC_DB`, `AHC_MEMORY_DB` | Dataset database (rebuildable) and persistent memory (corrections, rules, notes, chats). |
| `AHC_TPM` | Input tokens per minute to stay under (default 13,500; the free Gemma tier allows 16,000). |
| `GEMMA_*` | Model, thinking level and retries; see the starter section below. |

Replay a list of questions (corrections are saved automatically) and write the answers:

```powershell
.venv\Scripts\python.exe -m ahc.batch questions\sample_scenarios.json --out results\sample-results.md
```

## How it works

```
Question ─► Gemma (picks a tool, fills its arguments)
              │
              ▼
        22 deterministic tools ── ahc/analyst.py: the only code that does arithmetic
              │      │
              │      └─ effective-value layer: dataset record + active corrections (originals kept)
              ▼
        SQLite dataset DB (indexed) · rules read from the manuals/SOPs · persistent memory DB
              │
              ▼
   facts + citations + flags + visuals ─► Gemma words the answer ─► grounding check ─► UI
```

- **Gemma never calculates.** It interprets the question, chooses a tool and writes the explanation. Production status, downtime, spill totals, costs, windows and compliance come from Python.
- **Grounding check.** Gemma's wording is accepted only if every number and record ID in it also appears in the tool results (or the question). Otherwise the verified facts are shown instead, and the UI says so. A data question the model answers without calling a tool is never accepted: the built-in question patterns (`ahc/router.py`) run the same tools instead, and statements get one forced tool-call retry. The same patterns answer when Google's API is unreachable.
- **Rules come from the documents.** The production threshold (T200 15 °C, T350 20 °C), spill classes, SR-01..SR-03 and RC-01..RC-04 deadlines, and the root-cause rule are read from the manuals and SOPs at load time with the quoted passage kept (see the Rules page). If a number cannot be found a visible fallback is used, never a silent one; a new well type with no rule gets "rule not found", not a guess.
- **Downtime** is 7 days per weekly inspection that found the well not producing oil. Missed inspections add nothing and `downtime_hours` is never used. Status is derived from wellhead minus ambient temperature, not from `recorded_status`.
- **Reports are followed through `report_file`**, never by guessing file names; containment times and compliance rows are parsed from each report.
- **Visuals** are chosen from the answer's shape (list → table, change over time → line, comparison → bar, location → map, two dimensions → heatmap, one well → status card), and an explicitly requested visual always wins. Every answer can be switched between its available views.

## How each challenge requirement is met

| Requirement | Where |
| --- | --- |
| Chat over metadata, inspections, repairs, reports, regulator events, notes, manuals, SOPs | `ahc/ingest.py` loads all of it; 22 tools plus full-text search of manuals, SOPs and reports |
| Right visual, explicit request respected | `ahc/visuals.py`; status card, table, line, bar, map, heatmap |
| Cite exact records and documents | every tool returns citations; the evidence drawer opens the record or the manual section (`ahc/evidence.py`) |
| Correct status, downtime, spills, costs, windows, compliance | `ahc/analyst.py`, `ahc/periods.py`, `ahc/rules.py`; golden tests against the official examples |
| Shared knowledge and corrections persist across users | `ahc/store.py` (SQLite): corrections, scoped rules, shared notes and claims |
| Private memory per user | conversations and "wells we discussed" are keyed by the session user; the model never supplies a user ID; other users get 403 |
| Originals preserved; who, what, why, when, scope | corrections keep the dataset value, the value before, the new value, author, reason, timestamp and scope; a later correction supersedes but the history stays |
| Corrections applied later; conflicts surfaced | one effective-value layer feeds every tool; disagreements (inspector note vs correction, two users, user vs inspection) are flagged and both statements kept |
| Rules scoped to a well type | `propose_rule` saves a rule for `well_type` or one `well`; T350 rules never touch T200 |
| Final dataset loads from its documented format | roots in `AHC_DATA_DIRS`; no hardcoded IDs or answer strings; synthetic-dataset tests use IDs not in the sample |

Correction flow: say that a value is wrong, the copilot shows the **original value, the proposed replacement, the scope, who is changing it and why**, plus its effect (for example "not producing → producing") and any conflicting note. Nothing is saved until you press **Confirm and save**. The **Audit** page lists every correction, rule and shared note.

**Data lineage:** in a heatmap, click any cell or any total (area, month or grand total) to open its lineage: the contributing inspection records with their source file and line, the corrections applied, the detections that were excluded and why, the date and scope filters, and the exact calculation (for example `37 + 26 + 35 + 43 = 141`). The panel checks that the number of listed records equals the number shown. The totals are computed on the server; the browser adds nothing up.

Signals shown on answers: **Corrected data**, **Conflict**, **Needs confirmation**, **Unconfirmed**, **No evidence**, **Out of date** (stale recorded status), **User rule**.

## Tests

```powershell
.venv\Scripts\python.exe -m unittest discover        # 271 tests
```

- `tests/test_ahc_golden.py`, `test_ahc_memory.py`: the official sample dataset against the example scenarios (expected values live **only** in tests; skipped if `data/sample-data` is absent).
- `tests/test_ahc_core.py`: ingestion, rules, calculations and corrections on a **synthetic dataset** whose IDs, area names and edge cases (hot day, exact threshold, missed week, type-scoped rules) appear nowhere in the sample.
- `tests/test_ahc_agent.py`: the agent loop, grounding check, visual choice, tool gating and the HTTP API with a scripted model.
- `tests/test_ahc_router.py`: the built-in question patterns, the agent when the model is down, and the quota-aware retry.
- `tests/test_ahc_ui.py`: the front-end files parse and are wired together.
- `tests/test_ahc_lineage.py`: heatmap lineage reconciled against a raw-table recount and the source files, and proof that unsupported claims (digits, spelled-out numbers, invented IDs) cannot bypass verification.
- The original 124 starter tests (provider, thinking, images, retries, task framework) still pass.

## Limits worth knowing

- The free Gemma tier allows 16,000 input tokens per minute for `gemma-4-26b-a4b-it`. The agent keeps prompts small (about 2K tokens for a question), tracks a rolling budget, and skips the optional wording step (showing the verified facts) rather than stalling. The API also returns occasional transient `500`s; the SDK retries them.
- Containment times are parsed from the repair reports' compliance tables and prose with deterministic patterns (all 616 sample spill reports parse). A report worded very differently would show "no containment time on record" rather than a guess.
- The map is drawn to scale from latitude and longitude without a basemap, so it works offline.
- "Summer" is taken as 1 Jun to 31 Aug and the answer says so.

---

# Gemma 4 + Gradio Hackathon Starter (the base the copilot is built on)

A small, reusable starting point for building with **Gemma 4** through the Gemini API. It is infrastructure only: clone it, add your key, and spend the hackathon on the idea instead of on setup.

## Features

- Text -> Gemma 4 -> response
- Image -> Gemma 4 -> response
- Text + image -> Gemma 4 -> response
- Structured JSON output (prompted, then parsed and validated)
- One task file (`task.py`): change the task, prompt, and expected output without touching the provider or UI
- Fast by default: low "thinking" level, downscaled images, request timeout, and retries for transient failures (see [Speed and reliability](#speed-and-reliability))
- Clear errors for a missing API key, API failures, and malformed model output
- Loading state in the UI (status line, button disabled while the request runs)
- API key and model ID come from environment variables

## Architecture

```
task.py      THE task configuration: name, instructions, output schema, optional example.
app.py       Gradio UI. Reads the task, builds the prompt, calls gemma.py, parses the result.
prompts.py   Generic prompt builder (role, task, input, output format, rules, example).
gemma.py     The only file that talks to the provider (google-genai). Task-agnostic. Also holds the
             thinking, image-size, timeout, and retry settings.
utils.py     Extract / parse / validate JSON against a schema; error formatting. Task-agnostic.
tests/       Unit tests with a stubbed client or fake HTTP endpoint (no network, no API key needed).
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
| `GEMMA_THINKING` | no | How much the model "thinks" before answering: `minimal` (default, fastest), `low`, `medium`, `high`, or `default` (send no setting). See [Speed and reliability](#speed-and-reliability). |

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

In all three cases the system instruction is `prompts.build_prompt(...)`, built from the task in `task.py`. For image requests, `gemma.py` downsizes the PIL image if it is large, encodes it as JPEG or PNG (see below), and sends it as an inline image part followed by the text prompt. The response text is then passed to `utils.parse_model_json`, which strips a ```` ```json ```` fence if the model added one, parses the JSON, and checks it against the task's output schema.

JSON output is requested through the prompt only. This starter does not use the API's JSON mode / response schema, because Google's Gemma 4 docs do not document it.

## Speed and reliability

These settings live in `gemma.py` and apply to every task. The output JSON schema is not affected by any of them.

**Thinking (`GEMMA_THINKING`).** Gemma 4 "thinks" before it answers, which was about 80% of the request time in our measurements (roughly 13-15s per text request, against about 4s with `minimal`; real times vary with load).

- Values: `minimal` (default), `low`, `medium`, `high`, or `default` (send no setting, so the model uses its own behaviour: slowest).
- `gemma-4-26b-a4b-it` accepts `minimal` and `high`. If a model rejects the level you chose, the app logs one warning, repeats that request without the setting, and does the same for later requests until you restart. Only that specific error is handled this way; every other API error is reported as usual.
- A misspelled value is reported as a clear error. Trade-off: `minimal` may reason less deeply on hard tasks, so try `high` or `default` if answers look shallow.

**Images.** Images larger than 1536 px on the longest side are scaled down with the aspect ratio kept; smaller images are never enlarged.

- Photos are sent as JPEG (quality 90). Screenshots, diagrams, and text stay lossless PNG: JPEG is used only if it is less than half the size of the PNG. A 12-megapixel photo went from about 23 MB (PNG) to about 0.2 MB.
- Trade-off: very small text in a large screenshot (for example 4K) is harder to read after downscaling. Crop to the relevant area, or raise `MAX_IMAGE_DIMENSION` in `gemma.py`.

**Timeouts and retries.** Each attempt times out after 60 s (`REQUEST_TIMEOUT_MS`). Transient failures (HTTP 408, 429, 500, 502, 503, 504, connection errors, and timeouts) are tried up to 3 times in total, with a short wait between tries.

- Permanent errors are not retried: 400 (invalid request or unsupported setting), 401/403 (bad API key), and 404 (unknown model).
- The SDK does the retrying and nothing else does, so one failing request makes at most 3 HTTP requests.
- Limits: the SDK does not retry a server that drops the connection mid-request (`RemoteProtocolError`), and in the worst case an error appears after about 3 minutes (3 attempts of 60 s). A slower setup, such as `gemma-4-31b-it` with `GEMMA_THINKING=default` (about 90s per request in our tests), needs a larger `REQUEST_TIMEOUT_MS`; do not set it below 10000, because the API rejects shorter deadlines.

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

The tests use a stubbed client or a fake HTTP endpoint, so they need no network or API key, and they ignore whatever is in your `.env`.

## License

MIT. See [LICENSE](LICENSE).
