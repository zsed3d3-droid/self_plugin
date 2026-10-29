"""Bounded Orca scheduled precheck; every invocation exits nonzero.

No daemon, login, credentials, model switch, or new session. Delivery uses the
installed public Orca CLI and fresh best-effort scope/activity checks.
"""
import argparse
from dataclasses import asdict
from datetime import datetime
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from retry_state import CAPACITY_MESSAGE, RetryState, classify


CONTINUE_TEXT = "이전 요청에서 중단된 작업을 같은 컨텍스트에서 계속 진행해 주세요."
DRAFT_METADATA_VERSION = "1.4.230"


def stock_placeholder(text):
    # Exact strings/pattern from this audited build's native composer parser.
    return text in ("Ask Codex to do anything", "Ask a follow-up question") or bool(re.fullmatch(r'Try\s+["“].+["”]', text))


def atomic_json(path, value):
    temp = path.with_suffix(".tmp")
    with temp.open("w") as stream:
        os.chmod(temp, 0o600)
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temp.replace(path)


def event_time(record):
    try:
        value = datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00"))
        return value.timestamp() if value.tzinfo else None
    except (KeyError, TypeError, ValueError, AttributeError):
        return None


def receipt(result):
    send = (result.get("result") or {}).get("send") or {}
    prompt = send.get("prompt") or {}
    request_id = prompt.get("requestId")
    error = result.get("error") or {}
    data = error.get("data") or {}
    if not request_id:
        request_id = data.get("orchestrationRequestId")
    safe_id = request_id if isinstance(request_id, str) and re.fullmatch(r"[0-9a-fA-F-]{36}", request_id) else None
    stages = prompt.get("stages") or []
    if "turn_started" in stages:
        outcome = "turn_started"
    elif send.get("accepted") is True:
        outcome = "accepted_unproven"
    elif safe_id and data.get("retrySafe") is not False:
        outcome = "reconcile_same_request"
    else:
        outcome = "unknown_do_not_resend"
    return {"outcome": outcome, "request_id": safe_id, "stages": stages,
            "error_code": error.get("code"), "retry_safe": data.get("retrySafe")}


class OrcaCLI:
    def __init__(self, scope):
        self.scope = scope
        self.command = scope["orca_cli"]

    def call(self, *args):
        try:
            result = subprocess.run([self.command, *args, "--json"], capture_output=True,
                                    text=True, timeout=15, cwd=self.scope["workspace_path"])
            return json.loads(result.stdout)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            return {"ok": False, "error": {"code": "cli_response_unknown"}}

    def preflight(self):
        s = self.scope
        shown = self.call("terminal", "show", "--terminal", s["terminal_handle"])
        terminal = (shown.get("result") or {}).get("terminal") or {}
        matches = (shown.get("ok") is True and terminal.get("handle") == s["terminal_handle"]
                   and terminal.get("incarnationId") == s["terminal_incarnation"]
                   and terminal.get("ptyId") == s["pty_id"]
                   and terminal.get("worktreePath") == s["workspace_path"]
                   and terminal.get("agentIdentity") == "codex"
                   and terminal.get("connected") is True and terminal.get("writable") is True)
        if not matches:
            return False, "terminal_scope_changed"
        try:
            selected = json.loads(Path(s["pane_accounts_path"]).read_text())["panes"][s["pty_id"]]
            if selected.get("accountId") != s["account_id"] or selected.get("homeRoute") != "account-home":
                return False, "account_scope_changed"
        except (OSError, ValueError, KeyError, TypeError):
            return False, "account_scope_unverified"
        waited = self.call("terminal", "wait", "--terminal", s["terminal_handle"],
                           "--for", "tui-idle", "--timeout-ms", "1")
        wait = (waited.get("result") or {}).get("wait") or {}
        if waited.get("ok") is not True or wait.get("satisfied") is not True:
            return False, "active_or_waiting_for_user"
        # Inspect without logging terminal content. The structured error remains
        # the only trigger; this verifies its notice is still the current UI.
        screen_result = self.call("terminal", "read", "--terminal", s["terminal_handle"],
                                  "--screen", "--limit", "80")
        screen = (screen_result.get("result") or {}).get("terminal") or {}
        lines = screen.get("tail") or []
        if screen.get("source") != "screen" or not isinstance(lines, list):
            return False, "current_screen_unverified"
        # Native screen reads extract real drafts (including multiline text)
        # into this separate field and may replace the visible row with just ›.
        if "draft" in screen:
            return False, "composer_draft_present"
        composer = [i for i, line in enumerate(lines) if isinstance(line, str) and re.match(r"\s*›", line)]
        if not composer:
            return False, "current_composer_missing"
        suffix = re.sub(r"^\s*›", "", lines[composer[-1]], count=1).strip()
        if suffix:
            if not stock_placeholder(suffix):
                return False, "composer_not_empty"
            # Absence of draft plus a stock placeholder is admitted only on the
            # currently audited host build. A saved scope version is insufficient.
            status = self.call("status")
            version = ((status.get("result") or {}).get("runtime") or {}).get("appVersion")
            if status.get("ok") is not True or version != DRAFT_METADATA_VERSION:
                return False, "composer_metadata_version_unverified"
        above = " ".join(str(line).strip() for line in lines[max(0, composer[-1] - 8):composer[-1]])
        if not re.search(r"[■⚠]\s+" + re.escape(CAPACITY_MESSAGE), above):
            return False, "latest_capacity_notice_not_current"
        return True, "best_effort_preflight_passed"

    def send(self, request_id=None):
        args = ["terminal", "send", "--terminal", self.scope["terminal_handle"],
                "--text", CONTINUE_TEXT, "--enter", "--wait-submit", "1"]
        if request_id:
            args += ["--retry-request", request_id]
        return self.call(*args)


