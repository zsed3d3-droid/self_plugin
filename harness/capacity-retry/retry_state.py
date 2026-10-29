"""Capacity retry policy; time and delivery are supplied by the caller.

Only provider-owned task_complete/error fields are admitted. Text in user messages,
assistant messages, tools, or terminal output is never inspected for capacity.
"""
from dataclasses import asdict, dataclass, field
import hashlib
import json


CAPACITY_MESSAGE = "Selected model is at capacity. Please try a different model."


def classify(record, thread_id, offset=0):
    if not isinstance(record, dict):
        return None
    payload = record.get("payload") or {}
    if not isinstance(payload, dict):
        return None
    kind = payload.get("type")
    base = {"thread_id": thread_id, "turn_id": payload.get("turn_id")}
    if record.get("type") != "event_msg":
        return None
    if kind == "item_completed" and isinstance(payload.get("item"), dict) and payload["item"].get("type") == "UserMessage":
        return {**base, "kind": "new_message"}
    if kind == "task_started":
        return {**base, "kind": "active"}
    if kind in ("turn_aborted", "task_cancelled"):
        return {**base, "kind": "stop"}
    if kind != "task_complete":
        return None
    error = payload.get("error")
    if not error:
        return {**base, "kind": "complete"}
    # Do not infer transport failures from an unstructured string or display copy.
    if not isinstance(error, dict):
        return {**base, "kind": "other_error"}
    exact = error.get("codex_error_info") == "server_overloaded" and error.get("message") == CAPACITY_MESSAGE
    if not exact:
        return {**base, "kind": "other_error"}
    identity = [thread_id, payload.get("turn_id"), record.get("timestamp"), offset, "server_overloaded"]
    return {**base, "kind": "capacity", "event_id": hashlib.sha256(json.dumps(identity).encode()).hexdigest()[:24]}


@dataclass
class RetryState:
    thread_id: str
    terminal_handle: str
    terminal_incarnation: str
    account_scope: str
    model_id: str
    delay_seconds: int = 60
    status: str = "observing"
    reason: str = "startup_baseline"
    active_turn: str | None = None
    pending: dict | None = None
    last_event_id: str | None = None
    seen: list = field(default_factory=list)
    retries: int = 0
    require_atomic_guard: bool = True

    def __post_init__(self):
        if any(not isinstance(value, str) or not value.strip() for value in
               (self.thread_id, self.terminal_handle, self.terminal_incarnation, self.account_scope, self.model_id)):
            raise ValueError("Every same-session scope value is required")
        if self.delay_seconds != 60:
            raise ValueError("This policy requires the requested 60-second delay")

    def cancel(self, reason):
        self.pending = None
        self.status, self.reason = "observing", reason

    def observe(self, event, now):
        if not event or event.get("thread_id") != self.thread_id:
            return
        kind = event["kind"]
        if kind == "active":
            self.cancel("active_work")
            self.active_turn = event.get("turn_id")
        elif kind == "new_message":
            self.cancel("new_user_message")
            # Codex publishes task_started before its UserMessage item. Preserve
            # that exact turn; a message for another turn invalidates old work.
            if event.get("turn_id") != self.active_turn:
                self.active_turn = None
        elif kind == "stop":
            self.cancel("user_stop_or_pause")
            self.active_turn = None
        elif kind in ("complete", "other_error"):
            relevant = self.active_turn or (self.pending or {}).get("turn_id")
            if relevant and event.get("turn_id") != relevant:
                return
            self.cancel("completed" if kind == "complete" else "non_capacity_error")
            self.active_turn = None
        elif kind == "capacity":
            event_id = event.get("event_id")
            if not event_id or event_id in self.seen:
                return
            self.seen = (self.seen + [event_id])[-256:]
            # Ignore mismatched turn results (e.g. an old task's late completion).
            if not event.get("turn_id") or self.active_turn != event["turn_id"]:
                return
            self.active_turn = None
            self.last_event_id = event_id
            self.pending = {"event_id": event_id, "turn_id": event["turn_id"], "due_at": now + self.delay_seconds}
            self.status, self.reason = "waiting", "capacity_transport_error"

    def due(self, now, proof):
        """Return one durable delivery intent only with a fresh, exact host proof.

        Native adapters may explicitly opt into fresh best-effort preflight checks.
        That mode does not claim the read and complete prompt write are atomic.
        """
        if not self.pending or now < self.pending["due_at"] or self.status != "waiting":
            return None
        expected = {"thread_id": self.thread_id, "terminal_handle": self.terminal_handle,
                    "terminal_incarnation": self.terminal_incarnation, "account_scope": self.account_scope,
                    "model_id": self.model_id,
                    "event_id": self.pending["event_id"]}
        if any(proof.get(k) != v for k, v in expected.items()):
            self.cancel("scope_or_latest_event_changed")
            return None
        if proof.get("active_work") or proof.get("user_stopped") or proof.get("new_message"):
            self.cancel("host_activity_or_user_override")
            return None
        if not proof.get("transport_ready") or (self.require_atomic_guard and not proof.get("atomic_sendable_guard")):
            self.status, self.reason = "blocked", "same_session_delivery_transport_unavailable"
            return None
        if any(proof.get(key) is not False for key in ("active_work", "user_stopped", "new_message")):
            self.status, self.reason = "blocked", "host_activity_unverified"
            return None
        intent = {**expected, "request_id": "capacity-retry-" + self.pending["event_id"]}
        self.status, self.reason = "submitting", "one_retry_for_event"
        self.retries += 1
        return intent

    def snapshot(self):
        value = asdict(self)
        value.pop("seen")
        return value
