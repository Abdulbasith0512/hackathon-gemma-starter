# 5-minute video outline (your own voice)

**0:00-0:30 The problem.** Operators have inspections, repairs, notes and manuals in different places. One question can take hours. This copilot answers in seconds, with the evidence.

**0:30-2:15 How it is built** (screen: the README diagram, then the Rules page)
- Data goes into SQLite with provenance; manuals, SOPs and repair reports are split into citable sections.
- Rules (production threshold per well type, spill classes, deadlines) are read from the documents, with the quoted passage.
- 22 deterministic tools do all the maths. Gemma 4 only chooses the tool and words the answer; a grounding check rejects any number it cannot find in the tool results.
- Two memories: shared (corrections, rules, notes; originals kept, who/why/when/scope) and private per user.

**2:15-4:45 One real use case, end to end** (screen: the UI; pick Michael Turner)
1. Ask the wells-not-producing question for an area, as a table. Open a citation chip to show the actual inspection and the manual section.
2. Say a reading is wrong. Show the preview (original value, proposed value, scope, who, why, effect, the inspector's conflicting note). Press **Confirm and save**.
3. Ask the first question again: the well is gone from the list and the answer says why.
4. Switch the user to someone else (Jessica Reed): she sees the corrected value, the correction badge and the conflict. Open the **Audit** page to show the original value kept.
5. Ask her "the three wells we discussed yesterday": the copilot says it has no such earlier conversation (private memory).

**4:45-5:00 What worked, what is next.** Tested on the sample answers and on a synthetic dataset with different IDs; next steps from the write-up.
