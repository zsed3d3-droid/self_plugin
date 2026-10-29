"""Read-only rollout observer. Delivery is deliberately unavailable on this host.

This is an applied diagnostic, NOT an enabled automatic recovery hook. See README.
"""
import json
import os
from pathlib import Path
import signal
import time
from retry_state import RetryState, classify


def atomic_json(path, value):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temp.replace(path)


def main():
    config = json.loads(Path("/config/scope.json").read_text())
    output = Path("/state")
    output.mkdir(exist_ok=True)
    state = RetryState(**{key: config[key] for key in ("thread_id", "terminal_handle", "terminal_incarnation", "account_scope", "model_id")})
    run = True

    def stop(*_):
        nonlocal run
        run = False
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    source = Path("/input/rollout.jsonl")
    last_summary = None
    epoch = time.time()
    # Fold history only to identify current work. No historical error is armed:
    # replaying an old capacity can interrupt a newer task.
    with source.open("rb") as stream:
        while line := stream.readline():
            try:
                state.observe(classify(json.loads(line), state.thread_id, stream.tell() - len(line)), epoch)
            except (ValueError, UnicodeError):
                continue
        state.cancel("startup_baseline")
        baseline = stream.tell()
        fragment = b""
        while run:
            now = time.time()
            data = stream.read(1024 * 1024)
            fragment += data
            while b"\n" in fragment:
                line, fragment = fragment.split(b"\n", 1)
                position = stream.tell() - len(fragment) - len(line) - 1
                try:
                    record = json.loads(line)
                except (ValueError, UnicodeError):
                    continue
                state.observe(classify(record, state.thread_id, position), now)
            # No credentials, prompt sending, Mac binaries, or host daemon in this container.
            state.due(now, {"thread_id": state.thread_id, "terminal_handle": state.terminal_handle,
                           "terminal_incarnation": state.terminal_incarnation, "account_scope": state.account_scope,
                           "model_id": state.model_id,
                           "event_id": state.last_event_id, "transport_ready": False})
            summary = state.snapshot()
            summary.update({"mode": "observe_only", "automatic_retry_enabled": False,
                            "transport_blocker": "mac_unix_socket_not_mountable_and_websocket_requires_separate_pairing",
                            "started_at": epoch, "baseline_offset": baseline, "observed_offset": stream.tell(),
                            "updated_at": now})
            atomic_json(output / "status.json", summary)
            concise = {key: summary[key] for key in ("status", "reason", "pending", "last_event_id", "retries")}
            if concise != last_summary:
                with (output / "events.jsonl").open("a") as log:
                    log.write(json.dumps({"at": now, **concise}) + "\n")
                last_summary = concise
            time.sleep(1)


if __name__ == "__main__":
    main()
