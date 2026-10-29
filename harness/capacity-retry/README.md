# Capacity retry policy and native Orca adapter

**Native capacity retry schedule enabled: true, with best-effort checks. Docker diagnostic observer active: true, with delivery disabled.** These are the development workspace's states; copying this package does not enable anything elsewhere. A real capacity failure was not forced, and no live test prompt was sent to the active agent.

`native_precheck.py` runs as an existing Orca scheduled **shell precheck**, before any model call. Every invocation and its shell wrapper exit nonzero, so the automation's required placeholder prompt is skipped. There is no new host daemon, cron service, login, credential copy, provider/model change, or replacement session.

## Recovery behavior

- Only a new provider-owned Codex `event_msg/task_complete/error` with `codex_error_info: "server_overloaded"` and the exact capacity message can arm recovery. User quotes, assistant/tool output, authentication, quota, and billing failures cannot.
- The deadline is **provider event timestamp + 60 seconds**. A one-minute scheduled tick waits only the remaining 0–60 seconds. Scheduler delay, app sleep, and availability can make recovery later; it does not wait another full minute after first noticing an old error.
- Installation baselines at EOF after identifying current work. Historical capacity errors never arm a retry. An exclusive state lock, per-event identity, and persisted delivery attempt prevent duplicate fresh sends.
- New user messages, stop/pause events, active work, changed process/account/thread/model evidence, or a non-capacity result cancel pending recovery. The selected existing terminal/process, pane account selection, scoped rollout identity/model, idle condition, and current native capacity notice are checked again before delivery.
- Unsent drafts have priority. Orca screen reads can extract a draft into the separate `draft` field and replace its visible row with `›`; **any `draft` field refuses delivery**. Other nonempty composer text also refuses delivery. Source-confirmed stock placeholders without draft metadata are accepted only after a fresh supported `orca status` verifies the currently audited **1.4.230** build. A host upgrade cannot retain that assumption from a saved scope value.
- The complete prompt check/write is not atomic. The adapter uses fresh best-effort reads and inherits Orca's native composer parsing; an unrecognized layout is refused. It does not claim a transactional thread/input fence.
- A returned ambiguous request ID is reconciled once with the **same** ID and exact payload, after fresh user/activity/scope/composer checks. Silence without an ID or a process crash after the saved attempt never authorizes a second fresh send. `input_accepted` alone is not claimed as `turn_started`.

## Validation

The policy and native adapter currently pass **54 tests** using fake time, fake provider events, and a private fake CLI executable. Coverage includes timestamp deadlines, first-send user/stop races before receipt reconciliation, multiline/placeholder-shaped real drafts, current host-version changes, ambiguous receipts, crash recovery, locks, duplicates, and consecutive fresh failures.

A harmless **scheduled** precheck ran in an isolated dummy workspace. It wrote a marker, exited 1, recorded `skipped_precheck`, and created no agent or terminal. The actual scoped adapter's read-only check reported active work with no pending retry, delivery, or prompt sent. See `VALIDATION.json` for the current integration summary.

```sh
python3 -m unittest discover -s harness/capacity-retry -p 'test_*.py' -v
```

## Native installation and operation

1. Follow the installed `orca-cli` skill: resolve its executable once and read its version-matched `skills get orca-cli` guide. The precheck option is documented by `automations create --help` in the tested build.
2. Copy `native-scope.example.json` to ignored `native-scope.local.json`. Bind it to the existing terminal/process/account/thread/model, exact rollout file, account-selection metadata, and a private state directory. Never copy authentication files. Confirm the values against public terminal metadata and the selected rollout's metadata.
3. Run `native_precheck.py --scope native-scope.local.json --initialize` to baseline, then `--check-only`. Both intentionally exit **1**. Inspect the private native `status.json`; initialization must not schedule old errors.
4. Create an existing-workspace automation **disabled** with a one-minute trigger, provider `codex`, an inert placeholder prompt, and precheck `<absolute-python> <absolute-native_precheck.py> --scope <absolute-private-scope>; exit 1`. Use a 120-second precheck timeout. After validation, enable it with `automations edit <id> --enabled`.
5. Inspect `automations runs --id <id> --json` and the private native state. Scheduled runs should end in `skipped_precheck`; delivery truth is in the native state and prompt receipt, not that automation status.

**Never invoke `automations run` or the automation's manual Run button.** Orca's manual path bypasses precheck and can launch its required placeholder prompt. This adapter is for scheduled execution only. Disable it with `automations edit <id> --disabled`; keep its state and run history.

The existing Docker observer is separate: `observer.py` has no network, ports, credentials, host binary execution, or delivery transport. Its `mode: "observe_only"` and `automatic_retry_enabled: false` remain correct. `compose.yaml` installs that diagnostic, not the native adapter.

## Local data and preservation

Private scope/configuration, exact thread/terminal/account identifiers, transcript pointers, status, logs, and snapshots stay in ignored `.env`, `scope.json`, `state/`, `local/`, and `*.local.json`. Do not publish them or raw rollouts/terminal output. `.dockerignore` excludes them from image build context. Sources and state were preserved before native adapter changes; the earlier Docker image was retained under a preservation tag.

The initial Docker-to-macOS UNIX socket mount was rejected. Orca's WebSocket requires separate pairing/E2EE. The native scheduled precheck runs through the existing host app and removes that transport obstacle without copying credentials or starting a host service.
