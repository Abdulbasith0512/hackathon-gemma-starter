"""Part A2/B scenarios (corrections, rules, notes, claims, private memory) on the official sample.

Tools are run directly (no model): this is the deterministic core that the agent calls. Expected
values come from the Example Scenarios and live only in these tests.
"""

import unittest

from ahc import actions, tools
from ahc.agent import Agent
from ahc.analyst import Analyst
from ahc.tools import Ctx
from tests.test_ahc_golden import AS_OF, GoldenCase

MICHAEL, JESSICA, TYLER, LAURA, JAKE = "U-201", "U-202", "U-204", None, "U-102"


class MemoryCase(GoldenCase):
    def ctx(self, user, conv="CV-test", auto=False, message=""):
        return Ctx(self.fresh(), self.store, user, conv, auto, message)

    def run_tool(self, user, name, args, **kw):
        return tools.run_tool(self.ctx(user, **kw), name, args)

    def agent(self):
        return Agent(self.fresh(), self.store, llm=object())

    def user_id(self, name):
        return next(u["user_id"] for u in self.fresh().users.values() if u["name"] == name)

    @staticmethod
    def text(res):
        return " ".join(f["text"] for f in res["facts"])

    @staticmethod
    def cited(res):
        return {c["id"] for c in res["citations"]}


class CorrectionFlowTests(MemoryCase):
    ARGS = {"asset_id": "WELL-0164", "date": "2026-10-15", "field": "wellhead_temp_c", "new_value": 41.0,
            "reason": "The handheld thermal gun was faulty; the field crew re-measured the wellhead at 41.0 C"}

    def test_q12_correction_is_previewed_first_and_saves_nothing_until_confirmed(self):
        res = self.run_tool(MICHAEL, "propose_correction", self.ARGS)
        pv = res["pending"]["preview"]
        rows = {r[0]: r[1] for r in pv["rows"]}
        self.assertEqual((rows["Original value (dataset)"], rows["Proposed value"]), ("24.0", "41.0"))
        self.assertIn("INS-0164-0205", rows["Record"])
        self.assertIn("Michael Turner", rows["Corrected by"])
        self.assertIn("faulty", rows["Reason"])
        self.assertIn("This inspection only", rows["Scope"])
        self.assertTrue(any("not producing" in t and "producing" in t and "21.1" in t for t in pv["impact"]))
        self.assertTrue(any("Pump jack not moving." in t and "Tyler Hughes" in t for t in pv["warnings"]))
        self.assertEqual(self.store.all_corrections(), [])                       # nothing saved yet
        self.assertEqual(self.fresh().get_inspection("INS-0164-0205")["wellhead_temp_c"], 24.0)

    def test_q12_confirm_saves_keeps_the_original_and_flags_the_conflicting_note(self):
        res = self.run_tool(MICHAEL, "propose_correction", self.ARGS)
        out = actions.decide(self.fresh(), self.store, self.agent(), MICHAEL, res["pending"]["action_id"], True)
        (cor,) = self.store.all_corrections()
        self.assertEqual((cor["original_value"], cor["new_value"], cor["author_user_id"], cor["status"], cor["scope_type"]), (24.0, 41.0, MICHAEL, "active", "record"))
        self.assertIn("faulty", cor["reason"])
        self.assertTrue(cor["created_at"])
        self.assertIn(cor["correction_id"], {c["id"] for c in out["citations"]})
        self.assertIn("producing", out["answer"])
        self.assertTrue(any(f["type"] == "needs_confirmation" and "Pump jack not moving." in f["text"] for f in out["flags"]))
        self.assertTrue(any(f["type"] == "conflict" for f in out["flags"]))

    def test_q12_then_q2_again_lists_three_wells_and_says_why_0164_is_gone(self):
        res = self.run_tool(MICHAEL, "propose_correction", self.ARGS)
        actions.decide(self.fresh(), self.store, self.agent(), MICHAEL, res["pending"]["action_id"], True)
        r = self.run_tool(MICHAEL, "wells_not_producing", {"scope": "Northeast Block 8"})
        self.assertEqual({row[0] for row in r["visuals"]["table"]["rows"]}, {"WELL-0170", "WELL-0172", "WELL-0175"})
        t = self.text(r)
        self.assertIn("WELL-0164 is no longer listed", t)
        self.assertIn("corrected from 24.0 °C to 41.0 °C", t)

    def test_cancel_saves_nothing(self):
        res = self.run_tool(MICHAEL, "propose_correction", self.ARGS)
        out = actions.decide(self.fresh(), self.store, self.agent(), MICHAEL, res["pending"]["action_id"], False)
        self.assertEqual(out, {"cancelled": True})
        self.assertEqual(self.store.all_corrections(), [])
        with self.assertRaises(ValueError):  # already decided
            actions.decide(self.fresh(), self.store, self.agent(), MICHAEL, res["pending"]["action_id"], True)

    def test_only_the_proposer_can_confirm(self):
        res = self.run_tool(MICHAEL, "propose_correction", self.ARGS)
        with self.assertRaises(PermissionError):
            actions.decide(self.fresh(), self.store, self.agent(), JESSICA, res["pending"]["action_id"], True)
        self.assertEqual(self.store.all_corrections(), [])

    def test_q15_other_users_see_the_correction_and_the_disagreeing_note(self):
        res = self.run_tool(MICHAEL, "propose_correction", self.ARGS)
        actions.decide(self.fresh(), self.store, self.agent(), MICHAEL, res["pending"]["action_id"], True)
        r = self.run_tool(JESSICA, "well_status", {"asset_id": "WELL-0164"})   # a different user, a different chat
        self.assertIs(r["data"]["producing"], True)
        self.assertEqual(r["data"]["delta_c"], 21.1)
        t = self.text(r)
        self.assertIn("Michael Turner", t)
        self.assertIn("Pump jack not moving.", t)
        self.assertTrue({"conflict", "corrected"} <= {f["type"] for f in r["flags"]})

    def test_q13_volume_correction_makes_the_spill_reportable_with_the_follow_on_duties(self):
        args = {"asset_id": "WELL-0151", "date": "2026-09-24", "field": "spill_est_volume_bbl", "new_value": 5.4, "reason": "The field crew measured 5.4 bbl"}
        res = self.run_tool(MICHAEL, "propose_correction", args)
        self.assertTrue(any("reportable" in t for t in res["pending"]["preview"]["impact"]))
        out = actions.decide(self.fresh(), self.store, self.agent(), MICHAEL, res["pending"]["action_id"], True)
        text = out["answer"]
        self.assertIn("4.5", text)           # the AI estimate is kept for reference
        self.assertIn("5.4", text)
        self.assertIn("SR-01", text)
        self.assertIn("none is recorded", text)
        self.assertIn("23 Nov 2026", text)   # SR-03 verification due within 60 days
        self.assertIn("moderate", text)      # the old report classification no longer holds
        self.assertIn("no longer holds", text)
        self.assertIn("6.4 hours", text)     # the existing SR-02 breach from the report
        self.assertEqual(self.fresh().get_inspection("INS-0151-0201")["orig"]["spill_est_volume_bbl"], 4.5)

    def test_q15_laura_asks_which_spills_needed_a_regulator_report(self):
        args = {"asset_id": "WELL-0151", "date": "2026-09-24", "field": "spill_est_volume_bbl", "new_value": 5.4, "reason": "measured"}
        res = self.run_tool(MICHAEL, "propose_correction", args)
        actions.decide(self.fresh(), self.store, self.agent(), MICHAEL, res["pending"]["action_id"], True)
        r = self.run_tool(self.user_id("Laura Simmons"), "compliance_audit", {"scope": "Northeast Block 8", "period": "last 90 days", "protocol": "SR-01"})
        self.assertEqual(r["data"]["reportable"], 1)
        self.assertEqual([b["asset_id"] for b in r["data"]["breaches"]], ["WELL-0151"])
        t = self.text(r)
        self.assertIn("none is recorded", t)
        self.assertIn("1 of 4 spill(s)", t)  # no other spill reached 5 bbl


