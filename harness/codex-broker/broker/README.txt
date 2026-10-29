Personal Codex Broker

Runtime contract
- PostgreSQL only. BROKER_DATABASE_URL is required; BROKER_DATABASE_SCHEMA defaults to broker.
- CODEX_HOME=/codex holds the container's own native Codex login and persistent session files.
- Never copy the developer's existing host authentication into this volume.
- BROKER_OUTPUT_DIR=/outputs is the only application work directory. The container root/source
  must be read-only; Codex model commands use the read-only sandbox for summary/chat requests.
- Only the private API and explicit local design gate receive BROKER_TOKEN. The browser never receives it.
- Port8030 is also bound to 127.0.0.1 for that gate; it is not a remote/public endpoint.
- CLI version 0.165.0, Node 22, Python 3.12; dependency versions are pinned in requirements.txt.

Login from the root Compose project, using the same /codex volume as the running service:
  docker compose exec broker codex login --device-auth
A person must finish the displayed device login. No OpenAI API key is requested or copied.

Endpoints (Bearer BROKER_TOKEN, except GET /health)
  POST /turns {scope, request_id: UUID, prompt, model?: string, images?: [{mime_type,data_base64}]}
  GET /requests/{UUID}
  GET /sessions
  GET /sessions/{scope}/events
  POST /sessions/{scope}/resolve
       {inspected:true, action:"continue"|"stop", reason:"the user's explicit decision", reset_budget:false}

Scope is the exact topic/meeting/task identity, e.g. meeting:<uuid> or task:<uuid>.
A new request_id in the same scope resumes its retained thread; --last is never used.
The same UUID and payload returns the original completed result without invoking Codex again.
The same UUID with a changed payload is a conflict. Database advisory locks serialize a scope
across worker processes without holding an open transaction during model execution.

Unconfirmed execution, timeout and interrupted owners become unknown; no automatic replay.
The thread.started event is committed immediately. Startup never globally sweeps another
worker's running request. An orphan is classified only after acquiring its own scope lock.
Unknown requests are immutable, and changing UUID does not bypass the blocked scope.
A user must inspect the retained session and explicitly decide to continue or stop.

BROKER_FAILURE_BUDGET (default 3) counts consecutive unconfirmed turns in that scope.
Exhaustion records retry_budget_exhausted. Continuing then requires reset_budget:true plus
an explicit user reason. A completed turn resets the consecutive-failure count. These are
attempt limits, not automatic retries, and an agent must not manufacture a user decision.

GET /health reports database readiness and auth.json file presence. The latter is not proof
of current provider access; authentication_check explicitly says file_presence_only.
The service does not log prompts, provider stderr or credentials. Codex itself retains its
native conversation state in the dedicated volume, as required for resume.

Verification
  python3 -m pytest tests/test_broker.py -q  (from harness/codex-broker; provide a dedicated TEST_DATABASE_URL)
Tests use TEST_DATABASE_URL and fresh broker_test_<uuid> schemas, plus a local fake executable;
no model calls or real credentials are used. Container login and real inference are separate checks.

Image review extension (2026-10-29): optional still PNG/JPEG/WebP, at most3 images,
4MiB each/12MiB total and16MP each. Decode and MIME validation precede DB access.
Raw-byte hashes bind idempotence; completed results include image receipts. Missing
container auth rejects image work as503/not_started before creating a session.
Temporary request files are mode600 and removed after execution; product captures stay.
See scenario-ui-ux/references/vision-critique.md for the full contract and test limits.

The local gate can be invoked with python3 scripts/design-check.py. It loads only
BROKER_TOKEN from this project's private .env into that child process and never prints it.
Native hook host trust and an existing unresolved task still require actual user action.
The expired device login did not authenticate this container; live vision remains untested.
