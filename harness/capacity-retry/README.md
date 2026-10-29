# Capacity retry policy and local observer

**Diagnostic observer active: true. Automatic retry enabled: false.** These are the verified states in the development workspace; installing this source elsewhere does not start anything automatically. The policy and read-only Docker observer are implemented and tested. The current macOS Orca integration cannot deliver a retry under the required container-only service boundary. This package must not be described as a working recovery hook.

The desired behavior is one retry 60 seconds after a new provider capacity failure, using the same terminal process, account, model, and thread. A new capacity failure may schedule another 60-second wait. A user message, stop, active task, changed scope, quota error, authentication error, or billing error cancels the pending retry. Quoted error text is never a trigger.

## What is implemented

- `retry_state.py` admits only the observed structured Codex `event_msg` → `task_complete` → `error` with `codex_error_info: "server_overloaded"` and the exact provider capacity message. It requires a matching active turn and assigns a stable per-event identity.
- `due()` uses an injected clock and emits at most one delivery intent per event. It requires exact scope, latest error, and an atomic host sendable-status guard. It fails closed when the delivery transport is unavailable. It never changes model, signs in, copies credentials, starts a session, or guesses whether an ambiguous send failed.
- `observer.py` folds only the selected thread's history to identify current work, then baselines at EOF. Historical capacity failures do not schedule retries. State is small JSON plus a transition log; transcript text and credentials are not logged.
- The Docker observer has no network, ports, credentials, host binary execution, or host service. It records a future capacity event and its due time, then records why delivery is blocked. It does **not** send a prompt.

## Verified host boundary

On Orca 1.4.230 / Codex CLI 0.165.0, the native capacity notice tracker marks a newly rendered TUI notice as failure, but exposes no capacity retry setting. Scheduled automations run prompts and may create a fresh session when a reused terminal disappears, so they do not satisfy this policy.

Orca's local CLI uses a macOS UNIX socket and its local runtime token. A Docker bind mount of that actual socket was rejected by Docker Desktop (`bind source path does not exist: /socket_mnt/...`). Container-to-host TCP port 6768 is reachable, but Orca's WebSocket transport requires a separately paired device token and E2EE handshake. The local UNIX token does not authorize that protocol. No pairing credentials or OpenAI credentials were read/copied, no new login was requested, and no additional host daemon was created.

The existing Codex lifecycle hooks do not establish that a transport failure invokes a hook before a model turn begins. A project `PostToolUse` hook cannot recover a failure at that boundary.

## Run tests

```sh
python3 -m unittest discover -s harness/capacity-retry -p 'test_*.py' -v
```

Tests use fake time and fake host proofs. They do not wait 60 real seconds or inject errors into a live agent.

## Apply the diagnostic observer locally

This installs observation only. It does not enable automatic recovery.

1. Follow the installed `orca-cli` skill: resolve its executable once, read `skills get orca-cli`, then obtain the existing terminal handle and process incarnation with `terminal show --json`. Never launch a replacement agent.
2. Copy `scope.example.json` to ignored `scope.json` and fill the exact existing thread/terminal/account scope. Use only the selected thread's rollout file; never mount the whole Codex home or authentication directory.
3. Create ignored `.env` containing `CAPACITY_ROLLOUT="/absolute/path/to/the-selected-rollout.jsonl"`, `CAPACITY_UID=<your uid>`, and `CAPACITY_GID=<your gid>` on separate lines. Obtain the numeric IDs with `id -u` and `id -g`. This lets the container read the selected private file as its existing owner.
4. Create `state/` writable by that user, with mode 0700. Run `docker compose up -d --build` from this directory.
5. Inspect `state/status.json`. It must say `mode: "observe_only"` and `automatic_retry_enabled: false`. `docker compose stop` stops observation without removing data.

Do not use `rm`, volume removal, or Docker pruning to clean up this package. Keep local scope, `.env`, state, raw transcripts, backup copies, and local integration evidence out of public repositories.

## What is still required for automatic recovery

A supported host integration must make the existing terminal's delivery interface available to the container, or Orca must expose a native capacity retry hook. It must prove the same thread/account/process/model and latest failure, atomically refuse active work, bind one durable request ID, and reobserve user stop/new input immediately before submission. The policy's delivery intent is not proof of submission. A real integration must verify the receipt's `turn_started` without resending on silence.

No live capacity failure was forced, and no live prompt was sent during validation.