class RuleScopeTests(MemoryCase):
    def test_q14_type_rule_is_confirmed_then_applies_to_t350_only(self):
        before = self.run_tool(MICHAEL, "rca_candidates", {"scope": "Northeast Block 7", "equipment_kind": "pump_jack"})
        self.assertEqual(before["data"]["wells"], ["WELL-0108", "WELL-0121", "WELL-0138"])
        msg = "Note for all T350 wells: our team now wants a pump jack root-cause analysis after 2 repairs, not 3."
        res = self.run_tool(MICHAEL, "propose_rule", {"scope_type": "well_type", "scope_value": "T350", "key": "rca_corrective_count", "value": 2, "equipment_kind": "pump_jack", "reason": "team policy"}, message=msg)
        rows = {r[0]: r[1] for r in res["pending"]["preview"]["rows"]}
        self.assertIn("All T350 wells", rows["Scope"])
        self.assertIn("3", rows["Manual value"])
        self.assertEqual(self.store.all_scoped_rules(), [])                       # not saved yet
        actions.decide(self.fresh(), self.store, self.agent(), MICHAEL, res["pending"]["action_id"], True)
        (rule,) = self.store.all_scoped_rules()
        self.assertEqual((rule["scope_type"], rule["scope_value"], rule["value"], rule["author_user_id"], rule["source_text"]), ("well_type", "T350", 2.0, MICHAEL, msg))
        after = self.run_tool(MICHAEL, "rca_candidates", {"scope": "Northeast Block 7", "equipment_kind": "pump_jack"}, conv="CV-new-chat")
        self.assertEqual(after["data"]["wells"], ["WELL-0108", "WELL-0120", "WELL-0121", "WELL-0138"])
        self.assertNotIn("WELL-0102", after["data"]["wells"])
        t = self.text(after)
        self.assertIn("Michael Turner", t)
        self.assertIn("not the manual", t)
        self.assertIn(rule["rule_id"], self.cited(after))

    def test_unknown_type_or_key_is_refused(self):
        self.assertIn("error", self.run_tool(MICHAEL, "propose_rule", {"scope_type": "well_type", "scope_value": "T999", "key": "rca_corrective_count", "value": 2}))
        self.assertIn("error", self.run_tool(MICHAEL, "propose_rule", {"scope_type": "well_type", "scope_value": "T350", "key": "something_else", "value": 2}))


