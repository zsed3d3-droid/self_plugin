"""Native adapter tests: fake clock, fake provider events, and private fake CLI."""
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from native_precheck import CONTINUE_TEXT, NativeRunner, OrcaCLI
from retry_state import CAPACITY_MESSAGE


UUID = "11111111-2222-4333-8444-555555555555"


class FakeClock:
    def __init__(self, now=100):
        self.now = now
        self.waited = 0
        self.callback = None

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds
        self.waited += seconds
        if self.callback:
            callback, self.callback = self.callback, None
            callback()


class FakeHost:
    def __init__(self, clock):
        self.clock = clock
        self.calls = []
        self.ready = True
        self.on_preflight = None
        self.responses = []
        self.on_send = None

    def preflight(self):
        if self.on_preflight:
            self.on_preflight()
        return self.ready, "terminal_scope_changed" if not self.ready else "best_effort_preflight_passed"

    def send(self, request_id=None):
        self.calls.append((self.clock.time(), request_id))
        if self.on_send:
            callback, self.on_send = self.on_send, None
            callback()
        if self.responses:
            response = self.responses.pop(0)
            if isinstance(response, BaseException):
                raise response
            return response
        return {"ok": True, "result": {"send": {"accepted": True,
                "prompt": {"requestId": UUID, "stages": ["input_accepted", "turn_started"]}}}}


class NativeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.rollout = self.base / "rollout.jsonl"
        self.rollout.touch()
        self.scope = {"thread_id": "test-thread", "terminal_handle": "terminal-test",
                      "terminal_incarnation": "process-test", "account_scope": "account-test", "model_id": "model-test",
                      "rollout_path": str(self.rollout), "workspace_path": str(self.base), "pty_id": "pty-test",
                      "account_id": "account-test", "pane_accounts_path": str(self.base / "panes.json"),
                      "native_state_dir": str(self.base / "state"), "delivery_enabled": True, "orca_cli": "unused"}
        (self.base / "panes.json").write_text(json.dumps({"panes": {"pty-test": {
            "accountId": "account-test", "homeRoute": "account-home"}}}))
        self.clock = FakeClock()
        self.host = FakeHost(self.clock)
        self.append({"type": "session_meta", "payload": {"id": "test-thread", "cwd": str(self.base)}})
        self.append({"type": "turn_context", "payload": {"model": "model-test"}})
        self.event("task_started")
        self.runner = self.make_runner()
        self.runner.initialize()

    def make_runner(self, host=None):
        return NativeRunner(self.scope, host or self.host, self.clock.time, self.clock.sleep)

    def append(self, record):
        with self.rollout.open("a") as stream:
            stream.write(json.dumps(record) + "\n")

    def event(self, kind, at=100, turn="turn-one", **extra):
        self.append({"type": "event_msg", "timestamp": datetime.fromtimestamp(at, timezone.utc).isoformat(),
                     "payload": {"type": kind, "turn_id": turn, **extra}})

    def capacity(self, at=100, turn="turn-one"):
        self.event("task_complete", at, turn, error={"codex_error_info": "server_overloaded", "message": CAPACITY_MESSAGE})

    def test_waits_only_remaining_time_since_provider_event(self):
        self.capacity(at=100)
        self.clock.now = 130
        self.assertEqual(self.runner.tick(), "attempted")
        self.assertEqual(self.clock.waited, 30)
        self.assertEqual(self.host.calls, [(160, None)])

    def test_late_scheduler_tick_does_not_wait_another_minute(self):
        self.capacity(at=100)
        self.clock.now = 180
        self.runner.tick()
        self.assertEqual(self.clock.waited, 0)
        self.assertEqual(self.host.calls, [(180, None)])

    def test_initialize_discards_historical_failure(self):
        self.capacity()
        self.runner.initialize()
        self.clock.now = 500
        self.assertEqual(self.runner.tick(), "no_event")
        self.assertEqual(self.host.calls, [])

    def test_current_active_check_only_never_calls_cli_send(self):
        self.assertEqual(self.runner.tick(check_only=True), "active")
        self.assertEqual(self.host.calls, [])

    def test_quoted_user_text_does_not_arm_retry(self):
        self.append({"type": "response_item", "payload": {"type": "message", "role": "user", "content": CAPACITY_MESSAGE}})
        self.runner.tick()
        self.assertEqual(self.host.calls, [])
        self.assertIsNone(self.runner.policy.pending)

    def test_new_user_or_stop_or_active_during_wait_cancels(self):
        for kind in ["turn_aborted", "task_started", "item_completed"]:
            with self.subTest(kind=kind):
                self.runner.initialize()
                self.event("task_started")
                self.capacity()
                self.clock.now = 130
                self.clock.callback = lambda: self.event(kind, at=131, turn="turn-two", item={"type": "UserMessage"})
                self.assertEqual(self.runner.tick(), "cancelled")
                self.assertEqual(self.host.calls, [])

    def test_user_message_after_host_checks_cancels_before_send(self):
        self.capacity()
        self.clock.now = 160
        self.host.on_preflight = lambda: self.event("item_completed", at=160, turn="turn-two", item={"type": "UserMessage"})
        self.assertEqual(self.runner.tick(), "cancelled")
        self.assertEqual(self.host.calls, [])

    def test_changed_terminal_incarnation_is_refused(self):
        self.capacity()
        self.clock.now = 160
        self.host.ready = False
        self.assertEqual(self.runner.tick(), "preflight_refused")
        self.assertEqual(self.host.calls, [])

    def test_model_change_is_refused(self):
        self.capacity()
        self.append({"type": "event_msg", "payload": {"type": "thread_settings_applied",
                     "thread_settings": {"model": "different-model"}}})
        self.assertEqual(self.runner.tick(), "scope_changed")
        self.assertEqual(self.host.calls, [])

    def test_known_ambiguous_receipt_reconciles_only_same_request(self):
        self.capacity()
        self.clock.now = 160
        self.host.responses = [{"ok": False, "error": {"code": "runtime_timeout", "data": {"orchestrationRequestId": UUID}}}]
        self.runner.tick()
        self.assertEqual(self.host.calls, [(160, None), (160, UUID)])
        self.runner.tick()
        self.assertEqual(len(self.host.calls), 2)

    def test_user_message_or_stop_during_first_send_prevents_receipt_replay(self):
        for kind in ["item_completed", "turn_aborted"]:
            with self.subTest(kind=kind):
                self.runner.initialize()
                self.event("task_started")
                self.capacity()
                self.clock.now = 160
                self.host.calls.clear()
                self.host.responses = [{"ok": False, "error": {"code": "runtime_timeout",
                                       "data": {"orchestrationRequestId": UUID}}}]
                self.host.on_send = lambda: self.event(kind, at=160, turn="turn-two", item={"type": "UserMessage"})
                self.runner.tick()
                self.assertEqual(self.host.calls, [(160, None)])

    def test_nonempty_current_composer_line_is_refused_even_if_idle(self):
        for draft in ["user is typing", "Explain this codebase", "이미 입력한 초안"]:
            host = OrcaCLI(self.scope)
            responses = iter([
                {"ok": True, "result": {"terminal": {"handle": self.scope["terminal_handle"],
                    "incarnationId": self.scope["terminal_incarnation"], "ptyId": self.scope["pty_id"],
                    "worktreePath": self.scope["workspace_path"], "agentIdentity": "codex", "connected": True, "writable": True}}},
                {"ok": True, "result": {"wait": {"satisfied": True}}},
                {"ok": True, "result": {"terminal": {"source": "screen", "tail": ["■ " + CAPACITY_MESSAGE, "› " + draft]}}},
            ])
            host.call = lambda *args: next(responses)
            self.assertEqual(host.preflight(), (False, "composer_not_empty"))

    def composer_host(self, screen, version="1.4.230"):
        host = OrcaCLI(self.scope)
        responses = iter([
            {"ok": True, "result": {"terminal": {"handle": self.scope["terminal_handle"],
                "incarnationId": self.scope["terminal_incarnation"], "ptyId": self.scope["pty_id"],
                "worktreePath": self.scope["workspace_path"], "agentIdentity": "codex", "connected": True, "writable": True}}},
            {"ok": True, "result": {"wait": {"satisfied": True}}},
            {"ok": True, "result": {"terminal": {"source": "screen", **screen}}},
            {"ok": True, "result": {"runtime": {"appVersion": version}}},
        ])
        host.call = lambda *args: next(responses)
        return host

    def test_native_stock_placeholder_without_draft_is_admitted_on_audited_live_version(self):
        for placeholder in ['Ask Codex to do anything', 'Ask a follow-up question', 'Try "refactor this file"']:
            host = self.composer_host({"tail": ["■ " + CAPACITY_MESSAGE, "› " + placeholder]})
            self.assertEqual(host.preflight(), (True, "best_effort_preflight_passed"))

    def test_actual_draft_equal_to_placeholder_or_multiline_is_always_refused(self):
        for draft in ['Ask Codex to do anything', 'Try "refactor this file"', 'first line\nsecond line']:
            host = self.composer_host({"draft": draft, "tail": ["■ " + CAPACITY_MESSAGE, "›"]})
            self.assertEqual(host.preflight(), (False, "composer_draft_present"))

    def test_host_upgrade_does_not_keep_saved_placeholder_assumption(self):
        for version in ["1.4.231", None]:
            host = self.composer_host({"tail": ["■ " + CAPACITY_MESSAGE, "› Ask Codex to do anything"]}, version)
            self.assertEqual(host.preflight(), (False, "composer_metadata_version_unverified"))

    def test_silence_without_request_id_never_resends(self):
        self.capacity()
        self.clock.now = 160
        self.host.responses = [{"ok": False, "error": {"code": "cli_response_unknown"}}]
        self.runner.tick()
        self.clock.now = 240
        self.make_runner().tick()
        self.assertEqual(len(self.host.calls), 1)

    def test_accepted_unproven_receipt_is_observed_once_using_same_id(self):
        self.capacity()
        self.clock.now = 160
        unproven = {"ok": True, "result": {"send": {"accepted": True,
                    "prompt": {"requestId": UUID, "stages": ["input_accepted"]}}}}
        self.host.responses = [unproven, unproven]
        self.runner.tick()
        self.runner.tick()
        self.assertEqual(self.host.calls, [(160, None), (160, UUID)])

    def test_auth_quota_billing_do_not_schedule_native_delivery(self):
        for code in ["authentication_error", "insufficient_quota", "credit_balance_exhausted"]:
            self.runner.initialize()
            self.event("task_started")
            self.event("task_complete", error={"codex_error_info": code, "message": CAPACITY_MESSAGE})
            self.runner.tick()
            self.assertEqual(self.host.calls, [])

    def test_scope_mismatch_in_rollout_metadata_is_refused(self):
        self.capacity()
        self.append({"type": "session_meta", "payload": {"id": "another-thread", "cwd": str(self.base)}})
        self.clock.now = 160
        self.assertEqual(self.runner.tick(), "scope_changed")
        self.assertEqual(self.host.calls, [])

    def test_crash_after_persisted_attempt_never_creates_second_send(self):
        self.capacity()
        self.clock.now = 160
        self.host.responses = [SystemExit(99)]
        with self.assertRaises(SystemExit):
            self.runner.tick()
        self.make_runner().tick()
        self.assertEqual(len(self.host.calls), 1)

    def test_consecutive_fresh_failure_and_duplicate_tick_are_distinct(self):
        self.capacity()
        self.clock.now = 160
        self.runner.tick()
        self.runner.tick()
        self.assertEqual(len(self.host.calls), 1)
        self.event("task_started", 170, "turn-two")
        self.capacity(180, "turn-two")
        self.clock.now = 190
        self.runner.tick()
        self.assertEqual(self.host.calls, [(160, None), (240, None)])

    def test_native_cli_entry_always_exits_nonzero_and_lock_prevents_overlap(self):
        scope_file = self.base / "scope.json"
        scope_file.write_text(json.dumps(self.scope))
        before = self.runner.path.read_bytes()
        lock = (self.runner.directory / "run.lock").open("a")
        self.addCleanup(lock.close)
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = subprocess.run([sys.executable, str(Path(__file__).with_name("native_precheck.py")),
                                 "--scope", str(scope_file), "--check-only"], capture_output=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.runner.path.read_bytes(), before)

    def test_private_fake_cli_delivery_integration(self):
        fake = self.base / "fake-orca"
        calls = self.base / "fake-cli-calls.jsonl"
        fixture = {"scope": self.scope, "calls": str(calls), "uuid": UUID}
        fake.write_text("#!" + sys.executable + "\n" + "import json,sys\n" + "F=" + repr(fixture) + "\n" + '''
a=sys.argv[1:];s=F["scope"]
with open(F["calls"],"a") as f:f.write(json.dumps(a)+"\\n")
if a[:2]==["terminal","show"]:
 r={"terminal":{"handle":s["terminal_handle"],"incarnationId":s["terminal_incarnation"],"ptyId":s["pty_id"],"worktreePath":s["workspace_path"],"agentIdentity":"codex","connected":True,"writable":True}}
elif a[:2]==["terminal","wait"]:r={"wait":{"satisfied":True}}
elif a[:2]==["terminal","read"]:r={"terminal":{"source":"screen","tail":["■ Selected model is at capacity. Please try a different model.","›"]}}
elif a[:2]==["terminal","send"]:r={"send":{"accepted":True,"prompt":{"requestId":F["uuid"],"stages":["input_accepted","turn_started"]}}}
else:raise SystemExit(2)
print(json.dumps({"ok":True,"result":r}))
''')
        fake.chmod(0o700)
        self.scope["orca_cli"] = str(fake)
        self.capacity()
        self.clock.now = 160
        runner = self.make_runner(OrcaCLI(self.scope))
        self.assertEqual(runner.tick(), "attempted")
        log = [json.loads(line) for line in calls.read_text().splitlines()]
        sends = [args for args in log if args[:2] == ["terminal", "send"]]
        self.assertEqual(len(sends), 1)
        self.assertEqual(sends[0][sends[0].index("--text") + 1], CONTINUE_TEXT)
        self.assertEqual(runner.data["delivery"]["outcome"], "turn_started")


if __name__ == "__main__":
    unittest.main()
