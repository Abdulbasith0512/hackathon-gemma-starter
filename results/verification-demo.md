# Copilot results

Dataset roots: data\test-data\dataset · as-of 2027-01-15 · model gemma-4-26b-a4b-it · thinking minimal

### Q1 — Michael Turner: All our wells feed one reservoir. Map the reservoir pressure across the field from the pressure data.

I am unable to map the reservoir pressure across the field as no tool is available to retrieve reservoir pressure data.

*   The available tools provide information on well production status, downtime, repairs, spills, and inspections, but do not include reservoir pressure readings.
*   A search of the documentation did not return any data sources or procedures for reservoir pressure mapping.

**Visual: table** (Documents matching 'reservoir pressure data')

| Ref | Document | Section | Passage |
|---|---|---|---|
| T200#11 | T200 Rod-Lift Oil Well — Operating & Maintenance Manual | 11. Records |  … Human notes that
explain an abnormal reading (for example a planned shut-in) are valid context and
should be considered alongside the sensor [data]. |
| T200#3 | T200 Rod-Lift Oil Well — Operating & Maintenance Manual | 3. Normal operation |  … Produced
fluid leaves the [reservoir] warmer than the surface air, so a producing wellhead
runs noticeably warmer than ambient. When the pump stops, the …  |
| SR-01 | Spill Response SOP | SR-01 |  … Discovery time is the time of the inspection that detected the spill. `hours_to_report` in the [data] is the time to the written …  |
| T200#2 | T200 Rod-Lift Oil Well — Operating & Maintenance Manual | 2. Equipment overview |  … pump / Insert rod pump 1.75 in / Lifts fluid from the [reservoir] /
/ Flowline / 3 in carbon steel / Carries produced fluid to the gathering line …  |
| operations-sop-rev2#ops-3-status-evidence-precedence | Operations SOP | OPS-3 Status evidence precedence |  … or not producing oil, by the well-type manual,
  after any `[data]_correction` note), or
- its latest operator note saying the well was shut …  |

**Evidence:** T200#11, T200#3, SR-01, T200#2, operations-sop-rev2#ops-3-status-evidence-precedence

**Verification: NEEDS_REVIEW** — No independent recomputation exists for search_documents, so its result is not verified here. No independent rule classifies this question, so it cannot be confirmed that the tools used answer what was asked. (EV-B882D0CFA2)
_tools: search_documents · answer: model · 17.7s_

### Q2 — Robert Hayes: Which well produced the most oil in 2026?

I do not have a tool that provides the total oil production volume per well; the available tools only track downtime, repairs, spills, and regulatory events.

**Visual: bar** (Downtime ranking, the whole field (ALL wells), 20 Oct 2022 to 31 Dec 2026)

| Rank | Well | Type | Downtime days | Non-producing weeks |
|---|---|---|---|---|


**Verification: NEEDS_REVIEW** — No independent rule classifies this question, so it cannot be confirmed that the tools used answer what was asked. (EV-04B987441F)
_tools: downtime_ranking · answer: model · 63.8s_

### Q3 — Laura Simmons: Since 1 Nov 2026, every time an operator note reports gas at a well, did we get someone out to that well in time under our operating procedures? List every report and whether the response met the deadline.

Since 1 November 2026, 17 gas-odor reports met the response deadline and 9 missed it.