class SharedKnowledgeAndPrivacyTests(MemoryCase):
    def test_q16_a_shared_note_reaches_other_users(self):
        res = self.run_tool(JAKE, "add_shared_note", {"asset_id": "WELL-0007", "kind": "planned_downtime", "valid_from": "2026-10-17", "duration_days": 10,
                                                      "text": "WELL-0007 will be shut in from 17 Oct for a 10-day planned workover."})
        self.assertIn("SN-", res["facts"][0]["text"])
        r = self.run_tool(MICHAEL, "well_context", {"asset_id": "WELL-0007"})
        t = self.text(r)
        self.assertIn("Jake Morales", t)
        self.assertIn("17 Oct 2026", t)
        self.assertIn("27 Oct 2026", t)  # about 10 days
        self.assertIn("planned workover", t)

    def test_q11_q16_private_memory_is_recalled_for_its_owner_only(self):
        conv1 = self.store.new_conversation(MICHAEL, "Q6")
        mid = self.store.add_message(conv1, MICHAEL, "assistant", "answer")
        self.store.record_entities(MICHAEL, conv1, mid, [("well", "WELL-0121"), ("well", "WELL-0138"), ("well", "WELL-0107")], "Which 3 wells in Northeast Block 7 had the most downtime?")
        mine = self.run_tool(MICHAEL, "recall_discussed", {}, conv="CV-day-2")
        self.assertEqual(mine["data"]["wells"], ["WELL-0121", "WELL-0138", "WELL-0107"])
        costs = self.run_tool(MICHAEL, "repair_costs", {"wells": mine["data"]["wells"], "period": "this year"})
        self.assertEqual(costs["data"]["per_well"], {"WELL-0121": 25794, "WELL-0138": 46942, "WELL-0107": 5176})
        hers = self.run_tool(JESSICA, "recall_discussed", {}, conv="CV-jessica")
        self.assertIs(hers["data"]["found"], False)
        self.assertIn("no earlier conversation", self.text(hers))
        self.assertNotIn("WELL-0121", self.text(hers))

    def test_a_conversation_is_only_readable_by_its_owner(self):
        conv = self.store.new_conversation(MICHAEL, "private")
        self.store.add_message(conv, MICHAEL, "user", "secret question")
        self.assertEqual(len(self.store.messages(conv, MICHAEL)), 1)
        self.assertEqual(self.store.messages(conv, JESSICA), [])
        self.assertEqual(self.store.conversations(JESSICA), [])
        with self.assertRaises(PermissionError):
            self.agent().respond(JESSICA, conv, "hello")

    def test_recall_can_pick_the_discussion_that_had_the_stated_number_of_wells(self):
        for topic, wells in (("Three wells", ["WELL-0121", "WELL-0138", "WELL-0107"]), ("One well", ["WELL-0164"])):
            conv = self.store.new_conversation(MICHAEL, topic)
            mid = self.store.add_message(conv, MICHAEL, "assistant", "x")
            self.store.record_entities(MICHAEL, conv, mid, [("well", w) for w in wells], topic)   # the one-well chat is the most recent
        picked = self.run_tool(MICHAEL, "recall_discussed", {"count": 3}, conv="CV-new")
        self.assertEqual(picked["data"]["wells"], ["WELL-0121", "WELL-0138", "WELL-0107"])
        none = self.run_tool(MICHAEL, "recall_discussed", {"count": 5}, conv="CV-new")
        self.assertIs(none["data"]["found"], False)
        self.assertIn("5 wells", self.text(none))

    def test_recall_ignores_the_current_conversation(self):
        conv = self.store.new_conversation(MICHAEL, "now")
        mid = self.store.add_message(conv, MICHAEL, "assistant", "x")
        self.store.record_entities(MICHAEL, conv, mid, [("well", "WELL-0001")], "topic")
        self.assertIs(self.run_tool(MICHAEL, "recall_discussed", {}, conv=conv)["data"]["found"], False)


