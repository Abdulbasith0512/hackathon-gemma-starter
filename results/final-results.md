# Copilot results

Dataset roots: data\test-data\dataset · as-of 2027-01-15 · model gemma-4-26b-a4b-it · thinking minimal

### Q1 — Michael Turner: All our wells feed one reservoir. Map the reservoir pressure across the field from the pressure data.

I cannot map the reservoir pressure because there is no tool available to retrieve reservoir pressure data or generate pressure maps.

**Visual: table** (Documents matching 'reservoir pressure map')

| Ref | Document | Section | Passage |
|---|---|---|---|
| SR-03 | Spill Response SOP | SR-03 |  … Take **at least 4 soil samples** to [map] the edges of a reportable spill. Haul soil above 5% TPH to an approved disposal site …  |
| T200#3 | T200 Rod-Lift Oil Well — Operating & Maintenance Manual | 3. Normal operation |  … Produced
fluid leaves the [reservoir] warmer than the surface air, so a producing wellhead
runs noticeably warmer than ambient. When the pump stops, the …  |
| T200#2 | T200 Rod-Lift Oil Well — Operating & Maintenance Manual | 2. Equipment overview |  … pump / Insert rod pump 1.75 in / Lifts fluid from the [reservoir] /
/ Flowline / 3 in carbon steel / Carries produced fluid to the gathering line …  |
| spill-response-sop#4 | Spill Response SOP | 4. Protocols |  … Take **at least 4 soil samples** to [map] the edges of a reportable spill. Haul soil above 5% TPH to an approved disposal site …  |
| T200#9.1 | T200 Rod-Lift Oil Well — Operating & Maintenance Manual | 9.1 Pressure | Maximum allowable wellhead working [pressure]: 3,000 psi. |

**Evidence:** SR-03, T200#3, T200#2, spill-response-sop#4, T200#9.1

_tools: search_documents · answer: model · 9.2s_

### Q2 — Robert Hayes: Which well produced the most oil in 2026?

I am unable to determine which well produced the most oil in 2026 because I do not have access to a tool that provides historical production volumes per well.

**Visual: table** (Wells not producing in the whole field (T350 wells))

| Well | Wellhead above air | Recorded status | Reason |
|---|---|---|---|
| WELL-0003 | 27.8 °C | active | producing |
| WELL-0004 | 27.0 °C | active | producing |
| WELL-0005 | 25.2 °C | active | producing |
| WELL-0007 | 31.9 °C | down | producing |
| WELL-0009 | 25.2 °C | active | producing |
| WELL-0012 | 30.3 °C | active | producing |
| WELL-0013 | 36.3 °C | down | producing |
| WELL-0014 | 30.4 °C | active | producing |
| WELL-0017 | 30.3 °C | active | producing |
| WELL-0021 | 25.2 °C | down | producing |
| WELL-0024 | 29.6 °C | active | producing |
| WELL-0025 | 27.0 °C | active | producing |
| WELL-0028 | 29.2 °C | active | producing |
| WELL-0029 | 33.1 °C | active | producing |
| WELL-0034 | 28.3 °C | active | producing |
| WELL-0038 | 26.0 °C | active | producing |
| WELL-0041 | 35.1 °C | active | producing |
| WELL-0045 | 25.8 °C | down | producing |
| WELL-0049 | 28.2 °C | active | producing |
| WELL-0054 | 30.7 °C | active | producing |
| WELL-0055 | 29.3 °C | active | producing |
| WELL-0056 | 26.2 °C | down | producing |
| WELL-0059 | 30.5 °C | active | producing |
| WELL-0063 | 31.3 °C | active | producing |
| WELL-0065 | 25.1 °C | active | producing |
| WELL-0073 | 32.5 °C | active | producing |
| WELL-0075 | 31.7 °C | active | producing |
| WELL-0079 | 31.5 °C | active | producing |
| WELL-0081 | 26.2 °C | active | producing |
| WELL-0088 | 26.8 °C | active | producing |
| WELL-0090 | 30.9 °C | active | producing |
| WELL-0095 | 35.6 °C | active | producing |
| WELL-0098 | 31.8 °C | active | producing |
| WELL-0099 | 32.0 °C | active | producing |
| WELL-0103 | 31.4 °C | active | producing |
| WELL-0107 | 27.1 °C | active | producing |
| WELL-0108 | 26.1 °C | active | producing |
| WELL-0109 | 29.7 °C | active | producing |
| WELL-0111 | 34.9 °C | active | producing |
| WELL-0114 | 30.5 °C | active | producing |

_144 more rows not shown_

**Evidence:** INS-0003-0216, INS-0004-0217, INS-0005-0218, INS-0007-0216, INS-0009-0217, INS-0012-0219, INS-0013-0219, INS-0014-0130, INS-0017-0219, INS-0021-0221, INS-0024-0219, INS-0025-0215, INS-0028-0217, INS-0029-0103, INS-0034-0172, INS-0038-0220, INS-0041-0219, INS-0045-0214, INS-0049-0218, INS-0054-0219, INS-0055-0216, INS-0056-0219, INS-0059-0219, INS-0063-0216, INS-0065-0217, INS-0073-0220, INS-0075-0218, INS-0079-0213, INS-0081-0215, INS-0088-0220 …

_tools: wells_not_producing · answer: model · 63.3s_

### Q3 — Laura Simmons: Since 1 Nov 2026, every time an operator note reports gas at a well, did we get someone out to that well in time under our operating procedures? List every report and whether the response met the deadline.