class NativeRunner:
    def __init__(self, scope, host=None, clock=time.time, sleep=time.sleep):
        self.scope = scope
        self.host = host or OrcaCLI(scope)
        self.clock, self.sleep = clock, sleep
        self.directory = Path(scope["native_state_dir"])
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = self.directory / "state.json"
        self.data = None
        self.policy = None

    def save(self, reason=None):
        if reason:
            self.data["last_check_reason"] = reason
        self.data["policy"] = asdict(self.policy)
        self.data["updated_at"] = self.clock()
        atomic_json(self.path, self.data)
        status = self.policy.snapshot()
        status.update({"adapter": "native_scheduled_precheck", "automatic_retry_enabled": self.scope.get("delivery_enabled", False),
                       "delivery_guard": "fresh_best_effort_preflight", "updated_at": self.data["updated_at"],
                       "last_check_reason": self.data.get("last_check_reason"),
                       "delivery": self.data.get("delivery"), "baseline_offset": self.data["baseline_offset"],
                       "observed_offset": self.data["cursor"]})
        atomic_json(self.directory / "status.json", status)
        transition = {key: status.get(key) for key in ("status", "reason", "pending", "last_check_reason", "delivery")}
        if transition != self.data.get("last_transition"):
            with (self.directory / "events.jsonl").open("a") as stream:
                os.chmod(stream.name, 0o600)
                stream.write(json.dumps({"at": self.clock(), **transition}, ensure_ascii=False) + "\n")
            self.data["last_transition"] = transition
            atomic_json(self.path, self.data)

    def initialize(self):
        s = self.scope
        self.policy = RetryState(**{key: s[key] for key in
            ("thread_id", "terminal_handle", "terminal_incarnation", "account_scope", "model_id")}, require_atomic_guard=False)
        stat = Path(s["rollout_path"]).stat()
        self.data = {"cursor": 0, "baseline_offset": 0, "file_identity": [stat.st_dev, stat.st_ino],
                     "session_id": None, "session_cwd": None, "current_model": None, "delivery": None,
                     "created_at": self.clock(), "initialized": True}
        self.read_new(baseline=True)
        self.policy.cancel("startup_baseline")
        self.data["baseline_offset"] = self.data["cursor"]
        self.save("baseline_at_eof_no_historical_retry")

    def load(self):
        if not self.path.exists():
            self.initialize()
            return False
        self.data = json.loads(self.path.read_text())
        self.policy = RetryState(**self.data["policy"])
        return True

    def read_new(self, baseline=False):
        path = Path(self.scope["rollout_path"])
        stat = path.stat()
        if [stat.st_dev, stat.st_ino] != self.data["file_identity"] or stat.st_size < self.data["cursor"]:
            self.initialize()
            return
        with path.open("rb") as stream:
            stream.seek(self.data["cursor"])
            while True:
                offset = stream.tell()
                line = stream.readline()
                if not line or not line.endswith(b"\n"):
                    break
                self.data["cursor"] = stream.tell()
                try:
                    record = json.loads(line)
                except (ValueError, UnicodeError):
                    continue
                if not isinstance(record, dict):
                    continue
                payload = record.get("payload") or {}
                if not isinstance(payload, dict):
                    continue
                if record.get("type") == "session_meta":
                    self.data["session_id"], self.data["session_cwd"] = payload.get("id"), payload.get("cwd")
                if record.get("type") == "turn_context":
                    self.data["current_model"] = payload.get("model")
                if record.get("type") == "event_msg" and payload.get("type") == "thread_settings_applied":
                    self.data["current_model"] = (payload.get("thread_settings") or {}).get("model", self.data["current_model"])
                event = classify(record, self.policy.thread_id, offset)
                occurred = event_time(record)
                if event and event["kind"] == "capacity" and (occurred is None or occurred > self.clock() + 5):
                    self.policy.cancel("capacity_timestamp_unverified")
                    continue
                self.policy.observe(event, occurred if occurred is not None else self.clock())
                if event and event["kind"] in ("active", "new_message", "stop", "complete", "other_error"):
                    self.data["delivery"] = None
        if baseline:
            self.policy.cancel("startup_baseline")

    def scope_matches(self):
        return (self.data["session_id"] == self.scope["thread_id"]
                and self.data["session_cwd"] == self.scope["workspace_path"]
                and self.data["current_model"] == self.scope["model_id"])

    def reconcile(self):
        delivery = self.data.get("delivery")
        if not delivery or delivery["outcome"] not in ("reconcile_same_request", "accepted_unproven") or delivery.get("reconciled_at"):
            return
        if not delivery.get("request_id"):
            delivery["outcome"] = "unknown_do_not_resend"
            return
        expected = (delivery["event_id"], delivery["request_id"])
        self.read_new()
        current = self.data.get("delivery")
        if (not current or (current.get("event_id"), current.get("request_id")) != expected
                or self.policy.active_turn or not self.scope_matches()):
            self.save("user_or_scope_changed_before_reconciliation")
            return
        ready, reason = self.host.preflight()
        self.read_new()
        current = self.data.get("delivery")
        if (not ready or not current or (current.get("event_id"), current.get("request_id")) != expected
                or self.policy.active_turn or not self.scope_matches()):
            self.save(reason if not ready else "user_or_scope_changed_during_reconciliation_checks")
            return
        # Exact replay of an attested durable request observes/reconciles that
        # request; it does not mint a second prompt. Never replay after a refusal.
        response = self.host.send(delivery["request_id"])
        self.data["delivery"] = {**receipt(response), "event_id": delivery["event_id"],
                                 "attempted_at": delivery["attempted_at"], "reconciled_at": self.clock()}
        if self.data["delivery"]["outcome"] == "reconcile_same_request":
            self.data["delivery"]["outcome"] = "unknown_do_not_resend"
        self.save("same_durable_request_reconciled")

    def tick(self, check_only=False):
        existing = self.load()
        if not existing:
            return "initialized"
        self.read_new()
        if not self.scope_matches():
            self.policy.cancel("thread_or_model_scope_changed")
            self.save("thread_or_model_scope_changed")
            return "scope_changed"
        if self.policy.active_turn:
            self.save("active_work_no_delivery")
            return "active"
        if check_only or not self.scope.get("delivery_enabled"):
            self.save("check_only_no_delivery")
            return "check_only"
        if self.data.get("delivery"):
            self.reconcile()
            self.save("existing_delivery_no_new_prompt")
            return "existing_delivery"
        if not self.policy.pending:
            self.save("no_new_capacity_event")
            return "no_event"
        # Timestamp is the provider event time, not first observation time. A
        # one-minute scheduler tick therefore waits only the remaining 0–60s.
        remaining = min(60, max(0, self.policy.pending["due_at"] - self.clock()))
        deadline = self.clock() + remaining
        while self.clock() < deadline:
            self.save("waiting_until_event_timestamp_plus_60")
            self.sleep(min(1, deadline - self.clock()))
            self.read_new()
            if not self.policy.pending or self.policy.active_turn or not self.scope_matches():
                self.save("user_or_work_changed_during_wait")
                return "cancelled"
        ready, reason = self.host.preflight()
        # Re-read after host RPCs and immediately before delivery; fresh user or
        # stop events win. The remaining check/write gap is explicitly best effort.
        self.read_new()
        if not self.policy.pending or self.policy.active_turn or not self.scope_matches():
            self.save("user_or_work_changed_after_preflight")
            return "cancelled"
        if not ready:
            self.policy.cancel(reason)
            self.save(reason)
            return "preflight_refused"
        proof = {key: self.scope[key] for key in
                 ("thread_id", "terminal_handle", "terminal_incarnation", "account_scope", "model_id")}
        proof.update(event_id=self.policy.last_event_id, transport_ready=True,
                     active_work=False, user_stopped=False, new_message=False)
        intent = self.policy.due(self.clock(), proof)
        if not intent:
            self.save("no_delivery_intent")
            return "no_intent"
        # Save before spawning. If the process dies before Orca returns a request
        # ID, the saved unknown state forbids a second send for this same event.
        self.data["delivery"] = {"event_id": intent["event_id"], "outcome": "unknown_do_not_resend",
                                 "request_id": None, "attempted_at": self.clock()}
        self.save("one_prompt_attempt_started")
        response = self.host.send()
        self.data["delivery"] = {**receipt(response), "event_id": intent["event_id"],
                                 "attempted_at": self.data["delivery"]["attempted_at"]}
        self.save("prompt_receipt_recorded")
        self.reconcile()
        return "attempted"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", type=Path, required=True)
    parser.add_argument("--initialize", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    scope = json.loads(args.scope.read_text())
    runner = NativeRunner(scope)
    lock_path = Path(scope["native_state_dir"]) / "run.lock"
    with lock_path.open("a") as lock:
        os.chmod(lock_path, 0o600)
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        if args.initialize:
            runner.initialize()
        else:
            runner.tick(check_only=args.check_only)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # No unbounded diagnostics, transcript, environment, or credential dumps.
        print("capacity native precheck: local check failed; no automatic fresh retry", file=sys.stderr)
    finally:
        raise SystemExit(1)