class ClaimTests(MemoryCase):
    def claim(self, user, asset, state, text, since=None):
        return self.run_tool(user, "check_claim", {"asset_id": asset, "asserted_state": state, "claim_text": text, **({"since": since} if since else {})})

    def test_q17_conflicting_statements_are_both_kept_and_the_unsupported_one_is_unconfirmed(self):
        first = self.claim(MICHAEL, "WELL-0175", "shut_in", "WELL-0175 has been shut in for planned work since 14 Oct.", "2026-10-14")
        self.assertIs(first["data"]["verdict"]["matches"], True)
        second = self.claim(TYLER, "WELL-0175", "producing", "WELL-0175 is running fine.")
        self.assertIs(second["data"]["verdict"]["matches"], False)
        t = self.text(second)
        self.assertIn("0.4 °C", t)
        self.assertIn("Jessica Reed", t)                 # the 15 Oct inspector
        self.assertIn("Michael Turner", t)               # whose note matches the inspection
        self.assertIn("unconfirmed", t)
        self.assertIn("Both statements are kept", t)
        self.assertTrue({"unconfirmed", "conflict"} <= {f["type"] for f in second["flags"]})
        notes = self.store.shared_notes_for("WELL-0175")
        self.assertEqual([(n["author_user_id"], n["status"]) for n in notes], [(MICHAEL, "consistent_with_records"), (TYLER, "unconfirmed")])

    def test_q17_a_back_online_claim_is_checked_against_the_latest_inspection_and_the_expected_return(self):
        r = self.claim(JAKE, "WELL-0001", "producing", "WELL-0001 is back online since 14 Oct.", "2026-10-14")
        self.assertIs(r["data"]["verdict"]["matches"], False)
        t = self.text(r)
        self.assertIn("not producing", t)
        self.assertIn("CTX-0001-003", t)
        self.assertIn("20 Oct", t)                       # the note expects the return around 20 Oct
        self.assertIn("unconfirmed", t)

    def test_audit_trail_lists_every_shared_item(self):
        self.claim(MICHAEL, "WELL-0175", "shut_in", "shut in since 14 Oct")
        self.assertEqual(len(self.store.all_shared_notes()), 1)


class ExplanationTests(MemoryCase):
    def test_q18_disagreeing_notes_are_shown_and_the_detection_stands(self):
        r = self.run_tool(MICHAEL, "spill_evidence", {"asset_id": "WELL-0101", "date": "2026-08-20"})
        t = self.text(r)
        self.assertIn("INS-0101-0197", t)
        self.assertIn("CTX-0101-002", t)
        self.assertIn("Ryan Brooks", t)
        self.assertIn("CTX-0101-003", t)
        self.assertIn("Chris Dalton", t)
        self.assertIn("MNT-0101-029", t)
        self.assertIn("Neither note is a formal correction", t)
        self.assertIn("detection stands", t)
        self.assertIn("conflict", {f["type"] for f in r["flags"]})
        self.assertTrue({"INS-0101-0197", "CTX-0101-002", "CTX-0101-003", "MNT-0101-029"} <= self.cited(r))

    def test_q9_compliance_audit_for_well_0001(self):
        r = self.run_tool(MICHAEL, "compliance_audit", {"scope": "WELL-0001", "period": "last 12 months"})
        self.assertEqual(sorted(b["protocol"] for b in r["data"]["breaches"]), ["RC-04", "SR-01", "SR-02", "SR-03"])
        self.assertEqual(r["data"]["fines_open_usd"], 5000)
        t = self.text(r)
        for needle in ("41 hours", "24-hour limit", "REG-0001-001", "REG-0001-002", "USD 5,000", "10 Aug 2026", "REG-0001-003", "30 Jul 2026", "about 7 hours", "4-hour limit",
                       "RC-02 met", "7 Mar 2026", "root-cause analysis", "MNT-0001-028", "MNT-0001-029", "MNT-0001-032", "Action required", "CTX-0001-003", "maintenance system"):
            self.assertIn(needle, t, needle)
        self.assertEqual(len(r["data"]["pending"]), 2)

    def test_q10_spills_not_contained_within_the_sop_limit(self):
        r = self.run_tool(MICHAEL, "compliance_audit", {"scope": "Southwest Block 24", "period": "last 90 days", "protocol": "SR-02"})
        got = {(b["asset_id"], b["detail"].split(",")[0]) for b in r["data"]["breaches"]}
        self.assertEqual(got, {("WELL-0082", "contained after about 7.1 hours"), ("WELL-0100", "contained after about 8.1 hours")})
        self.assertTrue({"MNT-0082-028", "INS-0082-0198", "MNT-0100-034", "INS-0100-0196"} <= self.cited(r))


if __name__ == "__main__":
    unittest.main()