*   **Summary:** Out of 26 total reports, 17 met the response deadline and 9 missed it [operations-sop-rev2#ops-1-gas-odor-response].
*   **Deadline Rules:** For reports before 1 January 2027, the deadline was 24 hours; for reports after that date, the deadline was 12 hours [operations-sop-rev2#ops-1-gas-odor-response].
*   **Missed Deadlines (Examples):**
    *   **WELL-0163:** Report [CTX-0163-002] on 2026-11-03; first response [MNT-0163-019] was after 251.1 hours (Limit: 24 h) [CTX-0163-002].
    *   **WELL-0341:** Report [CTX-0341-002] on 2026-11-19; first response [INS-0341-0109] was after 677.8 hours (Limit: 24 h) [CTX-0341-002].
    *   **WELL-0332:** Report [CTX-0332-004] on 2026-12-03; no response is recorded (Limit: 24 h).
    *   **WELL-0401:** Report [CTX-0401-002] on 2026-12-05; first response [MNT-0401-033] was after 138.2 hours (Limit: 24 h) [CTX-0401-002].
    *   **WELL-0052:** Report [CTX-0052-003] on 2026-12-18; no response is recorded (Limit: 24 h).
    *   **WELL-0362:** Report [CTX-0362-002] on 2026-12-24; first response [MNT-0362-030] was after 31.8 hours (Limit: 24 h) [CTX-0362-002].
    *   **WELL-0161:** Report [CTX-0161-006] on 2026-12-25; first response [INS-0161-0168] was after 475.2 hours (Limit: 24 h) [CTX-0161-006].
    *   **WELL-0599:** Report [CTX-0599-003] on 2027-01-06; first response [INS-0599-0196] was after 16.4 hours (Limit: 12 h) [CTX-0599-003].
    *   **WELL-0516:** Report [CTX-0516-002] on 2027-01-06; first response [INS-0516-0215] was after 15.0 hours (Limit: 12 h) [CTX-0516-002].

**Visual: table** (Gas-odor reports and responses · the whole field, 1 Nov 2026 to 15 Jan 2027)

| Well | Area | Reported at | Response | Hours to response | Deadline | Met / Missed |
|---|---|---|---|---|---|---|
| WELL-0163 | Northeast Block 8 | 2026-11-03 20:55 UTC | MNT-0163-019 · 2026-11-14 08:00 UTC | 251.1 | 2026-11-04 20:55 UTC (24 h) | Missed |
| WELL-0149 | Northeast Block 7 | 2026-11-06 18:20 UTC | MNT-0149-029 · 2026-11-07 08:00 UTC | 13.7 | 2026-11-07 18:20 UTC (24 h) | Met |
| WELL-0165 | Northeast Block 8 | 2026-11-13 20:35 UTC | MNT-0165-031 · 2026-11-14 08:00 UTC | 11.4 | 2026-11-14 20:35 UTC (24 h) | Met |
| WELL-0341 | Northwest Block 12 | 2026-11-19 07:40 UTC | INS-0341-0109 · 2026-12-17 13:30 UTC | 677.8 | 2026-11-20 07:40 UTC (24 h) | Missed |
| WELL-0091 | Southwest Block 24 | 2026-11-27 22:25 UTC | MNT-0091-019 · 2026-11-28 08:00 UTC | 9.6 | 2026-11-28 22:25 UTC (24 h) | Met |
| WELL-0423 | Northwest Block 12 | 2026-12-03 05:25 UTC | INS-0423-0213 · 2026-12-03 09:15 UTC | 3.8 | 2026-12-04 05:25 UTC (24 h) | Met |
| WELL-0059 | Southwest Block 24 | 2026-12-03 06:10 UTC | INS-0059-0213 · 2026-12-03 12:15 UTC | 6.1 | 2026-12-04 06:10 UTC (24 h) | Met |
| WELL-0332 | Northwest Block 12 | 2026-12-03 12:10 UTC | none | — | 2026-12-04 12:10 UTC (24 h) | Missed |
| WELL-0401 | Northwest Block 12 | 2026-12-05 13:50 UTC | MNT-0401-033 · 2026-12-11 08:00 UTC | 138.2 | 2026-12-06 13:50 UTC (24 h) | Missed |
| WELL-0189 | Northeast Block 8 | 2026-12-10 12:35 UTC | MNT-0189-037 · 2026-12-11 08:00 UTC | 19.4 | 2026-12-11 12:35 UTC (24 h) | Met |
| WELL-0403 | Northwest Block 12 | 2026-12-10 21:15 UTC | MNT-0403-024 · 2026-12-11 08:00 UTC | 10.8 | 2026-12-11 21:15 UTC (24 h) | Met |
| WELL-0244 | Southeast Block 31 | 2026-12-11 05:25 UTC | MNT-0244-026 · 2026-12-11 08:00 UTC | 2.6 | 2026-12-12 05:25 UTC (24 h) | Met |
| WELL-0040 | Southwest Block 23 | 2026-12-12 01:55 UTC | MNT-0040-029 · 2026-12-12 08:00 UTC | 6.1 | 2026-12-13 01:55 UTC (24 h) | Met |
| WELL-0228 | Southeast Block 31 | 2026-12-16 19:50 UTC | INS-0228-0144 · 2026-12-17 12:45 UTC | 16.9 | 2026-12-17 19:50 UTC (24 h) | Met |
| WELL-0052 | Southwest Block 24 | 2026-12-18 06:45 UTC | none | — | 2026-12-19 06:45 UTC (24 h) | Missed |
| WELL-0370 | Northwest Block 12 | 2026-12-21 12:45 UTC | MNT-0370-028 · 2026-12-22 08:00 UTC | 19.2 | 2026-12-22 12:45 UTC (24 h) | Met |
| WELL-0362 | Northwest Block 12 | 2026-12-24 00:15 UTC | MNT-0362-030 · 2026-12-25 08:00 UTC | 31.8 | 2026-12-25 00:15 UTC (24 h) | Missed |
| WELL-0161 | Northeast Block 8 | 2026-12-25 15:45 UTC | INS-0161-0168 · 2027-01-14 11:00 UTC | 475.2 | 2026-12-26 15:45 UTC (24 h) | Missed |
| WELL-0135 | Northeast Block 7 | 2026-12-27 03:50 UTC | MNT-0135-034 · 2026-12-27 08:00 UTC | 4.2 | 2026-12-28 03:50 UTC (24 h) | Met |
| WELL-0324 | Northwest Block 12 | 2027-01-01 22:40 UTC | MNT-0324-036 · 2027-01-02 08:00 UTC | 9.3 | 2027-01-02 10:40 UTC (12 h) | Met |
| WELL-0330 | Northwest Block 12 | 2027-01-02 21:40 UTC | MNT-0330-030 · 2027-01-03 08:00 UTC | 10.3 | 2027-01-03 09:40 UTC (12 h) | Met |
| WELL-0599 | Southeast Block 32 | 2027-01-06 17:20 UTC | INS-0599-0196 · 2027-01-07 09:45 UTC | 16.4 | 2027-01-07 05:20 UTC (12 h) | Missed |
| WELL-0516 | Southeast Block 32 | 2027-01-06 21:15 UTC | INS-0516-0215 · 2027-01-07 12:15 UTC | 15.0 | 2027-01-07 09:15 UTC (12 h) | Missed |
| WELL-0425 | Northwest Block 12 | 2027-01-07 05:20 UTC | INS-0425-0218 · 2027-01-07 09:00 UTC | 3.7 | 2027-01-07 17:20 UTC (12 h) | Met |
| WELL-0465 | Southeast Block 32 | 2027-01-08 23:35 UTC | MNT-0465-031 · 2027-01-09 08:00 UTC | 8.4 | 2027-01-09 11:35 UTC (12 h) | Met |
| WELL-0137 | Northeast Block 7 | 2027-01-10 23:30 UTC | MNT-0137-032 · 2027-01-11 08:00 UTC | 8.5 | 2027-01-11 11:30 UTC (12 h) | Met |

**Evidence:** operations-sop-rev2#ops-1-gas-odor-response, CTX-0163-002, MNT-0163-019, CTX-0149-004, MNT-0149-029, CTX-0165-001, MNT-0165-031, CTX-0341-002, INS-0341-0109, CTX-0091-001, MNT-0091-019, CTX-0423-002, INS-0423-0213, CTX-0059-002, INS-0059-0213, CTX-0332-004, CTX-0401-002, MNT-0401-033, CTX-0189-003, MNT-0189-037, CTX-0403-004, MNT-0403-024, CTX-0244-002, MNT-0244-026, CTX-0040-002, MNT-0040-029, CTX-0228-004, INS-0228-0144, CTX-0052-003, CTX-0370-005 …

**Verification: PASS** — numbers and records recomputed from the dataset (EV-F015C6D4C2)
_tools: gas_response · answer: model · 77.8s_

### Q5 — Michael Turner: The State Oil & Gas Commission wrote to us in November 2026 about spills. Which of our spills does the letter cover, and on which ones are we not compliant? Show me a table.

0 regulator event(s) in the whole field, 1 Nov 2026 to 30 Nov 2026; fines USD 0, of which USD 0 still open.
48 oil spill(s) in the whole field, 1 Nov 2026 to 30 Nov 2026, totalling 70.5 bbl. [INS-0035-0210, INS-0062-0207, INS-0077-0204]
19 Nov 2026: WELL-0035, 1.0 bbl (INS-0035-0210).
5 Nov 2026: WELL-0062, 0.3 bbl (INS-0062-0207).
5 Nov 2026: WELL-0077, 0.7 bbl (INS-0077-0204).
19 Nov 2026: WELL-0113, 0.5 bbl (INS-0113-0213).
12 Nov 2026: WELL-0114, 0.5 bbl (INS-0114-0210).
12 Nov 2026: WELL-0117, 2.3 bbl (INS-0117-0196).
5 Nov 2026: WELL-0119, 6.0 bbl (INS-0119-0209).
12 Nov 2026: WELL-0134, 0.5 bbl (INS-0134-0208).
5 Nov 2026: WELL-0138, 1.2 bbl (INS-0138-0211).
12 Nov 2026: WELL-0143, 0.2 bbl (INS-0143-0179).
19 Nov 2026: WELL-0151, 0.7 bbl (INS-0151-0209).
19 Nov 2026: WELL-0169, 0.4 bbl (INS-0169-0211).
12 Nov 2026: WELL-0181, 1.5 bbl (INS-0181-0212).
12 Nov 2026: WELL-0189, 1.3 bbl (INS-0189-0212).
19 Nov 2026: WELL-0194, 0.4 bbl (INS-0194-0209).
12 Nov 2026: WELL-0200, 0.6 bbl (INS-0200-0210).
19 Nov 2026: WELL-0203, 4.3 bbl (INS-0203-0213).
12 Nov 2026: WELL-0225, 1.6 bbl (INS-0225-0208).
26 Nov 2026: WELL-0235, 0.5 bbl (INS-0235-0212).
26 Nov 2026: WELL-0240, 1.6 bbl (INS-0240-0211).
12 Nov 2026: WELL-0246, 0.1 bbl (INS-0246-0126).
12 Nov 2026: WELL-0253, 2.1 bbl (INS-0253-0209).
12 Nov 2026: WELL-0281, 0.6 bbl (INS-0281-0207).
5 Nov 2026: WELL-0287, 2.4 bbl (INS-0287-0208).
26 Nov 2026: WELL-0299, 0.6 bbl (INS-0299-0210).
5 Nov 2026: WELL-0331, 0.9 bbl (INS-0331-0206).
19 Nov 2026: WELL-0332, 2.5 bbl (INS-0332-0211).
5 Nov 2026: WELL-0381, 4.5 bbl (INS-0381-0205).
19 Nov 2026: WELL-0383, 4.4 bbl (INS-0383-0211).
19 Nov 2026: WELL-0390, 0.6 bbl (INS-0390-0209).
19 Nov 2026: WELL-0404, 3.2 bbl (INS-0404-0206).
5 Nov 2026: WELL-0405, 0.7 bbl (INS-0405-0209).
19 Nov 2026: WELL-0411, 0.4 bbl (INS-0411-0139).
19 Nov 2026: WELL-0420, 0.9 bbl (INS-0420-0211).
5 Nov 2026: WELL-0422, 2.2 bbl (INS-0422-0205).
12 Nov 2026: WELL-0429, 0.5 bbl (INS-0429-0210).
19 Nov 2026: WELL-0450, 0.4 bbl (INS-0450-0208).
26 Nov 2026: WELL-0459, 0.2 bbl (INS-0459-0212).
19 Nov 2026: WELL-0467, 0.9 bbl (INS-0467-0209).
12 Nov 2026: WELL-0487, 0.3 bbl (INS-0487-0209).
26 Nov 2026: WELL-0492, 1.0 bbl (INS-0492-0130).
26 Nov 2026: WELL-0494, 6.2 bbl (INS-0494-0209).
19 Nov 2026: WELL-0501, 0.8 bbl (INS-0501-0205).
5 Nov 2026: WELL-0505, 0.5 bbl (INS-0505-0210).
26 Nov 2026: WELL-0564, 5.7 bbl (INS-0564-0181).
5 Nov 2026: WELL-0572, 0.3 bbl (INS-0572-0207).
5 Nov 2026: WELL-0574, 1.0 bbl (INS-0574-0209).
26 Nov 2026: WELL-0589, 0.5 bbl (INS-0589-0212).
By area: Northwest Block 12 12; Southeast Block 32 11; Northeast Block 7 9; Northeast Block 8 6; Southeast Block 31 5; Southwest Block 23 3; Southwest Block 24 2.
23 breach(es) in the whole field for 1 Nov 2026 to 30 Nov 2026; USD 12,500 in fines still open. 3 of 48 spill(s) reached the 5 bbl reporting threshold.
WELL-0035 spill of 1.0 bbl on 19 Nov 2026 (INS-0035-0210), class moderate.
SR-02 breach: contained after about 8.7 hours, against a 4-hour limit (found only in the repair report). [report:MNT-0035-030, MNT-0035-030]
WELL-0062 spill of 0.3 bbl on 5 Nov 2026 (INS-0062-0207), class minor.
SR-02 breach: contained after about 5.2 hours, against a 4-hour limit (found only in the repair report). [report:MNT-0062-028, MNT-0062-028]
WELL-0077 spill of 0.7 bbl on 5 Nov 2026 (INS-0077-0204), class minor.
SR-02 breach: contained after about 5 hours, against a 4-hour limit (found only in the repair report). [report:MNT-0077-026, MNT-0077-026]
WELL-0113 spill of 0.5 bbl on 19 Nov 2026 (INS-0113-0213), class minor.
SR-02 met: contained after about 2.7 hours, against a 4-hour limit. [report:MNT-0113-032, MNT-0113-032]
WELL-0114 spill of 0.5 bbl on 12 Nov 2026 (INS-0114-0210), class minor.
SR-02 met: contained after about 3.1 hours, against a 4-hour limit. [report:MNT-0114-027, MNT-0114-027]
WELL-0117 spill of 2.3 bbl on 12 Nov 2026 (INS-0117-0196), class moderate.
SR-02 breach: contained after about 7.4 hours, against a 4-hour limit (found only in the repair report). [report:MNT-0117-023, MNT-0117-023]
WELL-0119 spill of 6.0 bbl on 5 Nov 2026 (INS-0119-0209), class reportable.
SR-01 met: the written notice was filed after 7 hours (REG-0119-001), within the 12-hour limit.
SR-03 met: remediation was verified by the agency (REG-0119-002).
SR-02 met: contained after about 1.9 hours, against a 4-hour limit. [report:MNT-0119-029, MNT-0119-029]
WELL-0134 spill of 0.5 bbl on 12 Nov 2026 (INS-0134-0208), class minor.
SR-02 met: contained after about 1.7 hours, against a 4-hour limit. [report:MNT-0134-032, MNT-0134-032]
WELL-0138 spill of 1.2 bbl on 5 Nov 2026 (INS-0138-0211), class moderate.
SR-02 met: contained after about 3.6 hours, against a 4-hour limit. [report:MNT-0138-036, MNT-0138-036]
WELL-0143 spill of 0.2 bbl on 12 Nov 2026 (INS-0143-0179), class minor.
SR-02 met: contained after about 2.4 hours, against a 4-hour limit. [report:MNT-0143-027, MNT-0143-027]
WELL-0151 spill of 0.7 bbl on 19 Nov 2026 (INS-0151-0209), class minor.
SR-02 met: contained after about 1.8 hours, against a 4-hour limit. [report:MNT-0151-028, MNT-0151-028]
WELL-0169 spill of 0.4 bbl on 19 Nov 2026 (INS-0169-0211), class minor.
SR-02 met: contained after about 2.3 hours, against a 4-hour limit. [report:MNT-0169-024, MNT-0169-024]
WELL-0181 spill of 1.5 bbl on 12 Nov 2026 (INS-0181-0212), class moderate.
SR-02 breach: contained after about 8.4 hours, against a 4-hour limit (found only in the repair report). [report:MNT-0181-029, MNT-0181-029]
WELL-0189 spill of 1.3 bbl on 12 Nov 2026 (INS-0189-0212), class moderate.
SR-02 breach: contained after about 7.1 hours, against a 4-hour limit (found only in the repair report). [report:MNT-0189-036, MNT-0189-036]
WELL-0194 spill of 0.4 bbl on 19 Nov 2026 (INS-0194-0209), class minor.
SR-02 met: contained after about 3.6 hours, against a 4-hour limit. [report:MNT-0194-039, MNT-0194-039]
WELL-0200 spill of 0.6 bbl on 12 Nov 2026 (INS-0200-0210), class minor.
SR-02 breach: contained after about 8.1 hours, against a 4-hour limit (found only in the repair report). [report:MNT-0200-027, MNT-0200-027]
WELL-0203 spill of 4.3 bbl on 19 Nov 2026 (INS-0203-0213), class moderate.
SR-02 met: contained after about 2.2 hours, against a 4-hour limit. [report:MNT-0203-030, MNT-0203-030]
WELL-0225 spill of 1.6 bbl on 12 Nov 2026 (INS-0225-0208), class moderate.
SR-02 met: contained after about 2 hours, against a 4-hour limit. [report:MNT-0225-032, MNT-0225-032]
WELL-0235 spill of 0.5 bbl on 26 Nov 2026 (INS-0235-0212), class minor.
SR-02 breach: contained after about 7.7 hours, against a 4-hour limit (found only in the repair report). [report:MNT-0235-028, MNT-0235-028]
WELL-0240 spill of 1.6 bbl on 26 Nov 2026 (INS-0240-0211), class moderate.
SR-02 met: contained after about 2.8 hours, against a 4-hour limit. [report:MNT-0240-036, MNT-0240-036]
WELL-0246 spill of 0.1 bbl on 12 Nov 2026 (INS-0246-0126), class minor.
SR-02 breach: contained after about 7.7 hours, against a 4-hour limit (found only in the repair report). [report:MNT-0246-016, MNT-0246-016]
WELL-0253 spill of 2.1 bbl on 12 Nov 2026 (INS-0253-0209), class moderate.
SR-02 met: contained after about 2 hours, against a 4-hour limit. [report:MNT-0253-030, MNT-0253-030]
WELL-0281 spill of 0.6 bbl on 12 Nov 2026 (INS-0281-0207), class minor.
SR-02 met: contained after about 2.7 hours, against a 4-hour limit. [report:MNT-0281-028, MNT-0281-028]
WELL-0287 spill of 2.4 bbl on 5 Nov 2026 (INS-0287-0208), class moderate.
SR-02 met: contained after about 1.8 hours, against a 4-hour limit. [report:MNT-0287-027, MNT-0287-027]
WELL-0299 spill of 0.6 bbl on 26 Nov 2026 (INS-0299-0210), class minor.
SR-02 met: contained after about 3.6 hours, against a 4-hour limit. [report:MNT-0299-034, MNT-0299-034]
WELL-0331 spill of 0.9 bbl on 5 Nov 2026 (INS-0331-0206), class minor.
SR-02 breach: contained after about 4.8 hours, against a 4-hour limit (found only in the repair report). [report:MNT-0331-028, MNT-0331-028]
WELL-0332 spill of 2.5 bbl on 19 Nov 2026 (INS-0332-0211), class moderate.
SR-02 met: contained after about 2.2 hours, against a 4-hour limit. [report:MNT-0332-033, MNT-0332-033]
WELL-0381 spill of 4.5 bbl on 5 Nov 2026 (INS-0381-0205), class moderate.
SR-02 breach: contained after about 6 hours, against a 4-hour limit (found only in the repair report). [report:MNT-0381-032, MNT-0381-032]
WELL-0383 spill of 4.4 bbl on 19 Nov 2026 (INS-0383-0211), class moderate.
SR-02 met: contained after about 1.7 hours, against a 4-hour limit. [report:MNT-0383-027, MNT-0383-027]
WELL-0390 spill of 0.6 bbl on 19 Nov 2026 (INS-0390-0209), class minor.
SR-02 met: contained after about 3.2 hours, against a 4-hour limit. [report:MNT-0390-030, MNT-0390-030]
WELL-0404 spill of 3.2 bbl on 19 Nov 2026 (INS-0404-0206), class moderate.
SR-02 met: contained after about 3.4 hours, against a 4-hour limit. [report:MNT-0404-032, MNT-0404-032]
WELL-0405 spill of 0.7 bbl on 5 Nov 2026 (INS-0405-0209), class minor.
SR-02 breach: contained after about 6.2 hours, against a 4-hour limit (found only in the repair report). [report:MNT-0405-029, MNT-0405-029]
WELL-0411 spill of 0.4 bbl on 19 Nov 2026 (INS-0411-0139), class minor.
SR-02 met: contained after about 2.7 hours, against a 4-hour limit. [report:MNT-0411-021, MNT-0411-021]
WELL-0420 spill of 0.9 bbl on 19 Nov 2026 (INS-0420-0211), class minor.
SR-02 breach: contained after about 7 hours, against a 4-hour limit (found only in the repair report). [report:MNT-0420-032, MNT-0420-032]
WELL-0422 spill of 2.2 bbl on 5 Nov 2026 (INS-0422-0205), class moderate.
SR-02 breach: contained after about 8.6 hours, against a 4-hour limit (found only in the repair report). [report:MNT-0422-030, MNT-0422-030]
WELL-0429 spill of 0.5 bbl on 12 Nov 2026 (INS-0429-0210), class minor.
SR-02 met: contained after about 3.7 hours, against a 4-hour limit. [report:MNT-0429-033, MNT-0429-033]
WELL-0450 spill of 0.4 bbl on 19 Nov 2026 (INS-0450-0208), class minor.
SR-02 breach: contained after about 5.8 hours, against a 4-hour limit (found only in the repair report). [report:MNT-0450-026, MNT-0450-026]
WELL-0459 spill of 0.2 bbl on 26 Nov 2026 (INS-0459-0212), class minor.
SR-02 breach: contained after about 4.6 hours, against a 4-hour limit (found only in the repair report). [report:MNT-0459-030, MNT-0459-030]
WELL-0467 spill of 0.9 bbl on 19 Nov 2026 (INS-0467-0209), class minor.
SR-02 breach: contained after about 6.6 hours, against a 4-hour limit (found only in the repair report). [report:MNT-0467-033, MNT-0467-033]
WELL-0487 spill of 0.3 bbl on 12 Nov 2026 (INS-0487-0209), class minor.
SR-02 met: contained after about 2.7 hours, against a 4-hour limit. [report:MNT-0487-023, MNT-0487-023]
WELL-0492 spill of 1.0 bbl on 26 Nov 2026 (INS-0492-0130), class moderate.
SR-02 breach: contained after about 8.4 hours, against a 4-hour limit (found only in the repair report). [report:MNT-0492-019, MNT-0492-019]
WELL-0494 spill of 6.2 bbl on 26 Nov 2026 (INS-0494-0209), class reportable.
SR-01 breach: reported after 38 hours (REG-0494-001), against a 12-hour limit. This led to notice of violation REG-0494-002 with a USD 5,000 fine, open.
RC-04 met: the response REG-0494-003 was filed on 1 Jan 2027 (due 16 Jan 2027). [REG-0494-002]
SR-03 met: remediation was verified by the agency (REG-0494-004).
SR-02 breach: contained after about 6.5 hours, against a 4-hour limit (found only in the repair report). [report:MNT-0494-025, MNT-0494-025]
WELL-0501 spill of 0.8 bbl on 19 Nov 2026 (INS-0501-0205), class minor.
SR-02 met: contained after about 3.8 hours, against a 4-hour limit. [report:MNT-0501-026, MNT-0501-026]
WELL-0505 spill of 0.5 bbl on 5 Nov 2026 (INS-0505-0210), class minor.
SR-02 met: contained after about 1.2 hours, against a 4-hour limit. [report:MNT-0505-031, MNT-0505-031]
WELL-0564 spill of 5.7 bbl on 26 Nov 2026 (INS-0564-0181), class reportable.
SR-01 breach: reported after 55 hours (REG-0564-001), against a 12-hour limit. This led to notice of violation REG-0564-003 with a USD 7,500 fine, open.
RC-04 pending: notice of violation REG-0564-003 needs a response by 25 Jan 2027.
SR-03 met: remediation was verified by the agency (REG-0564-002).
SR-02 breach: contained after about 5 hours, against a 4-hour limit (found only in the repair report). [report:MNT-0564-031, MNT-0564-031]
WELL-0572 spill of 0.3 bbl on 5 Nov 2026 (INS-0572-0207), class minor.
SR-02 breach: contained after about 5.6 hours, against a 4-hour limit (found only in the repair report). [report:MNT-0572-024, MNT-0572-024]
WELL-0574 spill of 1.0 bbl on 5 Nov 2026 (INS-0574-0209), class moderate.
SR-02 met: contained after about 1.3 hours, against a 4-hour limit. [report:MNT-0574-030, MNT-0574-030]
WELL-0589 spill of 0.5 bbl on 26 Nov 2026 (INS-0589-0212), class minor.
SR-02 met: contained after about 1.6 hours, against a 4-hour limit. [report:MNT-0589-031, MNT-0589-031]

**Visual: table** (Regulator events in the whole field, 1 Nov 2026 to 30 Nov 2026)

| Event | Well | Date | Type | Protocol | Status | Fine (USD) | Detail |
|---|---|---|---|---|---|---|---|


**Visual: table** (Oil spills in the whole field, 1 Nov 2026 to 30 Nov 2026)

| Date | Well | Volume (bbl) | Pad area % | Inspection |
|---|---|---|---|---|
| 2026-11-19 | WELL-0035 | 1.0 | 2.2 | INS-0035-0210 |
| 2026-11-05 | WELL-0062 | 0.3 | 2.4 | INS-0062-0207 |
| 2026-11-05 | WELL-0077 | 0.7 | 1.8 | INS-0077-0204 |
| 2026-11-19 | WELL-0113 | 0.5 | 2.5 | INS-0113-0213 |
| 2026-11-12 | WELL-0114 | 0.5 | 1.6 | INS-0114-0210 |
| 2026-11-12 | WELL-0117 | 2.3 | 5.1 | INS-0117-0196 |
| 2026-11-05 | WELL-0119 | 6.0 | 11.6 | INS-0119-0209 |
| 2026-11-12 | WELL-0134 | 0.5 | 2.4 | INS-0134-0208 |
| 2026-11-05 | WELL-0138 | 1.2 | 7.0 | INS-0138-0211 |
| 2026-11-12 | WELL-0143 | 0.2 | 1.1 | INS-0143-0179 |
| 2026-11-19 | WELL-0151 | 0.7 | 1.7 | INS-0151-0209 |
| 2026-11-19 | WELL-0169 | 0.4 | 0.7 | INS-0169-0211 |
| 2026-11-12 | WELL-0181 | 1.5 | 3.4 | INS-0181-0212 |
| 2026-11-12 | WELL-0189 | 1.3 | 2.3 | INS-0189-0212 |
| 2026-11-19 | WELL-0194 | 0.4 | 2.1 | INS-0194-0209 |
| 2026-11-12 | WELL-0200 | 0.6 | 1.4 | INS-0200-0210 |
| 2026-11-19 | WELL-0203 | 4.3 | 10.3 | INS-0203-0213 |
| 2026-11-12 | WELL-0225 | 1.6 | 6.2 | INS-0225-0208 |
| 2026-11-26 | WELL-0235 | 0.5 | 1.8 | INS-0235-0212 |
| 2026-11-26 | WELL-0240 | 1.6 | 4.1 | INS-0240-0211 |
| 2026-11-12 | WELL-0246 | 0.1 | 0.5 | INS-0246-0126 |
| 2026-11-12 | WELL-0253 | 2.1 | 3.8 | INS-0253-0209 |
| 2026-11-12 | WELL-0281 | 0.6 | 1.9 | INS-0281-0207 |
| 2026-11-05 | WELL-0287 | 2.4 | 7.1 | INS-0287-0208 |
| 2026-11-26 | WELL-0299 | 0.6 | 2.2 | INS-0299-0210 |
| 2026-11-05 | WELL-0331 | 0.9 | 5.3 | INS-0331-0206 |
| 2026-11-19 | WELL-0332 | 2.5 | 6.6 | INS-0332-0211 |
| 2026-11-05 | WELL-0381 | 4.5 | 10.3 | INS-0381-0205 |
| 2026-11-19 | WELL-0383 | 4.4 | 11.5 | INS-0383-0211 |
| 2026-11-19 | WELL-0390 | 0.6 | 1.7 | INS-0390-0209 |
| 2026-11-19 | WELL-0404 | 3.2 | 10.5 | INS-0404-0206 |
| 2026-11-05 | WELL-0405 | 0.7 | 1.1 | INS-0405-0209 |
| 2026-11-19 | WELL-0411 | 0.4 | 0.8 | INS-0411-0139 |
| 2026-11-19 | WELL-0420 | 0.9 | 3.5 | INS-0420-0211 |
| 2026-11-05 | WELL-0422 | 2.2 | 9.9 | INS-0422-0205 |
| 2026-11-12 | WELL-0429 | 0.5 | 1.8 | INS-0429-0210 |
| 2026-11-19 | WELL-0450 | 0.4 | 1.4 | INS-0450-0208 |
| 2026-11-26 | WELL-0459 | 0.2 | 1.5 | INS-0459-0212 |
| 2026-11-19 | WELL-0467 | 0.9 | 2.7 | INS-0467-0209 |
| 2026-11-12 | WELL-0487 | 0.3 | 0.8 | INS-0487-0209 |

_8 more rows not shown_

**Visual: table** (Compliance audit, the whole field, 1 Nov 2026 to 30 Nov 2026)

| Well | Inspection | Protocol | Status | Detail | Evidence |
|---|---|---|---|---|---|
| WELL-0035 | INS-0035-0210 | SR-02 | breach | contained after about 8.7 hours, against a 4-hour limit (found only in the repair report). | report:MNT-0035-030, MNT-0035-030, SR-02 |
| WELL-0062 | INS-0062-0207 | SR-02 | breach | contained after about 5.2 hours, against a 4-hour limit (found only in the repair report). | report:MNT-0062-028, MNT-0062-028, SR-02 |
| WELL-0077 | INS-0077-0204 | SR-02 | breach | contained after about 5 hours, against a 4-hour limit (found only in the repair report). | report:MNT-0077-026, MNT-0077-026, SR-02 |
| WELL-0113 | INS-0113-0213 | SR-02 | met | contained after about 2.7 hours, against a 4-hour limit. | report:MNT-0113-032, MNT-0113-032, SR-02 |
| WELL-0114 | INS-0114-0210 | SR-02 | met | contained after about 3.1 hours, against a 4-hour limit. | report:MNT-0114-027, MNT-0114-027, SR-02 |
| WELL-0117 | INS-0117-0196 | SR-02 | breach | contained after about 7.4 hours, against a 4-hour limit (found only in the repair report). | report:MNT-0117-023, MNT-0117-023, SR-02 |
| WELL-0119 | INS-0119-0209 | SR-01 | met | the written notice was filed after 7 hours (REG-0119-001), within the 12-hour limit. | REG-0119-001, SR-01 |
| WELL-0119 | INS-0119-0209 | SR-03 | met | remediation was verified by the agency (REG-0119-002). | REG-0119-002, SR-03 |
| WELL-0119 | INS-0119-0209 | SR-02 | met | contained after about 1.9 hours, against a 4-hour limit. | report:MNT-0119-029, MNT-0119-029, SR-02 |
| WELL-0134 | INS-0134-0208 | SR-02 | met | contained after about 1.7 hours, against a 4-hour limit. | report:MNT-0134-032, MNT-0134-032, SR-02 |
| WELL-0138 | INS-0138-0211 | SR-02 | met | contained after about 3.6 hours, against a 4-hour limit. | report:MNT-0138-036, MNT-0138-036, SR-02 |
| WELL-0143 | INS-0143-0179 | SR-02 | met | contained after about 2.4 hours, against a 4-hour limit. | report:MNT-0143-027, MNT-0143-027, SR-02 |
| WELL-0151 | INS-0151-0209 | SR-02 | met | contained after about 1.8 hours, against a 4-hour limit. | report:MNT-0151-028, MNT-0151-028, SR-02 |
| WELL-0169 | INS-0169-0211 | SR-02 | met | contained after about 2.3 hours, against a 4-hour limit. | report:MNT-0169-024, MNT-0169-024, SR-02 |
| WELL-0181 | INS-0181-0212 | SR-02 | breach | contained after about 8.4 hours, against a 4-hour limit (found only in the repair report). | report:MNT-0181-029, MNT-0181-029, SR-02 |
| WELL-0189 | INS-0189-0212 | SR-02 | breach | contained after about 7.1 hours, against a 4-hour limit (found only in the repair report). | report:MNT-0189-036, MNT-0189-036, SR-02 |
| WELL-0194 | INS-0194-0209 | SR-02 | met | contained after about 3.6 hours, against a 4-hour limit. | report:MNT-0194-039, MNT-0194-039, SR-02 |
| WELL-0200 | INS-0200-0210 | SR-02 | breach | contained after about 8.1 hours, against a 4-hour limit (found only in the repair report). | report:MNT-0200-027, MNT-0200-027, SR-02 |
| WELL-0203 | INS-0203-0213 | SR-02 | met | contained after about 2.2 hours, against a 4-hour limit. | report:MNT-0203-030, MNT-0203-030, SR-02 |
| WELL-0225 | INS-0225-0208 | SR-02 | met | contained after about 2 hours, against a 4-hour limit. | report:MNT-0225-032, MNT-0225-032, SR-02 |
| WELL-0235 | INS-0235-0212 | SR-02 | breach | contained after about 7.7 hours, against a 4-hour limit (found only in the repair report). | report:MNT-0235-028, MNT-0235-028, SR-02 |
| WELL-0240 | INS-0240-0211 | SR-02 | met | contained after about 2.8 hours, against a 4-hour limit. | report:MNT-0240-036, MNT-0240-036, SR-02 |
| WELL-0246 | INS-0246-0126 | SR-02 | breach | contained after about 7.7 hours, against a 4-hour limit (found only in the repair report). | report:MNT-0246-016, MNT-0246-016, SR-02 |
| WELL-0253 | INS-0253-0209 | SR-02 | met | contained after about 2 hours, against a 4-hour limit. | report:MNT-0253-030, MNT-0253-030, SR-02 |
| WELL-0281 | INS-0281-0207 | SR-02 | met | contained after about 2.7 hours, against a 4-hour limit. | report:MNT-0281-028, MNT-0281-028, SR-02 |
| WELL-0287 | INS-0287-0208 | SR-02 | met | contained after about 1.8 hours, against a 4-hour limit. | report:MNT-0287-027, MNT-0287-027, SR-02 |
| WELL-0299 | INS-0299-0210 | SR-02 | met | contained after about 3.6 hours, against a 4-hour limit. | report:MNT-0299-034, MNT-0299-034, SR-02 |
| WELL-0331 | INS-0331-0206 | SR-02 | breach | contained after about 4.8 hours, against a 4-hour limit (found only in the repair report). | report:MNT-0331-028, MNT-0331-028, SR-02 |
| WELL-0332 | INS-0332-0211 | SR-02 | met | contained after about 2.2 hours, against a 4-hour limit. | report:MNT-0332-033, MNT-0332-033, SR-02 |
| WELL-0381 | INS-0381-0205 | SR-02 | breach | contained after about 6 hours, against a 4-hour limit (found only in the repair report). | report:MNT-0381-032, MNT-0381-032, SR-02 |
| WELL-0383 | INS-0383-0211 | SR-02 | met | contained after about 1.7 hours, against a 4-hour limit. | report:MNT-0383-027, MNT-0383-027, SR-02 |
| WELL-0390 | INS-0390-0209 | SR-02 | met | contained after about 3.2 hours, against a 4-hour limit. | report:MNT-0390-030, MNT-0390-030, SR-02 |
| WELL-0404 | INS-0404-0206 | SR-02 | met | contained after about 3.4 hours, against a 4-hour limit. | report:MNT-0404-032, MNT-0404-032, SR-02 |
| WELL-0405 | INS-0405-0209 | SR-02 | breach | contained after about 6.2 hours, against a 4-hour limit (found only in the repair report). | report:MNT-0405-029, MNT-0405-029, SR-02 |
| WELL-0411 | INS-0411-0139 | SR-02 | met | contained after about 2.7 hours, against a 4-hour limit. | report:MNT-0411-021, MNT-0411-021, SR-02 |
| WELL-0420 | INS-0420-0211 | SR-02 | breach | contained after about 7 hours, against a 4-hour limit (found only in the repair report). | report:MNT-0420-032, MNT-0420-032, SR-02 |
| WELL-0422 | INS-0422-0205 | SR-02 | breach | contained after about 8.6 hours, against a 4-hour limit (found only in the repair report). | report:MNT-0422-030, MNT-0422-030, SR-02 |
| WELL-0429 | INS-0429-0210 | SR-02 | met | contained after about 3.7 hours, against a 4-hour limit. | report:MNT-0429-033, MNT-0429-033, SR-02 |
| WELL-0450 | INS-0450-0208 | SR-02 | breach | contained after about 5.8 hours, against a 4-hour limit (found only in the repair report). | report:MNT-0450-026, MNT-0450-026, SR-02 |
| WELL-0459 | INS-0459-0212 | SR-02 | breach | contained after about 4.6 hours, against a 4-hour limit (found only in the repair report). | report:MNT-0459-030, MNT-0459-030, SR-02 |

_16 more rows not shown_

**Evidence:** INS-0035-0210, INS-0062-0207, INS-0077-0204, INS-0113-0213, INS-0114-0210, INS-0117-0196, INS-0119-0209, INS-0134-0208, INS-0138-0211, INS-0143-0179, INS-0151-0209, INS-0169-0211, INS-0181-0212, INS-0189-0212, INS-0194-0209, INS-0200-0210, INS-0203-0213, INS-0225-0208, INS-0235-0212, INS-0240-0211, INS-0246-0126, INS-0253-0209, INS-0281-0207, INS-0287-0208, INS-0299-0210, INS-0331-0206, INS-0332-0211, INS-0381-0205, INS-0383-0211, INS-0390-0209 …

**Verification: NEEDS_REVIEW** — No independent recomputation exists for regulatory_events, so its result is not verified here. No independent recomputation exists for compliance_audit, so its result is not verified here. (EV-D42FFE869A)
_tools: regulatory_events, spills, compliance_audit · answer: verified facts · 72.1s_
_Showing the verified facts directly: the model rate limit was nearly used up, so the wording step was skipped._

### Q9a — Robert Hayes: How many recalled pumps are still in the ground, and in which areas?

I don't have any record of previously discussed recalled pumps in our conversation history. Could you please specify which pumps or wells you are referring to?

**Signals:** missing_evidence: No earlier conversation found for this user.

**Verification: NEEDS_REVIEW** — No independent recomputation exists for recall_discussed, so its result is not verified here. No independent rule classifies this question, so it cannot be confirmed that the tools used answer what was asked. (EV-D0B8ED5C84)
_tools: recall_discussed · answer: model · 58.5s_
