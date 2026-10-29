"""Policy tests use fictional scope values and an explicit clock; no live RPCs."""
import copy
import unittest

from retry_state import CAPACITY_MESSAGE, RetryState, classify


THREAD = "test-thread"


def record(kind, *, error=None, turn="turn-one", timestamp="2030-01-01T00:00:00Z"):
    payload = {"type": kind, "turn_id": turn}
    if error is not None:
        payload["error"] = error
    return {"type": "event_msg", "timestamp": timestamp, "payload": payload}


def capacity(*, turn="turn-one", timestamp="2030-01-01T00:00:00Z", offset=1):
    return classify(record("task_complete", turn=turn, timestamp=timestamp,
                           error={"message": CAPACITY_MESSAGE, "codex_error_info": "server_overloaded"}), THREAD, offset)


class AdmissionTests(unittest.TestCase):
    def test_exact_provider_error_is_admitted_with_stable_identity(self):
        first = capacity()
        self.assertEqual(first["kind"], "capacity")
        self.assertEqual(first, capacity())
        self.assertNotEqual(first["event_id"], capacity(offset=2)["event_id"])
        self.assertNotEqual(first["event_id"], capacity(turn="turn-two")["event_id"])

    def test_raw_user_quote_is_never_capacity_evidence(self):
        quoted = {"type": "response_item", "payload": {"type": "message", "role": "user",
                  "content": [{"type": "input_text", "text": "■ " + CAPACITY_MESSAGE}]}}
        self.assertIsNone(classify(quoted, THREAD))

    def test_assistant_tool_terminal_and_nonmessage_item_quotes_are_rejected(self):
        samples = [
            {"type": "response_item", "payload": {"type": "message", "role": "assistant", "content": CAPACITY_MESSAGE}},
            {"type": "response_item", "payload": {"type": "function_call_output", "output": CAPACITY_MESSAGE}},
            {"type": "terminal", "payload": {"text": "■ " + CAPACITY_MESSAGE}},
            {"type": "event_msg", "payload": {"type": "item_completed", "item": {"type": "CommandExecution", "text": CAPACITY_MESSAGE}}},
            {"type": "event_msg", "payload": {"type": "warning", "message": CAPACITY_MESSAGE}},
        ]
        for sample in samples:
            with self.subTest(sample=sample):
                self.assertIsNone(classify(sample, THREAD))

    def test_authoritative_user_message_is_an_override_with_its_turn_identity(self):
        sample = {"type": "event_msg", "payload": {"type": "item_completed", "turn_id": "turn-two",
                  "item": {"type": "UserMessage", "text": CAPACITY_MESSAGE}}}
        event = classify(sample, THREAD)
        self.assertEqual(event["kind"], "new_message")
        self.assertEqual(event["turn_id"], "turn-two")

    def test_quota_auth_billing_and_generic_errors_are_not_retried(self):
        for code in ["insufficient_quota", "usage_limit_exceeded", "authentication_error", "unauthorized",
                     "credit_balance_exhausted", "project_spend_limit_exceeded", "rate_limit_exceeded",
                     "server_error", "server_is_overloaded"]:
            with self.subTest(code=code):
                self.assertEqual(classify(record("task_complete", error={"message": CAPACITY_MESSAGE,
                                 "codex_error_info": code}), THREAD)["kind"], "other_error")

    def test_exact_display_copy_without_structured_code_is_not_evidence(self):
        for error in [CAPACITY_MESSAGE, {"message": CAPACITY_MESSAGE},
                      {"message": CAPACITY_MESSAGE, "code": "server_overloaded"},
                      {"message": "A different failure", "codex_error_info": "server_overloaded"}]:
            with self.subTest(error=error):
                self.assertEqual(classify(record("task_complete", error=error), THREAD)["kind"], "other_error")

    def test_non_dictionary_payload_is_ignored(self):
        self.assertIsNone(classify({"type": "event_msg", "payload": [CAPACITY_MESSAGE]}, THREAD))
        for sample in [None, [], "display copy", 1]:
            self.assertIsNone(classify(sample, THREAD))

    def test_supported_boundary_events_are_classified(self):
        for name, expected in [("task_started", "active"), ("turn_aborted", "stop"),
                               ("task_cancelled", "stop"), ("task_complete", "complete")]:
            with self.subTest(name=name):
                self.assertEqual(classify(record(name), THREAD)["kind"], expected)