Operations SOP §ops-1-gas-odor-response OPS-1 Gas odor response: An [operator] [note] reporting a [gas] smell needs a field [response] on that well. A [gas] odor [report] is an
[operator] [note] saying the …  [operations-sop-rev2#ops-1-gas-odor-response]
T200 Rod-Lift Oil Well — Operating & Maintenance Manual §8 8. Spill response on the pad:  … Spill [Response] SOP
(`sops/spill-[response]-sop.md`). In short: stop the source, contain, estimate the
volume, and [report] within the [deadline] set by …  [T200#8]
Operations SOP §operator-notes Operator notes: Field operators record what they see on their rounds as [operator] notes: the records with
`[note]_type` = `[operator]_[note]` in the well's notes …  [operations-sop-rev2#operator-notes]
Operations SOP §ops-3-status-evidence-precedence OPS-3 Status evidence precedence:  … restart [note] is more recent than the latest
inspection, the well is **producing (unconfirmed)** until an inspection confirms it. Other [operator]
notes ([gas] odor …  [operations-sop-rev2#ops-3-status-evidence-precedence]
Operations SOP §ops-2-temporary-bypass OPS-2 Temporary bypass:  … A bypass is in place from the [operator] [note] that puts it in until the [operator] [note] that takes it
out.
It is a …  [operations-sop-rev2#ops-2-temporary-bypass]

**Visual: table** (Documents matching 'gas report operator note operating procedure response deadline')

| Ref | Document | Section | Passage |
|---|---|---|---|
| operations-sop-rev2#ops-1-gas-odor-response | Operations SOP | OPS-1 Gas odor response | An [operator] [note] reporting a [gas] smell needs a field [response] on that well. A [gas] odor [report] is an
[operator] [note] saying the …  |
| T200#8 | T200 Rod-Lift Oil Well — Operating & Maintenance Manual | 8. Spill response on the pad |  … Spill [Response] SOP
(`sops/spill-[response]-sop.md`). In short: stop the source, contain, estimate the
volume, and [report] within the [deadline] set by …  |
| operations-sop-rev2#operator-notes | Operations SOP | Operator notes | Field operators record what they see on their rounds as [operator] notes: the records with
`[note]_type` = `[operator]_[note]` in the well's notes …  |
| operations-sop-rev2#ops-3-status-evidence-precedence | Operations SOP | OPS-3 Status evidence precedence |  … restart [note] is more recent than the latest
inspection, the well is **producing (unconfirmed)** until an inspection confirms it. Other [operator]
notes ([gas] odor …  |
| operations-sop-rev2#ops-2-temporary-bypass | Operations SOP | OPS-2 Temporary bypass |  … A bypass is in place from the [operator] [note] that puts it in until the [operator] [note] that takes it
out.
It is a …  |

**Evidence:** operations-sop-rev2#ops-1-gas-odor-response, T200#8, operations-sop-rev2#operator-notes, operations-sop-rev2#ops-3-status-evidence-precedence, operations-sop-rev2#ops-2-temporary-bypass

_tools: search_documents · answer: verified facts · 2.4s_
_Showing the verified facts directly: the model rate limit was nearly used up, so the wording step was skipped._

### Q4 — Chris Dalton: Across all areas, which temporary flowline bypasses are in place right now, and is each one allowed? Also list any bypass, past or present, that stayed in after its approval ran out or was never approved at all.

Management of Change — MOC-2026-036 §change Change: A [temporary] [flowline] bypass is authorized on these wells: WELL-0087, WELL-0158, WELL-0249, WELL-0284, WELL-0356, WELL-0388, WELL-0461. [moc-2026-036#change]
Operations SOP §ops-2-temporary-bypass OPS-2 Temporary bypass: A [temporary] [flowline] bypass is allowed only on a well named in a management-of-change memo
(the `moc-*.md` files in `fleet/sops …  [operations-sop-rev2#ops-2-temporary-bypass]
Management of Change — MOC-2026-036 §management-of-change-moc-2026-036 Management of Change — MOC-2026-036: > Fictional memo for the FlytBase Asset Copilot hackathon.

**Title:** [Temporary] [flowline] bypass during the winter valve program
**Date:** 6 Nov 2026
**Requested by:** Robert …  [moc-2026-036#management-of-change-moc-2026-036]
Management of Change — MOC-2026-044 §management-of-change-moc-2026-044 Management of Change — MOC-2026-044: > Fictional memo for the FlytBase Asset Copilot hackathon.

**Title:** Extension of MOC-2026-031 ([temporary] [flowline] bypass)
**Date:** 24 Nov 2026
**Requested by:** Robert …  [moc-2026-044#management-of-change-moc-2026-044]
Management of Change — MOC-2026-031 §change Change: A [temporary] [flowline] bypass is authorized on these wells: WELL-0013, WELL-0062, WELL-0118, WELL-0248, WELL-0476.

The bypass routes production around …  [moc-2026-031#change]
operator_note CTX-0087-001 by Jake Morales (valid 2 Dec 2026 onward): "Crew had the bypass installed at WELL-0087 by mid-morning."
operator_note CTX-0087-002 by Sarah Mitchell (valid 21 Dec 2026 onward): "Checked WELL-0087 after the rain, pad dry and clean."
operator_note CTX-0087-003 by Jake Morales (valid 29 Dec 2026 onward): "Rod squeal at WELL-0087 stuffing box, greased the polished rod."
operator_note CTX-0087-004 by Ryan Brooks (valid 6 Jan 2027 onward): "Took the bypass out at WELL-0087 after the valve was replaced."
operator_note CTX-0087-005 by Jake Morales (valid 10 Jan 2027 onward): "WELL-0087 tank gauged, level normal."
operator_note CTX-0158-002 by Ashley Bennett (valid 6 Nov 2026 onward): "Checked WELL-0158 after the rain, pad dry and clean."
operator_note CTX-0158-003 by Tyler Hughes (valid 20 Nov 2026 onward): "Put the bypass in at WELL-0158 so the flowline can stay in service."
operator_note CTX-0158-004 by Tyler Hughes (valid 29 Nov 2026 onward): "WELL-0158 pumping normally."
operator_note CTX-0158-005 by Ashley Bennett (valid 28 Dec 2026 onward): "Bypass removed from WELL-0158, flowline back to normal routing."
operator_note CTX-0249-002 by Diego Ramirez (valid 25 Nov 2026 onward): "Bypass installed on WELL-0249 flowline around the leaking check valve."
operator_note CTX-0249-003 by Kayla Morgan (valid 1 Jan 2027 onward): "Checked WELL-0249 after the rain, pad dry and clean."
operator_note CTX-0249-004 by Marcus Lee (valid 13 Jan 2027 onward): "WELL-0249 drive tripping on underload, restarted from the panel."
Open repair MNT-0249-018: ESP motor burnout, started 9 Jan 2027, planned end 2 Feb 2027; technician: Daniel Foster (U-302).
operator_note CTX-0284-002 by Sarah Mitchell (valid 12 Nov 2026 onward): "Bypass installed on WELL-0284 flowline around the leaking check valve."
operator_note CTX-0284-003 by Ryan Brooks (valid 10 Dec 2026 onward): "WELL-0284: valve work finished and bypass removed."
operator_note CTX-0284-004 by Sarah Mitchell (valid 18 Dec 2026 onward): "Walked the flowline at WELL-0284, nothing to report."
operator_note CTX-0284-005 by Ryan Brooks (valid 25 Dec 2026 onward): "WELL-0284 pumping normally."
operator_note CTX-0356-002 by Brandon Shaw (valid 18 Nov 2026 onward): "Bypass installed on WELL-0356 flowline around the leaking check valve."
operator_note CTX-0356-003 by Lauren Pruitt (valid 5 Dec 2026 onward): "Bypass removed from WELL-0356, flowline back to normal routing."
operator_note CTX-0356-004 by Austin Kemp (valid 3 Jan 2027 onward): "WELL-0356 pumping normally."
operator_note CTX-0356-005 by Lauren Pruitt (valid 13 Jan 2027 onward): "Pumper reports rattling at WELL-0356 pump jack, keep an eye on it."

**Visual: table** (Documents matching 'temporary flowline bypasses')

| Ref | Document | Section | Passage |
|---|---|---|---|
| moc-2026-036#change | Management of Change — MOC-2026-036 | Change | A [temporary] [flowline] bypass is authorized on these wells: WELL-0087, WELL-0158, WELL-0249, WELL-0284, WELL-0356, WELL-0388, WELL-0461. |
| operations-sop-rev2#ops-2-temporary-bypass | Operations SOP | OPS-2 Temporary bypass | A [temporary] [flowline] bypass is allowed only on a well named in a management-of-change memo
(the `moc-*.md` files in `fleet/sops …  |
| moc-2026-036#management-of-change-moc-2026-036 | Management of Change — MOC-2026-036 | Management of Change — MOC-2026-036 | > Fictional memo for the FlytBase Asset Copilot hackathon.

**Title:** [Temporary] [flowline] bypass during the winter valve program
**Date:** 6 Nov 2026
**Requested by:** Robert …  |
| moc-2026-044#management-of-change-moc-2026-044 | Management of Change — MOC-2026-044 | Management of Change — MOC-2026-044 | > Fictional memo for the FlytBase Asset Copilot hackathon.

**Title:** Extension of MOC-2026-031 ([temporary] [flowline] bypass)
**Date:** 24 Nov 2026
**Requested by:** Robert …  |
| moc-2026-031#change | Management of Change — MOC-2026-031 | Change | A [temporary] [flowline] bypass is authorized on these wells: WELL-0013, WELL-0062, WELL-0118, WELL-0248, WELL-0476.

The bypass routes production around …  |

**Visual: table** (Notes and planned work for WELL-0087)

| Note | Type | Author | Valid from | Valid to | Text |
|---|---|---|---|---|---|
| CTX-0087-001 | operator_note | Jake Morales | 2026-12-02 |  | Crew had the bypass installed at WELL-0087 by mid-morning. |
| CTX-0087-002 | operator_note | Sarah Mitchell | 2026-12-21 |  | Checked WELL-0087 after the rain, pad dry and clean. |
| CTX-0087-003 | operator_note | Jake Morales | 2026-12-29 |  | Rod squeal at WELL-0087 stuffing box, greased the polished rod. |
| CTX-0087-004 | operator_note | Ryan Brooks | 2027-01-06 |  | Took the bypass out at WELL-0087 after the valve was replaced. |
| CTX-0087-005 | operator_note | Jake Morales | 2027-01-10 |  | WELL-0087 tank gauged, level normal. |

**Visual: table** (Notes and planned work for WELL-0158)

| Note | Type | Author | Valid from | Valid to | Text |
|---|---|---|---|---|---|
| CTX-0158-002 | operator_note | Ashley Bennett | 2026-11-06 |  | Checked WELL-0158 after the rain, pad dry and clean. |
| CTX-0158-003 | operator_note | Tyler Hughes | 2026-11-20 |  | Put the bypass in at WELL-0158 so the flowline can stay in service. |
| CTX-0158-004 | operator_note | Tyler Hughes | 2026-11-29 |  | WELL-0158 pumping normally. |
| CTX-0158-005 | operator_note | Ashley Bennett | 2026-12-28 |  | Bypass removed from WELL-0158, flowline back to normal routing. |

**Visual: table** (Notes and planned work for WELL-0249)

| Note | Type | Author | Valid from | Valid to | Text |
|---|---|---|---|---|---|
| CTX-0249-002 | operator_note | Diego Ramirez | 2026-11-25 |  | Bypass installed on WELL-0249 flowline around the leaking check valve. |
| CTX-0249-003 | operator_note | Kayla Morgan | 2027-01-01 |  | Checked WELL-0249 after the rain, pad dry and clean. |
| CTX-0249-004 | operator_note | Marcus Lee | 2027-01-13 |  | WELL-0249 drive tripping on underload, restarted from the panel. |

**Visual: table** (Notes and planned work for WELL-0284)

| Note | Type | Author | Valid from | Valid to | Text |
|---|---|---|---|---|---|
| CTX-0284-002 | operator_note | Sarah Mitchell | 2026-11-12 |  | Bypass installed on WELL-0284 flowline around the leaking check valve. |
| CTX-0284-003 | operator_note | Ryan Brooks | 2026-12-10 |  | WELL-0284: valve work finished and bypass removed. |
| CTX-0284-004 | operator_note | Sarah Mitchell | 2026-12-18 |  | Walked the flowline at WELL-0284, nothing to report. |
| CTX-0284-005 | operator_note | Ryan Brooks | 2026-12-25 |  | WELL-0284 pumping normally. |

**Visual: table** (Notes and planned work for WELL-0356)

| Note | Type | Author | Valid from | Valid to | Text |
|---|---|---|---|---|---|
| CTX-0356-002 | operator_note | Brandon Shaw | 2026-11-18 |  | Bypass installed on WELL-0356 flowline around the leaking check valve. |
| CTX-0356-003 | operator_note | Lauren Pruitt | 2026-12-05 |  | Bypass removed from WELL-0356, flowline back to normal routing. |
| CTX-0356-004 | operator_note | Austin Kemp | 2027-01-03 |  | WELL-0356 pumping normally. |
| CTX-0356-005 | operator_note | Lauren Pruitt | 2027-01-13 |  | Pumper reports rattling at WELL-0356 pump jack, keep an eye on it. |

**Evidence:** moc-2026-036#change, operations-sop-rev2#ops-2-temporary-bypass, moc-2026-036#management-of-change-moc-2026-036, moc-2026-044#management-of-change-moc-2026-044, moc-2026-031#change, WELL-0087, CTX-0087-001, CTX-0087-002, CTX-0087-003, CTX-0087-004, CTX-0087-005, INS-0087-0218, WELL-0158, CTX-0158-002, CTX-0158-003, CTX-0158-004, CTX-0158-005, INS-0158-0219, WELL-0249, CTX-0249-002, CTX-0249-003, CTX-0249-004, INS-0249-0120, MNT-0249-018, WELL-0284, CTX-0284-002, CTX-0284-003, CTX-0284-004, CTX-0284-005, INS-0284-0218 …

_tools: search_documents, well_context, well_context, well_context, well_context, well_context · answer: verified facts · 68.5s_
_Showing the verified facts directly: the model rate limit was nearly used up, so the wording step was skipped._

### Q5 — Michael Turner: The State Oil & Gas Commission wrote to us in November 2026 about spills. Which of our spills does the letter cover, and on which ones are we not compliant? Show me a table.

0 regulator event(s) in the whole field, 1 Nov 2026 to 30 Nov 2026; fines USD 0, of which USD 0 still open.

**Visual: table** (Regulator events in the whole field, 1 Nov 2026 to 30 Nov 2026)

| Event | Well | Date | Type | Protocol | Status | Fine (USD) | Detail |
|---|---|---|---|---|---|---|---|


_tools: regulatory_events · answer: verified facts · 3.4s_
_Showing the verified facts directly: the model rate limit was nearly used up, so the wording step was skipped._

### Q6 — Nathan Pierce: Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right now, and why?

In the whole field: 554 producing, 46 not producing (latest inspection, 600 well(s)).
WELL-0010 (T350): 17.5 °C above air on 14 Jan 2027; recorded status active (out of date); Note CTX-0010-003 by Ryan Brooks (8 Jan 2027): "Repair crew on WELL-0010, shut the well in for them.". [INS-0010-0219]
WELL-0026 (T200): 5.4 °C above air on 14 Jan 2027; recorded status down; Repair MNT-0026-034: Flowline corrosion pinhole leak, started 3 Jan 2027, still open. [INS-0026-0216]
WELL-0032 (T350): 7.4 °C above air on 14 Jan 2027; recorded status active (out of date); No recorded reason. The inspector noted "Wellhead cold to touch.". [INS-0032-0219]
WELL-0033 (T350): 10.0 °C above air on 14 Jan 2027; recorded status active (out of date); Repair MNT-0033-033: Walking beam bearing wear, started 9 Jan 2027, still open. [INS-0033-0222]
WELL-0046 (T200): 2.1 °C above air on 14 Jan 2027; recorded status down; Repair MNT-0046-028: Stuffing box packing leak, started 1 Jan 2027, still open. [INS-0046-0220]
WELL-0053 (T200): 2.3 °C above air on 14 Jan 2027; recorded status active (out of date); No recorded reason. The inspector noted "Wellhead cold to touch.". [INS-0053-0220]
WELL-0069 (T200): 4.8 °C above air on 14 Jan 2027; recorded status active (out of date); No recorded reason. [INS-0069-0217]
WELL-0093 (T350): 4.5 °C above air on 14 Jan 2027; recorded status active (out of date); No recorded reason. [INS-0093-0216]
WELL-0097 (T350): 6.5 °C above air on 14 Jan 2027; recorded status active (out of date); No recorded reason. [INS-0097-0215]
WELL-0105 (T200): 3.9 °C above air on 14 Jan 2027; recorded status active (out of date); No recorded reason. The inspector noted "Wellhead cold to touch.". [INS-0105-0216]
WELL-0133 (T200): 4.0 °C above air on 14 Jan 2027; recorded status active (out of date); No recorded reason. The inspector noted "Unit stopped, brake set.". [INS-0133-0219]
WELL-0134 (T350): 3.2 °C above air on 14 Jan 2027; recorded status active (out of date); No recorded reason. [INS-0134-0216]
WELL-0160 (T200): 3.8 °C above air on 14 Jan 2027; recorded status active (out of date); No recorded reason. The inspector noted "Wellhead cold to touch.". [INS-0160-0217]
WELL-0167 (T200): 1.5 °C above air on 14 Jan 2027; recorded status active (out of date); No recorded reason. [INS-0167-0119]
WELL-0169 (T200): 5.2 °C above air on 14 Jan 2027; recorded status active (out of date); Repair MNT-0169-028: Stuffing box packing leak, started 8 Jan 2027, still open. [INS-0169-0219]
WELL-0175 (T200): 5.5 °C above air on 14 Jan 2027; recorded status active (out of date); No recorded reason. The inspector noted "Pump jack not moving.". [INS-0175-0216]
WELL-0197 (T200): 1.2 °C above air on 14 Jan 2027; recorded status down; Repair MNT-0197-029: Sucker rod parted, started 1 Jan 2027, still open. [INS-0197-0214]
WELL-0199 (T200): 4.1 °C above air on 31 Dec 2026; recorded status plugged; Repair MNT-0199-033: Prime mover failure, started 20 Dec 2026, completed 5 Jan 2027. [INS-0199-0216]
WELL-0203 (T500): 22.4 °C above air on 14 Jan 2027; recorded status active (out of date); No recorded reason. [INS-0203-0221]
WELL-0213 (T200): 1.5 °C above air on 14 Jan 2027; recorded status active (out of date); No recorded reason. [INS-0213-0221]
WELL-0219 (T500): 4.5 °C above air on 14 Jan 2027; recorded status active (out of date); No recorded reason. The inspector noted "No flow noise at the wellhead.". [INS-0219-0171]
WELL-0249 (T500): 5.9 °C above air on 14 Jan 2027; recorded status active (out of date); Repair MNT-0249-018: ESP motor burnout, started 9 Jan 2027, still open. [INS-0249-0120]
WELL-0251 (T200): -0.4 °C above air on 14 Jan 2027; recorded status active (out of date); Repair MNT-0251-029: Gearbox oil leak, started 9 Jan 2027, still open. [INS-0251-0215]
WELL-0263 (T350): 4.0 °C above air on 14 Jan 2027; recorded status active (out of date); Repair MNT-0263-035: Flowline corrosion pinhole leak, started 9 Jan 2027, still open. [INS-0263-0219]
WELL-0281 (T350): 10.2 °C above air on 14 Jan 2027; recorded status down; Repair MNT-0281-031: Flowline corrosion pinhole leak, started 2 Jan 2027, still open. [INS-0281-0214]
WELL-0309 (T200): 2.5 °C above air on 14 Jan 2027; recorded status active (out of date); No recorded reason. [INS-0309-0215]
WELL-0316 (T350): 1.0 °C above air on 14 Jan 2027; recorded status active (out of date); No recorded reason. The inspector noted "Pump jack not moving.". [INS-0316-0217]
WELL-0330 (T200): 4.4 °C above air on 14 Jan 2027; recorded status down; Repair MNT-0330-030: Flowline corrosion pinhole leak, started 3 Jan 2027, still open; Note CTX-0330-001 by Austin Kemp (18 Dec 2026): "Shut in WELL-0330 at the wellhead for the repair crew."; Note CTX-0330-002 by Rachel Dunn (19 Dec 2026): "WELL-0330 put back on production after the repair crew finished.". [INS-0330-0213]
WELL-0332 (T200): 0.5 °C above air on 14 Jan 2027; recorded status active (out of date); Note CTX-0332-002 by Austin Kemp (20 Nov 2026): "Shut-in WELL-0332 so the maintenance crew can start work.". [INS-0332-0217]
WELL-0373 (T200): 1.1 °C above air on 14 Jan 2027; recorded status active (out of date); No recorded reason. The inspector noted "No stroke observed during flight.". [INS-0373-0219]
WELL-0377 (T350): 0.4 °C above air on 14 Jan 2027; recorded status active (out of date); Repair MNT-0377-037: Prime mover failure, started 10 Jan 2027, still open. [INS-0377-0220]
WELL-0397 (T200): 5.2 °C above air on 14 Jan 2027; recorded status active (out of date); Repair MNT-0397-032: Sucker rod parted, started 9 Jan 2027, still open. [INS-0397-0219]
WELL-0404 (T200): 1.8 °C above air on 14 Jan 2027; recorded status down; Repair MNT-0404-034: Flowline corrosion pinhole leak, started 27 Dec 2026, still open. [INS-0404-0214]
WELL-0408 (T350): 7.1 °C above air on 14 Jan 2027; recorded status active (out of date); No recorded reason. [INS-0408-0218]
WELL-0418 (T350): 8.2 °C above air on 14 Jan 2027; recorded status active (out of date); No recorded reason. The inspector noted "Unit stopped, brake set.". [INS-0418-0219]
WELL-0429 (T350): 6.2 °C above air on 14 Jan 2027; recorded status active (out of date); Note CTX-0429-001 by Austin Kemp (23 Oct 2026): "Shut in WELL-0429 at the wellhead for the repair crew."; Note CTX-0429-003 by Rachel Dunn (13 Nov 2026): "Shut in WELL-0429 at the wellhead for the repair crew.". [INS-0429-0219]
WELL-0442 (T350): 2.5 °C above air on 14 Jan 2027; recorded status active (out of date); No recorded reason. [INS-0442-0220]
WELL-0452 (T350): 3.1 °C above air on 14 Jan 2027; recorded status down; Repair MNT-0452-031: Downhole pump stuck, started 2 Jan 2027, still open; Note CTX-0452-004 by Derek Walsh (13 Dec 2026): "Repair crew on WELL-0452, shut the well in for them.". [INS-0452-0219]
WELL-0471 (T350): 1.8 °C above air on 14 Jan 2027; recorded status active (out of date); No recorded reason. [INS-0471-0219]
WELL-0490 (T200): 5.1 °C above air on 14 Jan 2027; recorded status active (out of date); No recorded reason. [INS-0490-0170]
WELL-0496 (T500): 8.7 °C above air on 14 Jan 2027; recorded status down; Repair MNT-0496-033: Flowline corrosion pinhole leak, started 19 Dec 2026, still open. [INS-0496-0220]
WELL-0526 (T200): 2.7 °C above air on 14 Jan 2027; recorded status down; Repair MNT-0526-026: Prime mover failure, started 2 Jan 2027, still open. [INS-0526-0218]
WELL-0528 (T200): 3.1 °C above air on 14 Jan 2027; recorded status down; Repair MNT-0528-031: Gearbox oil leak, started 3 Jan 2027, still open. [INS-0528-0220]
WELL-0540 (T200): 1.8 °C above air on 14 Jan 2027; recorded status active (out of date); Repair MNT-0540-025: Prime mover failure, started 9 Jan 2027, still open. [INS-0540-0215]
WELL-0545 (T350): 4.1 °C above air on 14 Jan 2027; recorded status active (out of date); No recorded reason. [INS-0545-0218]
WELL-0562 (T200): 2.4 °C above air on 14 Jan 2027; recorded status down; Repair MNT-0562-025: Separator level controller fault, started 2 Jan 2027, still open. [INS-0562-0219]
WELL-0010 is not producing oil. At the latest inspection INS-0010-0219 the wellhead was 17.5 °C warmer than the air (27.7 °C vs 10.2 °C), below the T350 limit of 20.0 °C. [T350#3]
Latest inspection INS-0010-0219 on 14 Jan 2027 by drone, by Sarah Mitchell.
Reason: Note CTX-0010-003 by Ryan Brooks (8 Jan 2027): "Repair crew on WELL-0010, shut the well in for them.".
The recorded status in the system is 'active', which is out of date; the inspections are the truth. [WELL-0010]
WELL-0032 is not producing oil. At the latest inspection INS-0032-0219 the wellhead was 7.4 °C warmer than the air (19.4 °C vs 12.0 °C), below the T350 limit of 20.0 °C. [T350#3]
Latest inspection INS-0032-0219 on 14 Jan 2027 by drone, by Sarah Mitchell.
No recorded reason explains the stop; the inspector noted "Wellhead cold to touch.". Suggest a field check. [INS-0032-0219]
The recorded status in the system is 'active', which is out of date; the inspections are the truth. [WELL-0032]
WELL-0033 is not producing oil. At the latest inspection INS-0033-0222 the wellhead was 10.0 °C warmer than the air (16.2 °C vs 6.2 °C), below the T350 limit of 20.0 °C. [T350#3]
Latest inspection INS-0033-0222 on 14 Jan 2027 by drone, by Sarah Mitchell.
Reason: Repair MNT-0033-033: Walking beam bearing wear, started 9 Jan 2027, still open.
The recorded status in the system is 'active', which is out of date; the inspections are the truth. [WELL-0033]
WELL-0053 is not producing oil. At the latest inspection INS-0053-0220 the wellhead was 2.3 °C warmer than the air (10.0 °C vs 7.7 °C), below the T200 limit of 15.0 °C. [T200#9.3]
Latest inspection INS-0053-0220 on 14 Jan 2027 by drone, by Diego Ramirez.
No recorded reason explains the stop; the inspector noted "Wellhead cold to touch.". Suggest a field check. [INS-0053-0220]
The recorded status in the system is 'active', which is out of date; the inspections are the truth. [WELL-0053]
WELL-0069 is not producing oil. At the latest inspection INS-0069-0217 the wellhead was 4.8 °C warmer than the air (9.0 °C vs 4.2 °C), below the T200 limit of 15.0 °C. [T200#9.3]
Latest inspection INS-0069-0217 on 14 Jan 2027 by manual, by Jake Morales.
No recorded reason explains the stop. Suggest a field check. [INS-0069-0217]
The recorded status in the system is 'active', which is out of date; the inspections are the truth. [WELL-0069]

**Visual: table** (Wells not producing in the whole field)

| Well | Wellhead above air | Recorded status | Reason |
|---|---|---|---|
| WELL-0010 | 17.5 °C | active (out of date) | Note CTX-0010-003 by Ryan Brooks (8 Jan 2027): "Repair crew on WELL-0010, shut the well in for them." |
| WELL-0026 | 5.4 °C | down | Repair MNT-0026-034: Flowline corrosion pinhole leak, started 3 Jan 2027, still open |
| WELL-0032 | 7.4 °C | active (out of date) | No recorded reason. The inspector noted "Wellhead cold to touch." |
| WELL-0033 | 10.0 °C | active (out of date) | Repair MNT-0033-033: Walking beam bearing wear, started 9 Jan 2027, still open |
| WELL-0046 | 2.1 °C | down | Repair MNT-0046-028: Stuffing box packing leak, started 1 Jan 2027, still open |
| WELL-0053 | 2.3 °C | active (out of date) | No recorded reason. The inspector noted "Wellhead cold to touch." |
| WELL-0069 | 4.8 °C | active (out of date) | No recorded reason |
| WELL-0093 | 4.5 °C | active (out of date) | No recorded reason |
| WELL-0097 | 6.5 °C | active (out of date) | No recorded reason |
| WELL-0105 | 3.9 °C | active (out of date) | No recorded reason. The inspector noted "Wellhead cold to touch." |
| WELL-0133 | 4.0 °C | active (out of date) | No recorded reason. The inspector noted "Unit stopped, brake set." |
| WELL-0134 | 3.2 °C | active (out of date) | No recorded reason |
| WELL-0160 | 3.8 °C | active (out of date) | No recorded reason. The inspector noted "Wellhead cold to touch." |
| WELL-0167 | 1.5 °C | active (out of date) | No recorded reason |
| WELL-0169 | 5.2 °C | active (out of date) | Repair MNT-0169-028: Stuffing box packing leak, started 8 Jan 2027, still open |
| WELL-0175 | 5.5 °C | active (out of date) | No recorded reason. The inspector noted "Pump jack not moving." |
| WELL-0197 | 1.2 °C | down | Repair MNT-0197-029: Sucker rod parted, started 1 Jan 2027, still open |
| WELL-0199 | 4.1 °C | plugged | Repair MNT-0199-033: Prime mover failure, started 20 Dec 2026, completed 5 Jan 2027 |
| WELL-0203 | 22.4 °C | active (out of date) | No recorded reason |
| WELL-0213 | 1.5 °C | active (out of date) | No recorded reason |
| WELL-0219 | 4.5 °C | active (out of date) | No recorded reason. The inspector noted "No flow noise at the wellhead." |
| WELL-0249 | 5.9 °C | active (out of date) | Repair MNT-0249-018: ESP motor burnout, started 9 Jan 2027, still open |
| WELL-0251 | -0.4 °C | active (out of date) | Repair MNT-0251-029: Gearbox oil leak, started 9 Jan 2027, still open |
| WELL-0263 | 4.0 °C | active (out of date) | Repair MNT-0263-035: Flowline corrosion pinhole leak, started 9 Jan 2027, still open |
| WELL-0281 | 10.2 °C | down | Repair MNT-0281-031: Flowline corrosion pinhole leak, started 2 Jan 2027, still open |
| WELL-0309 | 2.5 °C | active (out of date) | No recorded reason |
| WELL-0316 | 1.0 °C | active (out of date) | No recorded reason. The inspector noted "Pump jack not moving." |
| WELL-0330 | 4.4 °C | down | Repair MNT-0330-030: Flowline corrosion pinhole leak, started 3 Jan 2027, still open; Note CTX-0330-001 by Austin Kemp (18 Dec 2026): "Shut in WELL-0330 at the wellhead for the repair crew."; Note CTX-0330-002 by Rachel Dunn (19 Dec 2026): "WELL-0330 put back on production after the repair crew finished." |
| WELL-0332 | 0.5 °C | active (out of date) | Note CTX-0332-002 by Austin Kemp (20 Nov 2026): "Shut-in WELL-0332 so the maintenance crew can start work." |
| WELL-0373 | 1.1 °C | active (out of date) | No recorded reason. The inspector noted "No stroke observed during flight." |
| WELL-0377 | 0.4 °C | active (out of date) | Repair MNT-0377-037: Prime mover failure, started 10 Jan 2027, still open |
| WELL-0397 | 5.2 °C | active (out of date) | Repair MNT-0397-032: Sucker rod parted, started 9 Jan 2027, still open |
| WELL-0404 | 1.8 °C | down | Repair MNT-0404-034: Flowline corrosion pinhole leak, started 27 Dec 2026, still open |
| WELL-0408 | 7.1 °C | active (out of date) | No recorded reason |
| WELL-0418 | 8.2 °C | active (out of date) | No recorded reason. The inspector noted "Unit stopped, brake set." |
| WELL-0429 | 6.2 °C | active (out of date) | Note CTX-0429-001 by Austin Kemp (23 Oct 2026): "Shut in WELL-0429 at the wellhead for the repair crew."; Note CTX-0429-003 by Rachel Dunn (13 Nov 2026): "Shut in WELL-0429 at the wellhead for the repair crew." |
| WELL-0442 | 2.5 °C | active (out of date) | No recorded reason |
| WELL-0452 | 3.1 °C | down | Repair MNT-0452-031: Downhole pump stuck, started 2 Jan 2027, still open; Note CTX-0452-004 by Derek Walsh (13 Dec 2026): "Repair crew on WELL-0452, shut the well in for them." |
| WELL-0471 | 1.8 °C | active (out of date) | No recorded reason |
| WELL-0490 | 5.1 °C | active (out of date) | No recorded reason |

_560 more rows not shown_

**Visual: status_card** (Status of WELL-0010)
**Visual: status_card** (Status of WELL-0032)
**Visual: status_card** (Status of WELL-0033)
**Visual: status_card** (Status of WELL-0053)
**Visual: status_card** (Status of WELL-0069)
**Signals:** missing_evidence: WELL-0032: nothing in the records explains the stop; check the pad.; missing_evidence: WELL-0053: nothing in the records explains the stop; check the pad.; missing_evidence: WELL-0069: nothing in the records explains the stop; check the pad.; missing_evidence: WELL-0093: nothing in the records explains the stop; check the pad.; missing_evidence: WELL-0097: nothing in the records explains the stop; check the pad.; missing_evidence: WELL-0105: nothing in the records explains the stop; check the pad.; missing_evidence: WELL-0133: nothing in the records explains the stop; check the pad.; missing_evidence: WELL-0134: nothing in the records explains the stop; check the pad.

**Evidence:** INS-0001-0216, INS-0002-0154, INS-0003-0216, INS-0004-0217, INS-0005-0218, INS-0006-0214, INS-0007-0216, INS-0008-0218, INS-0009-0217, INS-0010-0219, CTX-0010-003, INS-0011-0218, INS-0012-0219, INS-0013-0219, INS-0014-0130, INS-0015-0219, INS-0016-0197, INS-0017-0219, INS-0018-0219, INS-0019-0219, INS-0020-0220, INS-0021-0221, INS-0022-0210, INS-0023-0220, INS-0024-0219, INS-0025-0215, INS-0026-0216, MNT-0026-034, INS-0027-0219, INS-0028-0217 …

_tools: wells_not_producing, well_status, well_status, well_status, well_status, well_status · answer: verified facts · 63.4s_
_Showing the verified facts directly: the model rate limit was nearly used up, so the wording step was skipped._

### Q7a — Robert Hayes: Over the last month the operators have written notes about wells that sound or behave wrong. Which of those wells haven't had a repair since? Rank the 10 most likely to need a repair in the next 90 days, other than a spill clean-up, and quote the notes as evidence.

In your earlier conversation (17 Oct 2026) you asked "Which well produced the most oil in 2026?" which covered: WELL-0003, WELL-0004, WELL-0005, WELL-0007, WELL-0009, WELL-0012, WELL-0013, WELL-0014, WELL-0017, WELL-0021, WELL-0024, WELL-0025, WELL-0028, WELL-0029, WELL-0034, WELL-0038, WELL-0041, WELL-0045, WELL-0049, WELL-0054, WELL-0055, WELL-0056, WELL-0059, WELL-0063, WELL-0065, WELL-0073, WELL-0075, WELL-0079, WELL-0081, WELL-0088, WELL-0090, WELL-0095, WELL-0098, WELL-0099, WELL-0103, WELL-0107, WELL-0108, WELL-0109, WELL-0111, WELL-0114, WELL-0120, WELL-0122, WELL-0125, WELL-0127, WELL-0128, WELL-0129, WELL-0131, WELL-0132, WELL-0137, WELL-0138, WELL-0139, WELL-0142, WELL-0144, WELL-0145, WELL-0149, WELL-0150, WELL-0151, WELL-0153, WELL-0157, WELL-0158, WELL-0159, WELL-0161, WELL-0162, WELL-0163, WELL-0171, WELL-0174, WELL-0176, WELL-0183, WELL-0184, WELL-0187, WELL-0189, WELL-0191, WELL-0192, WELL-0193, WELL-0198, WELL-0200, WELL-0204, WELL-0207, WELL-0211, WELL-0221, WELL-0224, WELL-0225, WELL-0240, WELL-0252, WELL-0256, WELL-0260, WELL-0261, WELL-0266, WELL-0268, WELL-0274, WELL-0275, WELL-0277, WELL-0280, WELL-0293, WELL-0297, WELL-0298, WELL-0300, WELL-0302, WELL-0304, WELL-0308, WELL-0311, WELL-0312, WELL-0313, WELL-0315, WELL-0321, WELL-0325, WELL-0326, WELL-0331, WELL-0337, WELL-0339, WELL-0340, WELL-0345, WELL-0346, WELL-0347, WELL-0349, WELL-0350, WELL-0353, WELL-0365, WELL-0372, WELL-0378, WELL-0380, WELL-0381, WELL-0383, WELL-0390, WELL-0391, WELL-0393, WELL-0395, WELL-0409, WELL-0414, WELL-0422, WELL-0425, WELL-0426, WELL-0432, WELL-0444, WELL-0447, WELL-0450, WELL-0453, WELL-0454, WELL-0456, WELL-0459, WELL-0461, WELL-0462, WELL-0465, WELL-0468, WELL-0477, WELL-0497, WELL-0500, WELL-0501, WELL-0502, WELL-0503, WELL-0504, WELL-0508, WELL-0509, WELL-0510, WELL-0512, WELL-0513, WELL-0514, WELL-0522, WELL-0524, WELL-0525, WELL-0527, WELL-0529, WELL-0530, WELL-0533, WELL-0534, WELL-0537, WELL-0538, WELL-0549, WELL-0554, WELL-0555, WELL-0563, WELL-0565, WELL-0568, WELL-0569, WELL-0571, WELL-0573, WELL-0575, WELL-0579, WELL-0581, WELL-0584, WELL-0587, WELL-0591, WELL-0598, WELL-0600.
Unknown well 'all'.
Maintenance report MNT-0001-029 §notes-and-recommendations Notes and recommendations:  … on this well instead of patching sections; two failures in a [month] show the line is in poor condition.
- Add a visual check of …  [MNT-0001-029#notes-and-recommendations]
Maintenance report MNT-0001-029 §root-cause Root cause:  … This is the
second flowline failure in a [month] on this well: a pinhole leak was repaired on 10 May 2026
(MNT-0001-028 …  [MNT-0001-029#root-cause]
Operations SOP §operator-notes Operator notes: Field operators record what they see on their rounds as [operator] [notes]: the records with
`note_type` = `[operator]_note` in the well's [notes] …  [operations-sop-rev2#operator-notes]
Maintenance report MNT-0206-015 §root-cause Root cause: Cable crushed against the tubing during the [last] installation.
This is corrective repair number 3 on this well's esp pump in the [last] …  [MNT-0206-015#root-cause]
Maintenance report MNT-0352-027 §root-cause Root cause: Cable crushed against the tubing during the [last] installation.
This is corrective repair number 3 on this well's esp pump in the [last] …  [MNT-0352-027#root-cause]
13 well(s) in the whole field need a root-cause analysis on the pump jack: WELL-0069, WELL-0108, WELL-0121, WELL-0135, WELL-0138, WELL-0159, WELL-0170, WELL-0182, WELL-0298, WELL-0374, WELL-0484, WELL-0529, WELL-0599.
WELL-0069 (T200): 3 corrective pump jack repairs in the last 12 months (threshold 3, T200 manual): MNT-0069-032, MNT-0069-034, MNT-0069-039. [T200#10]
WELL-0108 (T350): 3 corrective pump jack repairs in the last 12 months (threshold 3, T350 manual): MNT-0108-024, MNT-0108-026, MNT-0108-028. [T350#6]
WELL-0121 (T200): 3 corrective pump jack repairs in the last 12 months (threshold 3, T200 manual): MNT-0121-031, MNT-0121-034, MNT-0121-035. [T200#10]
WELL-0135 (T200): 3 corrective pump jack repairs in the last 12 months (threshold 3, T200 manual): MNT-0135-031, MNT-0135-033, MNT-0135-034. [T200#10]
WELL-0138 (T350): 3 corrective pump jack repairs in the last 12 months (threshold 3, T350 manual): MNT-0138-031, MNT-0138-032, MNT-0138-034. [T350#6]
WELL-0159 (T350): 3 corrective pump jack repairs in the last 12 months (threshold 3, T350 manual): MNT-0159-025, MNT-0159-029, MNT-0159-031. [T350#6]
WELL-0170 (T200): 3 corrective pump jack repairs in the last 12 months (threshold 3, T200 manual): MNT-0170-026, MNT-0170-031, MNT-0170-032. [T200#10]
WELL-0182 (T200): 4 corrective pump jack repairs in the last 12 months (threshold 3, T200 manual): MNT-0182-021, MNT-0182-023, MNT-0182-027, MNT-0182-029. [T200#10]
WELL-0298 (T350): 3 corrective pump jack repairs in the last 12 months (threshold 3, T350 manual): MNT-0298-027, MNT-0298-030, MNT-0298-032. [T350#6]
WELL-0374 (T200): 4 corrective pump jack repairs in the last 12 months (threshold 3, T200 manual): MNT-0374-022, MNT-0374-024, MNT-0374-027, MNT-0374-029. [T200#10]
WELL-0484 (T200): 3 corrective pump jack repairs in the last 12 months (threshold 3, T200 manual): MNT-0484-024, MNT-0484-029, MNT-0484-033. [T200#10]
WELL-0529 (T350): 3 corrective pump jack repairs in the last 12 months (threshold 3, T350 manual): MNT-0529-012, MNT-0529-015, MNT-0529-016. [T350#6]
WELL-0599 (T200): 3 corrective pump jack repairs in the last 12 months (threshold 3, T200 manual): MNT-0599-021, MNT-0599-026, MNT-0599-030. [T200#10]

**Visual: table** (Wells you discussed earlier)

| Well | Discussed when asked |
|---|---|
| WELL-0003 | Which well produced the most oil in 2026? |
| WELL-0004 | Which well produced the most oil in 2026? |
| WELL-0005 | Which well produced the most oil in 2026? |
| WELL-0007 | Which well produced the most oil in 2026? |
| WELL-0009 | Which well produced the most oil in 2026? |
| WELL-0012 | Which well produced the most oil in 2026? |
| WELL-0013 | Which well produced the most oil in 2026? |
| WELL-0014 | Which well produced the most oil in 2026? |
| WELL-0017 | Which well produced the most oil in 2026? |
| WELL-0021 | Which well produced the most oil in 2026? |
| WELL-0024 | Which well produced the most oil in 2026? |
| WELL-0025 | Which well produced the most oil in 2026? |
| WELL-0028 | Which well produced the most oil in 2026? |
| WELL-0029 | Which well produced the most oil in 2026? |
| WELL-0034 | Which well produced the most oil in 2026? |
| WELL-0038 | Which well produced the most oil in 2026? |
| WELL-0041 | Which well produced the most oil in 2026? |
| WELL-0045 | Which well produced the most oil in 2026? |
| WELL-0049 | Which well produced the most oil in 2026? |
| WELL-0054 | Which well produced the most oil in 2026? |
| WELL-0055 | Which well produced the most oil in 2026? |
| WELL-0056 | Which well produced the most oil in 2026? |
| WELL-0059 | Which well produced the most oil in 2026? |
| WELL-0063 | Which well produced the most oil in 2026? |
| WELL-0065 | Which well produced the most oil in 2026? |
| WELL-0073 | Which well produced the most oil in 2026? |
| WELL-0075 | Which well produced the most oil in 2026? |
| WELL-0079 | Which well produced the most oil in 2026? |
| WELL-0081 | Which well produced the most oil in 2026? |
| WELL-0088 | Which well produced the most oil in 2026? |
| WELL-0090 | Which well produced the most oil in 2026? |
| WELL-0095 | Which well produced the most oil in 2026? |
| WELL-0098 | Which well produced the most oil in 2026? |
| WELL-0099 | Which well produced the most oil in 2026? |
| WELL-0103 | Which well produced the most oil in 2026? |
| WELL-0107 | Which well produced the most oil in 2026? |
| WELL-0108 | Which well produced the most oil in 2026? |
| WELL-0109 | Which well produced the most oil in 2026? |
| WELL-0111 | Which well produced the most oil in 2026? |
| WELL-0114 | Which well produced the most oil in 2026? |

_144 more rows not shown_

**Visual: table** (Documents matching 'operator notes sound behavior last month')

| Ref | Document | Section | Passage |
|---|---|---|---|
| MNT-0001-029#notes-and-recommendations | Maintenance report MNT-0001-029 | Notes and recommendations |  … on this well instead of patching sections; two failures in a [month] show the line is in poor condition.
- Add a visual check of …  |
| MNT-0001-029#root-cause | Maintenance report MNT-0001-029 | Root cause |  … This is the
second flowline failure in a [month] on this well: a pinhole leak was repaired on 10 May 2026
(MNT-0001-028 …  |
| operations-sop-rev2#operator-notes | Operations SOP | Operator notes | Field operators record what they see on their rounds as [operator] [notes]: the records with
`note_type` = `[operator]_note` in the well's [notes] …  |
| MNT-0206-015#root-cause | Maintenance report MNT-0206-015 | Root cause | Cable crushed against the tubing during the [last] installation.
This is corrective repair number 3 on this well's esp pump in the [last] …  |
| MNT-0352-027#root-cause | Maintenance report MNT-0352-027 | Root cause | Cable crushed against the tubing during the [last] installation.
This is corrective repair number 3 on this well's esp pump in the [last] …  |

**Visual: table** (Root-cause analysis candidates (pump jack))

| Well | Type | Corrective repairs | Threshold | Rule source |
|---|---|---|---|---|
| WELL-0069 | T200 | 3 | 3 | T200 manual |
| WELL-0108 | T350 | 3 | 3 | T350 manual |
| WELL-0121 | T200 | 3 | 3 | T200 manual |
| WELL-0135 | T200 | 3 | 3 | T200 manual |
| WELL-0138 | T350 | 3 | 3 | T350 manual |
| WELL-0159 | T350 | 3 | 3 | T350 manual |
| WELL-0170 | T200 | 3 | 3 | T200 manual |
| WELL-0182 | T200 | 4 | 3 | T200 manual |
| WELL-0298 | T350 | 3 | 3 | T350 manual |
| WELL-0374 | T200 | 4 | 3 | T200 manual |
| WELL-0484 | T200 | 3 | 3 | T200 manual |
| WELL-0529 | T350 | 3 | 3 | T350 manual |
| WELL-0599 | T200 | 3 | 3 | T200 manual |

**Evidence:** WELL-0003, WELL-0004, WELL-0005, WELL-0007, WELL-0009, WELL-0012, WELL-0013, WELL-0014, WELL-0017, WELL-0021, WELL-0024, WELL-0025, WELL-0028, WELL-0029, WELL-0034, WELL-0038, WELL-0041, WELL-0045, WELL-0049, WELL-0054, WELL-0055, WELL-0056, WELL-0059, WELL-0063, WELL-0065, WELL-0073, WELL-0075, WELL-0079, WELL-0081, WELL-0088 …

_tools: recall_discussed, well_context, search_documents, rca_candidates · answer: verified facts · 237.2s_
_Showing the verified facts directly: the model rate limit was nearly used up, so the wording step was skipped._

### Q7b — Robert Hayes: Which three would you send a crew to first this week, and why?

To determine which three wells to prioritize, I first need to identify which wells currently have high downtime or are not producing, as well as any recent operator notes regarding their behavior.

I will start by checking the current status and recent notes for the top RCA candidates.

**Visual: table** (Root-cause analysis candidates (pump jack))

| Well | Type | Corrective repairs | Threshold | Rule source |
|---|---|---|---|---|
| WELL-0069 | T200 | 3 | 3 | T200 manual |
| WELL-0108 | T350 | 3 | 3 | T350 manual |
| WELL-0121 | T200 | 3 | 3 | T200 manual |
| WELL-0135 | T200 | 3 | 3 | T200 manual |
| WELL-0138 | T350 | 3 | 3 | T350 manual |
| WELL-0159 | T350 | 3 | 3 | T350 manual |
| WELL-0170 | T200 | 3 | 3 | T200 manual |
| WELL-0182 | T200 | 4 | 3 | T200 manual |
| WELL-0298 | T350 | 3 | 3 | T350 manual |
| WELL-0374 | T200 | 4 | 3 | T200 manual |
| WELL-0484 | T200 | 3 | 3 | T200 manual |
| WELL-0529 | T350 | 3 | 3 | T350 manual |
| WELL-0599 | T200 | 3 | 3 | T200 manual |

**Evidence:** MNT-0069-032, MNT-0069-034, MNT-0069-039, MNT-0108-024, MNT-0108-026, MNT-0108-028, MNT-0121-031, MNT-0121-034, MNT-0121-035, MNT-0135-031, MNT-0135-033, MNT-0135-034, MNT-0138-031, MNT-0138-032, MNT-0138-034, MNT-0159-025, MNT-0159-029, MNT-0159-031, MNT-0170-026, MNT-0170-031, MNT-0170-032, MNT-0182-021, MNT-0182-023, MNT-0182-027, MNT-0182-029, MNT-0298-027, MNT-0298-030, MNT-0298-032, MNT-0374-022, MNT-0374-024 …

_tools: rca_candidates · answer: model · 65.5s_

### Q8a — Nathan Pierce: WELL-0333's recalled pump was swapped out yesterday. The work order isn't in the system yet. Please count it as replaced from now on.

I have added a shared note for WELL-0333 stating that the recalled pump was swapped out yesterday (2027-01-14) and that the work order is pending in the system [SN-0001].

**Evidence:** WELL-0333, SN-0001

_tools: add_shared_note · answer: model · 68.1s_

### Q8b — Nathan Pierce: Also, just for me: whenever you list wells, sort them by area and then by well ID, and show costs in thousands of dollars.

Understood. I will sort all future well lists by area and then by well ID, and I will display all costs in thousands of dollars.

**Visual: table** (Wells you discussed earlier)

| Well | Discussed when asked |
|---|---|
| WELL-0010 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |
| WELL-0026 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |
| WELL-0032 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |
| WELL-0033 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |
| WELL-0046 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |
| WELL-0053 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |
| WELL-0069 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |
| WELL-0093 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |
| WELL-0097 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |
| WELL-0105 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |
| WELL-0133 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |
| WELL-0134 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |
| WELL-0160 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |
| WELL-0167 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |
| WELL-0169 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |
| WELL-0175 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |
| WELL-0197 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |
| WELL-0199 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |
| WELL-0203 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |
| WELL-0213 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |
| WELL-0219 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |
| WELL-0249 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |
| WELL-0251 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |
| WELL-0263 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |
| WELL-0281 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |
| WELL-0309 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |
| WELL-0316 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |
| WELL-0330 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |
| WELL-0332 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |
| WELL-0373 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |
| WELL-0377 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |
| WELL-0397 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |
| WELL-0404 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |
| WELL-0408 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |
| WELL-0418 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |
| WELL-0429 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |
| WELL-0442 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |
| WELL-0452 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |
| WELL-0471 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |
| WELL-0490 | Across the whole field, not just my area, for which wells do the latest inspection and the operator notes disagree about whether the well is producing oil? For each one, what is its real status right  |

_560 more rows not shown_

**Evidence:** WELL-0010, WELL-0026, WELL-0032, WELL-0033, WELL-0046, WELL-0053, WELL-0069, WELL-0093, WELL-0097, WELL-0105, WELL-0133, WELL-0134, WELL-0160, WELL-0167, WELL-0169, WELL-0175, WELL-0197, WELL-0199, WELL-0203, WELL-0213, WELL-0219, WELL-0249, WELL-0251, WELL-0263, WELL-0281, WELL-0309, WELL-0316, WELL-0330, WELL-0332, WELL-0373 …

_tools: recall_discussed · answer: model · 85.8s_

### Q8c — Robert Hayes: Which recalled pumps are still in the ground right now?

In your earlier conversation (17 Oct 2026) you asked "Which three would you send a crew to first this week, and why?" which covered: WELL-0069, WELL-0108, WELL-0121, WELL-0135, WELL-0138, WELL-0159, WELL-0170, WELL-0182, WELL-0298, WELL-0374, WELL-0484, WELL-0529, WELL-0599.
2 other earlier discussion(s) also match; the most recent one is used.
Maintenance report MNT-0302-031 §what-happened What happened: Field staff reported that the [pump] in this well was on the Highline [Pump] Co. [recall] list (notice of 1 Dec 2026). The operator …  [MNT-0302-031#what-happened]
Maintenance report MNT-0345-039 §what-happened What happened: Field staff reported that the [pump] in this well was on the Highline [Pump] Co. [recall] list (notice of 1 Dec 2026). The operator …  [MNT-0345-039#what-happened]
Maintenance report MNT-0398-025 §what-happened What happened: Field staff reported that the [pump] in this well was on the Highline [Pump] Co. [recall] list (notice of 1 Dec 2026). The operator …  [MNT-0398-025#what-happened]
Maintenance report MNT-0427-025 §what-happened What happened: Field staff reported that the [pump] in this well was on the Highline [Pump] Co. [recall] list (notice of 1 Dec 2026). The operator …  [MNT-0427-025#what-happened]
Maintenance report MNT-0302-031 §root-cause Root cause: Supplier [recall] of the [pump] lot for plunger cracking; the [pump] had not failed in service. [MNT-0302-031#root-cause]
WELL-0302 is producing oil. At the latest inspection INS-0302-0217 the wellhead was 24.3 °C warmer than the air (36.2 °C vs 11.9 °C), at or above the T350 limit of 20.0 °C. [T350#3]
Latest inspection INS-0302-0217 on 14 Jan 2027 by drone, by Caleb Whitaker.
The recorded status in the system is 'active'. [WELL-0302]

**Visual: table** (Wells you discussed earlier)

| Well | Discussed when asked |
|---|---|
| WELL-0069 | Which three would you send a crew to first this week, and why? |
| WELL-0108 | Which three would you send a crew to first this week, and why? |
| WELL-0121 | Which three would you send a crew to first this week, and why? |
| WELL-0135 | Which three would you send a crew to first this week, and why? |
| WELL-0138 | Which three would you send a crew to first this week, and why? |
| WELL-0159 | Which three would you send a crew to first this week, and why? |
| WELL-0170 | Which three would you send a crew to first this week, and why? |
| WELL-0182 | Which three would you send a crew to first this week, and why? |
| WELL-0298 | Which three would you send a crew to first this week, and why? |
| WELL-0374 | Which three would you send a crew to first this week, and why? |
| WELL-0484 | Which three would you send a crew to first this week, and why? |
| WELL-0529 | Which three would you send a crew to first this week, and why? |
| WELL-0599 | Which three would you send a crew to first this week, and why? |

**Visual: table** (Documents matching 'pump recall')

| Ref | Document | Section | Passage |
|---|---|---|---|
| MNT-0302-031#what-happened | Maintenance report MNT-0302-031 | What happened | Field staff reported that the [pump] in this well was on the Highline [Pump] Co. [recall] list (notice of 1 Dec 2026). The operator …  |
| MNT-0345-039#what-happened | Maintenance report MNT-0345-039 | What happened | Field staff reported that the [pump] in this well was on the Highline [Pump] Co. [recall] list (notice of 1 Dec 2026). The operator …  |
| MNT-0398-025#what-happened | Maintenance report MNT-0398-025 | What happened | Field staff reported that the [pump] in this well was on the Highline [Pump] Co. [recall] list (notice of 1 Dec 2026). The operator …  |
| MNT-0427-025#what-happened | Maintenance report MNT-0427-025 | What happened | Field staff reported that the [pump] in this well was on the Highline [Pump] Co. [recall] list (notice of 1 Dec 2026). The operator …  |
| MNT-0302-031#root-cause | Maintenance report MNT-0302-031 | Root cause | Supplier [recall] of the [pump] lot for plunger cracking; the [pump] had not failed in service. |

**Visual: status_card** (Status of WELL-0302)
**Evidence:** WELL-0069, WELL-0108, WELL-0121, WELL-0135, WELL-0138, WELL-0159, WELL-0170, WELL-0182, WELL-0298, WELL-0374, WELL-0484, WELL-0529, WELL-0599, MNT-0302-031#what-happened, MNT-0345-039#what-happened, MNT-0398-025#what-happened, MNT-0427-025#what-happened, MNT-0302-031#root-cause, WELL-0302, INS-0302-0217, T350#3

_tools: recall_discussed, search_documents, well_status · answer: verified facts · 68.1s_
_Showing the verified facts directly: the model rate limit was nearly used up, so the wording step was skipped._

### Q8d — Olivia Grant: Nathan told me the recalled pump on WELL-0577 was swapped as well. Take it off the recall list.

I have verified that WELL-0577 is currently producing according to the latest inspection [INS-0577-0211].

*   The well is confirmed to be producing oil, with a wellhead temperature 30.0 °C above ambient [INS-0577-0211].
*   Your statement regarding the pump swap has been recorded as a shared note [SN-0002].

**Evidence:** WELL-0577, INS-0577-0211, T200#9.3, CTX-0577-001, CTX-0577-002, SN-0002

_tools: check_claim · answer: model · 61.2s_

### Q8e — Nathan Pierce: Show me the recalled pumps that are still in the ground in my area, and what it cost to install each one.

I cannot identify any recalled pumps currently in the ground in your area based on the available records.

* Regarding the pump for **WELL-0333** mentioned in your previous discussions, your own note [SN-0001] states it was swapped out on 2027-01-14.

**Visual: table** (Wells you discussed earlier)

| Well | Discussed when asked |
|---|---|
| WELL-0333 | WELL-0333's recalled pump was swapped out yesterday. The work order isn't in the system yet. Please count it as replaced from now on. |

**Visual: table** (Notes and planned work for WELL-0333)

| Note | Type | Author | Valid from | Valid to | Text |
|---|---|---|---|---|---|
| SN-0001 | info | Nathan Pierce | 2027-01-14 |  | Recalled pump was swapped out on 2027-01-14. Work order not yet in system. |

**Evidence:** WELL-0333, SN-0001, INS-0333-0219

_tools: recall_discussed, well_context · answer: model · 64.0s_

### Q9a — Robert Hayes: How many recalled pumps are still in the ground, and in which areas?

13 well(s) in the whole field need a root-cause analysis on the pump jack: WELL-0069, WELL-0108, WELL-0121, WELL-0135, WELL-0138, WELL-0159, WELL-0170, WELL-0182, WELL-0298, WELL-0374, WELL-0484, WELL-0529, WELL-0599.
WELL-0069 (T200): 3 corrective pump jack repairs in the last 12 months (threshold 3, T200 manual): MNT-0069-032, MNT-0069-034, MNT-0069-039. [T200#10]
WELL-0108 (T350): 3 corrective pump jack repairs in the last 12 months (threshold 3, T350 manual): MNT-0108-024, MNT-0108-026, MNT-0108-028. [T350#6]
WELL-0121 (T200): 3 corrective pump jack repairs in the last 12 months (threshold 3, T200 manual): MNT-0121-031, MNT-0121-034, MNT-0121-035. [T200#10]
WELL-0135 (T200): 3 corrective pump jack repairs in the last 12 months (threshold 3, T200 manual): MNT-0135-031, MNT-0135-033, MNT-0135-034. [T200#10]
WELL-0138 (T350): 3 corrective pump jack repairs in the last 12 months (threshold 3, T350 manual): MNT-0138-031, MNT-0138-032, MNT-0138-034. [T350#6]
WELL-0159 (T350): 3 corrective pump jack repairs in the last 12 months (threshold 3, T350 manual): MNT-0159-025, MNT-0159-029, MNT-0159-031. [T350#6]
WELL-0170 (T200): 3 corrective pump jack repairs in the last 12 months (threshold 3, T200 manual): MNT-0170-026, MNT-0170-031, MNT-0170-032. [T200#10]
WELL-0182 (T200): 4 corrective pump jack repairs in the last 12 months (threshold 3, T200 manual): MNT-0182-021, MNT-0182-023, MNT-0182-027, MNT-0182-029. [T200#10]
WELL-0298 (T350): 3 corrective pump jack repairs in the last 12 months (threshold 3, T350 manual): MNT-0298-027, MNT-0298-030, MNT-0298-032. [T350#6]
WELL-0374 (T200): 4 corrective pump jack repairs in the last 12 months (threshold 3, T200 manual): MNT-0374-022, MNT-0374-024, MNT-0374-027, MNT-0374-029. [T200#10]
WELL-0484 (T200): 3 corrective pump jack repairs in the last 12 months (threshold 3, T200 manual): MNT-0484-024, MNT-0484-029, MNT-0484-033. [T200#10]
WELL-0529 (T350): 3 corrective pump jack repairs in the last 12 months (threshold 3, T350 manual): MNT-0529-012, MNT-0529-015, MNT-0529-016. [T350#6]
WELL-0599 (T200): 3 corrective pump jack repairs in the last 12 months (threshold 3, T200 manual): MNT-0599-021, MNT-0599-026, MNT-0599-030. [T200#10]

**Visual: table** (Root-cause analysis candidates (pump jack))

| Well | Type | Corrective repairs | Threshold | Rule source |
|---|---|---|---|---|
| WELL-0069 | T200 | 3 | 3 | T200 manual |
| WELL-0108 | T350 | 3 | 3 | T350 manual |
| WELL-0121 | T200 | 3 | 3 | T200 manual |
| WELL-0135 | T200 | 3 | 3 | T200 manual |
| WELL-0138 | T350 | 3 | 3 | T350 manual |
| WELL-0159 | T350 | 3 | 3 | T350 manual |
| WELL-0170 | T200 | 3 | 3 | T200 manual |
| WELL-0182 | T200 | 4 | 3 | T200 manual |
| WELL-0298 | T350 | 3 | 3 | T350 manual |
| WELL-0374 | T200 | 4 | 3 | T200 manual |
| WELL-0484 | T200 | 3 | 3 | T200 manual |
| WELL-0529 | T350 | 3 | 3 | T350 manual |
| WELL-0599 | T200 | 3 | 3 | T200 manual |

**Evidence:** MNT-0069-032, MNT-0069-034, MNT-0069-039, MNT-0108-024, MNT-0108-026, MNT-0108-028, MNT-0121-031, MNT-0121-034, MNT-0121-035, MNT-0135-031, MNT-0135-033, MNT-0135-034, MNT-0138-031, MNT-0138-032, MNT-0138-034, MNT-0159-025, MNT-0159-029, MNT-0159-031, MNT-0170-026, MNT-0170-031, MNT-0170-032, MNT-0182-021, MNT-0182-023, MNT-0182-027, MNT-0182-029, MNT-0298-027, MNT-0298-030, MNT-0298-032, MNT-0374-022, MNT-0374-024 …

_tools: rca_candidates · answer: verified facts · 3.2s_
_Showing the verified facts directly: the model rate limit was nearly used up, so the wording step was skipped._

### Q9b — Robert Hayes: Different topic. Who leads Northwest Production, and how many wells does that team run?

I cannot determine who leads Northwest Production or how many wells that team manages from the available records.

* Search results for the leadership of Northwest Production returned maintenance reports for wells in the Northwest area, but did not contain information regarding personnel or team oversight.

**Visual: table** (Documents matching 'Who leads Northwest Production?')

| Ref | Document | Section | Passage |
|---|---|---|---|
| MNT-0301-018#maintenance-report-mnt-0301-018 | Maintenance report MNT-0301-018 | Maintenance Report — MNT-0301-018 | **Asset:** WELL-0301 (NW-12 Well 301, T500, [Northwest] Block 12)
**Equipment:** flowline
**Work started:** 22 Mar 2025 08:00 · **Finished:** 14 Apr 2025 …  |
| MNT-0302-008#maintenance-report-mnt-0302-008 | Maintenance report MNT-0302-008 | Maintenance Report — MNT-0302-008 | **Asset:** WELL-0302 (NW-12 Well 302, T350, [Northwest] Block 12)
**Equipment:** flowline
**Work started:** 01 Mar 2024 08:00 · **Finished:** 02 Mar 2024 …  |
| MNT-0302-013#maintenance-report-mnt-0302-013 | Maintenance report MNT-0302-013 | Maintenance Report — MNT-0302-013 | **Asset:** WELL-0302 (NW-12 Well 302, T350, [Northwest] Block 12)
**Equipment:** flowline
**Work started:** 09 Aug 2024 08:00 · **Finished:** 17 Sep 2024 …  |
| MNT-0302-031#maintenance-report-mnt-0302-031 | Maintenance report MNT-0302-031 | Maintenance Report — MNT-0302-031 | **Asset:** WELL-0302 (NW-12 Well 302, T350, [Northwest] Block 12)
**Equipment:** downhole pump
**Work started:** 22 Dec 2026 07:00 · **Finished:** 23 Dec …  |
| MNT-0303-002#maintenance-report-mnt-0303-002 | Maintenance report MNT-0303-002 | Maintenance Report — MNT-0303-002 | **Asset:** WELL-0303 (NW-12 Well 303, T500, [Northwest] Block 12)
**Equipment:** flowline
**Work started:** 22 Jan 2023 08:00 · **Finished:** 08 Feb 2023 …  |

**Evidence:** MNT-0301-018#maintenance-report-mnt-0301-018, MNT-0302-008#maintenance-report-mnt-0302-008, MNT-0302-013#maintenance-report-mnt-0302-013, MNT-0302-031#maintenance-report-mnt-0302-031, MNT-0303-002#maintenance-report-mnt-0303-002

_tools: search_documents · answer: model · 63.7s_

### Q9c — Robert Hayes: What does our operations SOP say about cold weather? Name one well that missed the check in December.

Operations SOP §operations-sop Operations SOP:  … operating,
> safety or regulatory guidance.

Document ID: [SOP]-OPS · Revision 2 · Effective 1 Oct 2026 · Owner: Field [Operations] with Health, Safety & Environment (TEAM-HSE) [operations-sop-rev2#operations-sop]
Regulatory Compliance SOP §regulatory-compliance-sop Regulatory Compliance SOP: > Fictional [SOP] for the FlytBase Asset Copilot hackathon. Not legal or regulatory guidance.

Document ID: [SOP]-RC · Revision 2 · Owner: Health, Safety & Environment (TEAM …  [regulatory-compliance-sop#regulatory-compliance-sop]
T200 Rod-Lift Oil Well — Operating & Maintenance Manual §8 8. Spill response on the pad: Any crude release must be handled under the company Spill Response [SOP]
(`sops/spill-response-[sop].md`). In short: stop the source, contain, estimate …  [T200#8]
Spill Response SOP §spill-response-sop Spill Response SOP: > Fictional [SOP] for the FlytBase Asset Copilot hackathon. Simplified and modelled on
> common US onshore practice. It is not a copy of any rule …  [spill-response-sop#spill-response-sop]
T200 Rod-Lift Oil Well — Operating & Maintenance Manual §7 7. Common failure modes: | Symptom | Likely cause | First action |
|---|---|---|
| Unit running, wellhead [cold] | Rod parted or pump stuck | Shut in, call rod/pump crew |
| Unit stopped, motor hot …  [T200#7]
0 of 600 well(s) in the whole field went more than 14 days between inspections in 1 Dec 2026 to 31 Dec 2026, or have a latest inspection older than 14 days (RC-01 allows 14 days).

**Visual: table** (Documents matching 'cold weather operations SOP')

| Ref | Document | Section | Passage |
|---|---|---|---|
| operations-sop-rev2#operations-sop | Operations SOP | Operations SOP |  … operating,
> safety or regulatory guidance.

Document ID: [SOP]-OPS · Revision 2 · Effective 1 Oct 2026 · Owner: Field [Operations] with Health, Safety & Environment (TEAM-HSE) |
| regulatory-compliance-sop#regulatory-compliance-sop | Regulatory Compliance SOP | Regulatory Compliance SOP | > Fictional [SOP] for the FlytBase Asset Copilot hackathon. Not legal or regulatory guidance.

Document ID: [SOP]-RC · Revision 2 · Owner: Health, Safety & Environment (TEAM …  |
| T200#8 | T200 Rod-Lift Oil Well — Operating & Maintenance Manual | 8. Spill response on the pad | Any crude release must be handled under the company Spill Response [SOP]
(`sops/spill-response-[sop].md`). In short: stop the source, contain, estimate …  |
| spill-response-sop#spill-response-sop | Spill Response SOP | Spill Response SOP | > Fictional [SOP] for the FlytBase Asset Copilot hackathon. Simplified and modelled on
> common US onshore practice. It is not a copy of any rule …  |
| T200#7 | T200 Rod-Lift Oil Well — Operating & Maintenance Manual | 7. Common failure modes | / Symptom / Likely cause / First action /
/---/---/---/
/ Unit running, wellhead [cold] / Rod parted or pump stuck / Shut in, call rod/pump crew /
/ Unit stopped, motor hot …  |

**Visual: table** (Inspection gaps in the whole field, 1 Dec 2026 to 31 Dec 2026)

| Well | Gaps over limit | Longest gap | Last inspection | Days since last inspection |
|---|---|---|---|---|


**Evidence:** operations-sop-rev2#operations-sop, regulatory-compliance-sop#regulatory-compliance-sop, T200#8, spill-response-sop#spill-response-sop, T200#7, RC-01

_tools: search_documents, inspection_gaps · answer: verified facts · 63.2s_
_Showing the verified facts directly: the model rate limit was nearly used up, so the wording step was skipped._

### Q9d — Robert Hayes: An operator reported a gas smell at WELL-0332 on 3 Dec. What was the H2S reading?

Operations SOP §ops-1-gas-odor-response OPS-1 Gas odor response:  … note saying the crew smelled [gas], noticed a rotten-egg [smell] or a [gas] odor, or that an [H2S]
monitor alarmed at a well …  [operations-sop-rev2#ops-1-gas-odor-response]
Maintenance report MNT-0332-003 §maintenance-report-mnt-0332-003 Maintenance Report — MNT-0332-003: **Asset:** [WELL-0332] (NW-12 Well 332, T200, Northwest Block 12)
**Equipment:** flowline
**Work started:** 10 Mar 2023 08:00 · **Finished:** 10 Mar 2023 …  [MNT-0332-003#maintenance-report-mnt-0332-003]
Maintenance report MNT-0332-033 §maintenance-report-mnt-0332-033 Maintenance Report — MNT-0332-033: **Asset:** [WELL-0332] (NW-12 Well 332, T200, Northwest Block 12)
**Equipment:** flowline
**Work started:** 20 Nov 2026 08:00 · **Finished:** 20 Nov 2026 …  [MNT-0332-033#maintenance-report-mnt-0332-033]
Maintenance report MNT-0332-025 §maintenance-report-mnt-0332-025 Maintenance Report — MNT-0332-025: **Asset:** [WELL-0332] (NW-12 Well 332, T200, Northwest Block 12)
**Equipment:** wellhead
**Work started:** 16 Nov 2025 08:00 · **Finished:** 18 Nov 2025 …  [MNT-0332-025#maintenance-report-mnt-0332-025]
Maintenance report MNT-0332-024 §maintenance-report-mnt-0332-024 Maintenance Report — MNT-0332-024: **Asset:** [WELL-0332] (NW-12 Well 332, T200, Northwest Block 12)
**Equipment:** pump jack
**Work started:** 17 Oct 2025 08:00 · **Finished:** 28 Oct …  [MNT-0332-024#maintenance-report-mnt-0332-024]

**Visual: table** (Documents matching 'WELL-0332 gas smell 3 Dec H2S reading')

| Ref | Document | Section | Passage |
|---|---|---|---|
| operations-sop-rev2#ops-1-gas-odor-response | Operations SOP | OPS-1 Gas odor response |  … note saying the crew smelled [gas], noticed a rotten-egg [smell] or a [gas] odor, or that an [H2S]
monitor alarmed at a well …  |
| MNT-0332-003#maintenance-report-mnt-0332-003 | Maintenance report MNT-0332-003 | Maintenance Report — MNT-0332-003 | **Asset:** [WELL-0332] (NW-12 Well 332, T200, Northwest Block 12)
**Equipment:** flowline
**Work started:** 10 Mar 2023 08:00 · **Finished:** 10 Mar 2023 …  |
| MNT-0332-033#maintenance-report-mnt-0332-033 | Maintenance report MNT-0332-033 | Maintenance Report — MNT-0332-033 | **Asset:** [WELL-0332] (NW-12 Well 332, T200, Northwest Block 12)
**Equipment:** flowline
**Work started:** 20 Nov 2026 08:00 · **Finished:** 20 Nov 2026 …  |
| MNT-0332-025#maintenance-report-mnt-0332-025 | Maintenance report MNT-0332-025 | Maintenance Report — MNT-0332-025 | **Asset:** [WELL-0332] (NW-12 Well 332, T200, Northwest Block 12)
**Equipment:** wellhead
**Work started:** 16 Nov 2025 08:00 · **Finished:** 18 Nov 2025 …  |
| MNT-0332-024#maintenance-report-mnt-0332-024 | Maintenance report MNT-0332-024 | Maintenance Report — MNT-0332-024 | **Asset:** [WELL-0332] (NW-12 Well 332, T200, Northwest Block 12)
**Equipment:** pump jack
**Work started:** 17 Oct 2025 08:00 · **Finished:** 28 Oct …  |

**Evidence:** operations-sop-rev2#ops-1-gas-odor-response, MNT-0332-003#maintenance-report-mnt-0332-003, MNT-0332-033#maintenance-report-mnt-0332-033, MNT-0332-025#maintenance-report-mnt-0332-025, MNT-0332-024#maintenance-report-mnt-0332-024

_tools: search_documents · answer: verified facts · 2.5s_
_Showing the verified facts directly: the model rate limit was nearly used up, so the wording step was skipped._

### Q9e — Robert Hayes: Back to the pumps from my first question: which of those wells are not producing oil right now, and when was each one last repaired?

In your earlier conversation (17 Oct 2026) you asked "Which recalled pumps are still in the ground right now?" which covered: WELL-0302.
0 well(s) in WELL-0302 are not producing oil right now (latest inspection).
WELL-0302 is producing oil. At the latest inspection INS-0302-0217 the wellhead was 24.3 °C warmer than the air (36.2 °C vs 11.9 °C), at or above the T350 limit of 20.0 °C. [T350#3]
Latest inspection INS-0302-0217 on 14 Jan 2027 by drone, by Caleb Whitaker.
The recorded status in the system is 'active'. [WELL-0302]

**Visual: table** (Wells you discussed earlier)

| Well | Discussed when asked |
|---|---|
| WELL-0302 | Which recalled pumps are still in the ground right now? |

**Visual: table** (Wells not producing in WELL-0302)

| Well | Wellhead above air | Recorded status | Reason |
|---|---|---|---|


**Visual: status_card** (Status of WELL-0302)
**Evidence:** WELL-0302, INS-0302-0217, T350#3

_tools: recall_discussed, wells_not_producing, well_status · answer: verified facts · 66.4s_
_Showing the verified facts directly: the model rate limit was nearly used up, so the wording step was skipped._

### Q9f — Robert Hayes: Of all the wells we've talked about today, which one would you deal with first, and why?

In your earlier conversation (17 Oct 2026) you asked "Which recalled pumps are still in the ground right now?" which covered: WELL-0302.

**Visual: table** (Wells you discussed earlier)

| Well | Discussed when asked |
|---|---|
| WELL-0302 | Which recalled pumps are still in the ground right now? |

**Evidence:** WELL-0302

_tools: recall_discussed · answer: verified facts · 62.2s_
_The model's wording contained values not found in the records (11.9, 20.0, 24.3, 36.2, INS-0302-0217); showing the verified facts instead._

### Q10 — Michael Turner: When a well stays shut in longer than the repair itself, what are we usually waiting on: parts, crews, contractors or weather? Break it down by area for jobs started in 2026, with the typical number of extra days, and tell me if any area stands out.

Downtime by area for the whole field, 1 Jan 2026 to 31 Dec 2026: Northwest Block 12 2989 days; Southeast Block 32 2765 days; Northeast Block 8 1379 days; Southwest Block 23 1372 days; Northeast Block 7 1197 days; Southwest Block 24 1162 days; Southeast Block 31 728 days.
Northwest Block 12: 2989 downtime days across 150 well(s) (116 with downtime), 19.9 days per well, in 1 Jan 2026 to 31 Dec 2026.
Southeast Block 32: 2765 downtime days across 150 well(s) (103 with downtime), 18.4 days per well, in 1 Jan 2026 to 31 Dec 2026.
Northeast Block 8: 1379 downtime days across 62 well(s) (49 with downtime), 22.2 days per well, in 1 Jan 2026 to 31 Dec 2026.
Southwest Block 23: 1372 downtime days across 63 well(s) (48 with downtime), 21.8 days per well, in 1 Jan 2026 to 31 Dec 2026.
Northeast Block 7: 1197 downtime days across 62 well(s) (44 with downtime), 19.3 days per well, in 1 Jan 2026 to 31 Dec 2026.
Southwest Block 24: 1162 downtime days across 63 well(s) (45 with downtime), 18.4 days per well, in 1 Jan 2026 to 31 Dec 2026.
Southeast Block 31: 728 downtime days across 50 well(s) (29 with downtime), 14.6 days per well, in 1 Jan 2026 to 31 Dec 2026.
Downtime counts each weekly inspection that found the well not producing oil as 7 days; missed inspections add none, and repair downtime_hours is not used.

**Visual: bar** (Downtime by area, 1 Jan 2026 to 31 Dec 2026)

| Area | Downtime days | Wells | Days per well |
|---|---|---|---|
| Northwest Block 12 | 2989 | 150 | 19.9 |
| Southeast Block 32 | 2765 | 150 | 18.4 |
| Northeast Block 8 | 1379 | 62 | 22.2 |
| Southwest Block 23 | 1372 | 63 | 21.8 |
| Northeast Block 7 | 1197 | 62 | 19.3 |
| Southwest Block 24 | 1162 | 63 | 18.4 |
| Southeast Block 31 | 728 | 50 | 14.6 |

_tools: downtime · answer: verified facts · 5.4s_
_Showing the verified facts directly: the model rate limit was nearly used up, so the wording step was skipped._

### Q11 — Olivia Grant: Which region of the field consistently runs hotter?

I do not have access to temperature data for the regions to determine which one runs hotter.

* The available tools provide spill heatmaps, but no regional temperature trends or datasets.

**Visual: heatmap** (Spills by area and month, 1 Jan 2027 to 15 Jan 2027)

| Area | Jan | Total |
|---|---|---|
| Northeast Block 7 | 2 | 2 |
| Northeast Block 8 | 3 | 3 |
| Northwest Block 12 | 7 | 7 |
| Southeast Block 31 | 1 | 1 |
| Southeast Block 32 | 4 | 4 |
| Southwest Block 23 | 4 | 4 |
| Southwest Block 24 | 3 | 3 |

**Evidence:** INS-0006-0214, INS-0010-0218, INS-0019-0219, INS-0045-0214, INS-0067-0216, INS-0097-0214, INS-0123-0109, INS-0165-0217, INS-0216-0219, INS-0262-0218, INS-0278-0201, INS-0284-0218, INS-0293-0172, INS-0310-0216, INS-0347-0133, INS-0356-0214, INS-0361-0218, INS-0399-0217, INS-0417-0219, INS-0448-0212, INS-0521-0175, INS-0534-0219, INS-0560-0215, INS-0595-0216

_tools: spill_heatmap · answer: model · 56.9s_
