# Final hours checklist (test dataset release)

1. **Load the test dataset.** Copy the released folder next to the sample, for example `data\test-data\` (it must contain `fleet\` and `assets\`, or a `sample-data` folder holding them).

   ```powershell
   $env:AHC_DATA_DIRS = "data\test-data"              # test data only; add ";data\sample-data" to load both
   $env:AHC_AS_OF = "2026-10-16"                       # use the date the final questions state as "today"
   .venv\Scripts\python.exe -m ahc                     # http://127.0.0.1:8000
   ```

   If both roots contain the same record IDs with different content, the later root wins and the start-up summary lists how many records were replaced. For the final answers load only the dataset the questions are about.

2. **Check it loaded.** The header shows wells, inspections, repairs and reports. In the **Rules** page the production thresholds should read from the manuals (no "fallback" tags). Any ingestion issue is listed in `/api/bootstrap` under `stats.issues`.

3. **Smoke-test the sample answers** still hold (they use `data\sample-data`, not the test data):

   ```powershell
   .venv\Scripts\python.exe -m unittest tests.test_ahc_golden tests.test_ahc_memory
   ```

4. **Run the final questions.** Put them in `questions\final.json` in the same format as `questions\sample_scenarios.json` (`id`, `user`, `chat`, `text`; same `chat` label = same conversation):

   ```powershell
   .venv\Scripts\python.exe -m ahc.batch questions\final.json --out results\final-results.md
   ```

   Memory starts empty for each run. Corrections and rules in the file are saved automatically. Re-run a single question with `--only Q7`. If a question returns an API error, run it again (the free tier returns occasional 500/429 errors).

5. **Read every answer against its evidence**: open the cited records in the UI for anything that looks surprising. Copy answers into page 2 of `docs\WRITEUP.md`.

6. **Submit**: public GitHub repository link (MIT license is already in the repo), the 2-page write-up, the 5-minute video.
