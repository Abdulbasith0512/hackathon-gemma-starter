# Asset Intelligence Copilot: write-up (draft, 2 pages)

## Page 1: system design

**Goal.** Answer operators' plain-English questions about the wells correctly and with evidence, keep what people tell it, and never let a language model do the arithmetic.

**Data: storage, indexing, retrieval.** The documented dataset folders load into SQLite in about 2 seconds (cached after that): wells, ~39.6k inspections, ~5.7k repairs, regulator events and notes, indexed by well and time, by date, and by the inspection that triggered each follow-up record. Every record keeps its source file and line and its original JSON, so the evidence panel can show exactly what was used. The manuals, SOPs and 1,509 repair reports are split into citable sections with SQLite full-text search. Reports are found only through each repair's `report_file`; containment times and compliance tables are parsed from them. Thresholds and deadlines (production temperature per well type, spill classes, SR-01..SR-03, RC-01..RC-04, the root-cause trigger) are read from the manuals and SOPs at load time and keep the quoted passage; a missing number is shown as a fallback, never silent.

**Tools.** 22 deterministic Python tools: status, wells not producing, temperature series, spills, downtime, downtime ranking, repair costs and repairs, spill heatmap, root-cause candidates, compliance audit, spill evidence, regulator events, inspection gaps, long downtime, document search, recall, and four write tools (correction, rule, shared note, claim check). Each returns data, citations, flags and drawable visuals. Gemma 4 (26B-A4B, Google AI Studio free tier) uses function calling to choose the tool and fill its arguments, then words the answer. A grounding check accepts the wording only if every number and record ID in it appears in the tool results or the question; otherwise the verified facts are shown. If the model is unreachable, built-in question patterns call the same tools.

**Numbers, documents and notes together.** One "effective value" layer overlays corrections on dataset records, so every tool and every user sees the same corrected data and the original is always one click away. Production status is derived from wellhead minus ambient temperature against the manual's threshold for the well type, never from `recorded_status`. Downtime is 7 days per weekly inspection that found the well not producing; repair `downtime_hours` is ignored. Stops are explained from open repairs and notes ("no recorded reason" when there is none), and compliance joins inspections, regulator events, repair reports and SOP deadlines.

**Memory.** *Shared* (SQLite, persistent): corrections keep the dataset value, the value before, the new value, who, why, when and scope, and a later correction supersedes without deleting; rules are scoped to a well type or one well (a T350 rule never touches T200); shared notes and status claims. *Private:* conversations and "the wells we discussed" are keyed to the signed-in user; the model never supplies a user ID, and another user's chat returns HTTP 403. A correction is previewed (original, proposal, scope, author, reason, effect, conflicting notes) and saved only on confirmation.

**Conflicts and new data.** Disagreements are surfaced, not resolved: a correction that contradicts the inspector's note, two users' claims, or a claim against the latest inspection are flagged (*Conflict*, *Needs confirmation*, *Unconfirmed*) and both statements are kept. Nothing names a well, area, user or answer in code: datasets are listed in `AHC_DATA_DIRS`, tests include a synthetic dataset with IDs that are not in the sample, and an unknown well type reports "rule not found" instead of guessing.

**Models and cost.** Gemma 4 26B-A4B-IT with minimal thinking, about 2-3K input tokens per question (free tier: 16K per minute, handled by a rolling token budget that skips the optional wording step rather than stalling). No paid services.

**Next.** Evaluate on held-out phrasing, add the production-threshold override as a scoped rule, and a basemap-backed map.

## Page 2: results on the final questions

*(Fill in from `results/final-results.md` after the 4:00 PM run: for each question, the answer, what worked, what did not and why.)*

| # | Question | Answer (short) | Worked? | Notes |
|---|---|---|---|---|
| | | | | |