class PolicyTests(unittest.TestCase):
    def fresh(self):
        return RetryState(THREAD, "terminal-test", "incarnation-test", "account-test", "model-test")

    def activate(self, state, turn="turn-one", now=100):
        state.observe(classify(record("task_started", turn=turn), THREAD), now)

    def waiting(self):
        state = self.fresh()
        self.activate(state)
        state.observe(capacity(), 100)
        return state

    def proof(self, state, **changes):
        value = {"thread_id": THREAD, "terminal_handle": "terminal-test", "terminal_incarnation": "incarnation-test",
                 "account_scope": "account-test", "model_id": "model-test", "event_id": state.last_event_id, "transport_ready": True,
                 "atomic_sendable_guard": True, "active_work": False, "user_stopped": False, "new_message": False}
        value.update(changes)
        return value

    def test_fake_clock_waits_a_full_sixty_seconds(self):
        state = self.waiting()
        self.assertEqual(state.pending["due_at"], 160)
        self.assertIsNone(state.due(159.999, self.proof(state)))
        self.assertEqual(state.status, "waiting")
        self.assertEqual(state.retries, 0)
        intent = state.due(160, self.proof(state))
        self.assertEqual(intent["event_id"], state.last_event_id)
        self.assertEqual(state.retries, 1)

    def test_due_creates_one_intent_even_after_ambiguous_delivery(self):
        state = self.waiting()
        intent = state.due(160, self.proof(state))
        self.assertEqual(intent["request_id"], "capacity-retry-" + intent["event_id"])
        self.assertEqual(state.status, "submitting")
        # A caller losing the RPC reply must reconcile this same request ID.
        self.assertIsNone(state.due(220, self.proof(state)))
        self.assertEqual(state.retries, 1)

    def test_all_scope_fields_and_latest_error_are_required(self):
        for field in ["thread_id", "terminal_handle", "terminal_incarnation", "account_scope", "model_id", "event_id"]:
            for missing in [False, True]:
                with self.subTest(field=field, missing=missing):
                    state = self.waiting()
                    proof = self.proof(state)
                    if missing:
                        proof.pop(field)
                    else:
                        proof[field] = "different-scope"
                    self.assertIsNone(state.due(160, proof))
                    self.assertEqual(state.reason, "scope_or_latest_event_changed")
                    self.assertIsNone(state.pending)
                    self.assertEqual(state.retries, 0)

    def test_host_busy_stop_pause_or_new_message_override_due_retry(self):
        for flag in ["active_work", "user_stopped", "new_message"]:
            with self.subTest(flag=flag):
                state = self.waiting()
                self.assertIsNone(state.due(160, self.proof(state, **{flag: True})))
                self.assertIsNone(state.pending)
                self.assertEqual(state.reason, "host_activity_or_user_override")

    def test_delivery_without_atomic_sendable_guard_is_blocked(self):
        for field in ["transport_ready", "atomic_sendable_guard"]:
            with self.subTest(field=field):
                state = self.waiting()
                self.assertIsNone(state.due(160, self.proof(state, **{field: False})))
                self.assertEqual(state.status, "blocked")
                self.assertEqual(state.reason, "same_session_delivery_transport_unavailable")
                self.assertEqual(state.retries, 0)
                # A later positive proof cannot silently rearm a blocked event.
                self.assertIsNone(state.due(161, self.proof(state)))

    def test_missing_activity_evidence_cannot_authorize_delivery(self):
        for field in ["active_work", "user_stopped", "new_message"]:
            state = self.waiting()
            proof = self.proof(state)
            proof.pop(field)
            self.assertIsNone(state.due(160, proof))
            self.assertEqual(state.reason, "host_activity_unverified")

    def test_empty_scope_or_different_delay_is_rejected(self):
        with self.assertRaises(ValueError):
            RetryState(THREAD, "terminal", "incarnation", "account", "")
        with self.assertRaises(ValueError):
            RetryState(THREAD, "terminal", "incarnation", "account", "model", delay_seconds=59)

    def test_late_foreign_turn_completion_does_not_cancel_current_work(self):
        state = self.fresh()
        self.activate(state)
        for kind in ["complete", "other_error"]:
            state.observe({"kind": kind, "thread_id": THREAD, "turn_id": "older-turn"}, 120)
            self.assertEqual(state.active_turn, "turn-one")

    def test_active_work_cancels_waiting_retry(self):
        state = self.waiting()
        self.activate(state, "turn-two", now=120)
        self.assertEqual(state.active_turn, "turn-two")
        self.assertIsNone(state.pending)
        self.assertIsNone(state.due(160, self.proof(state)))

    def test_user_stop_or_pause_cancels_wait_and_late_error(self):
        for name in ["turn_aborted", "task_cancelled"]:
            with self.subTest(name=name):
                state = self.waiting()
                state.observe(classify(record(name), THREAD), 120)
                state.observe(capacity(offset=12), 121)
                self.assertIsNone(state.pending)
                self.assertEqual(state.reason, "user_stop_or_pause")

    def test_new_user_message_cancels_pending_retry(self):
        state = self.waiting()
        state.observe({"kind": "new_message", "thread_id": THREAD}, 120)
        self.assertIsNone(state.pending)
        self.assertEqual(state.reason, "new_user_message")

    def test_new_message_prevents_old_active_turn_late_capacity_rearming(self):
        state = self.fresh()
        self.activate(state)
        state.observe({"kind": "new_message", "thread_id": THREAD}, 120)
        state.observe(capacity(), 121)
        self.assertIsNone(state.pending)
        self.assertIsNone(state.active_turn)

    def test_matching_authoritative_user_message_preserves_current_active_turn(self):
        state = self.fresh()
        self.activate(state)
        state.observe({"kind": "new_message", "thread_id": THREAD, "turn_id": "turn-one"}, 101)
        self.assertEqual(state.active_turn, "turn-one")
        state.observe(capacity(), 102)
        self.assertEqual(state.status, "waiting")
        self.assertEqual(state.pending["due_at"], 162)

    def test_real_started_raw_user_authoritative_user_sequence_can_recover_capacity(self):
        state = self.fresh()
        samples = [
            record("task_started"),
            {"type": "response_item", "payload": {"type": "message", "role": "user", "content": CAPACITY_MESSAGE}},
            {"type": "event_msg", "payload": {"type": "item_completed", "turn_id": "turn-one",
             "item": {"type": "UserMessage", "text": CAPACITY_MESSAGE}}},
        ]
        for sample in samples:
            state.observe(classify(sample, THREAD), 100)
        self.assertEqual(state.active_turn, "turn-one")
        state.observe(capacity(), 101)
        self.assertEqual(state.status, "waiting")
        self.assertEqual(state.pending["due_at"], 161)

    def test_startup_history_fold_retains_active_turn_and_never_replays_old_capacity(self):
        state = self.fresh()
        self.activate(state, "previous-turn", now=10)
        stale = capacity(turn="previous-turn", offset=1)
        state.observe(stale, 11)
        self.activate(state, "turn-one", now=20)
        state.cancel("startup_baseline")
        self.assertEqual(state.active_turn, "turn-one")
        self.assertIsNone(state.pending)
        state.observe(stale, 100)
        self.assertIsNone(state.pending)
        state.observe(capacity(turn="turn-one", offset=2), 101)
        self.assertEqual(state.pending["due_at"], 161)

    def test_user_message_for_different_turn_invalidates_old_active_turn(self):
        state = self.fresh()
        self.activate(state)
        state.observe({"kind": "new_message", "thread_id": THREAD, "turn_id": "turn-two"}, 101)
        state.observe(capacity(), 102)
        self.assertIsNone(state.active_turn)
        self.assertIsNone(state.pending)

    def test_complete_and_noncapacity_failure_cancel_retry(self):
        for name, error in [("task_complete", None), ("task_complete", {"message": "billing", "codex_error_info": "insufficient_quota"})]:
            with self.subTest(error=error):
                state = self.waiting()
                state.observe(classify(record(name, error=error), THREAD), 120)
                self.assertIsNone(state.pending)
                self.assertIsNone(state.active_turn)
                self.assertIsNone(state.due(160, self.proof(state)))

    def test_foreign_thread_cannot_activate_or_cancel_or_schedule(self):
        state = self.waiting()
        before = copy.deepcopy(state.snapshot())
        for kind in ["active", "new_message", "stop", "complete", "other_error", "capacity"]:
            state.observe({"kind": kind, "thread_id": "different-thread", "turn_id": "turn-two", "event_id": "foreign-event"}, 120)
        self.assertEqual(state.snapshot(), before)

    def test_capacity_without_observed_active_turn_is_not_replayed(self):
        state = self.fresh()
        state.observe(capacity(), 100)
        self.assertIsNone(state.pending)
        self.assertEqual(state.status, "observing")

    def test_capacity_for_old_turn_does_not_replace_current_turn(self):
        state = self.fresh()
        self.activate(state, "turn-two")
        state.observe(capacity(turn="turn-one"), 101)
        self.assertEqual(state.active_turn, "turn-two")
        self.assertIsNone(state.pending)

    def test_duplicate_error_does_not_extend_deadline_or_create_retry(self):
        state = self.waiting()
        state.observe(capacity(), 145)
        self.assertEqual(state.pending["due_at"], 160)
        state.due(160, self.proof(state))
        state.observe(capacity(), 200)
        self.assertEqual(state.status, "submitting")
        self.assertIsNone(state.due(220, self.proof(state)))
        self.assertEqual(state.retries, 1)

    def test_consecutive_fresh_capacity_events_each_wait_sixty_seconds(self):
        state = self.waiting()
        first = state.due(160, self.proof(state))
        self.activate(state, "turn-two", now=161)
        state.observe(capacity(turn="turn-two", timestamp="2030-01-01T00:01:01Z", offset=2), 162)
        self.assertNotEqual(state.last_event_id, first["event_id"])
        self.assertEqual(state.pending["due_at"], 222)
        self.assertIsNone(state.due(221.999, self.proof(state)))
        second = state.due(222, self.proof(state))
        self.assertNotEqual(first["request_id"], second["request_id"])
        self.assertEqual(state.retries, 2)

    def test_snapshot_has_no_raw_error_content_or_dedup_history(self):
        value = self.waiting().snapshot()
        self.assertNotIn("seen", value)
        self.assertNotIn(CAPACITY_MESSAGE, str(value))


if __name__ == "__main__":
    unittest.main()
