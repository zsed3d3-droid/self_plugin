"""PostgreSQL-backed, single-user Codex broker with explicit scope continuity.

Advisory locks serialize each scope across processes. No request is automatically
replayed. A lost/unconfirmed turn blocks the scope until an explicit user decision.
Only bounded protocol metadata and final results enter the DB; prompts and raw
provider diagnostics are not logged by this service. Codex owns its session files.
"""
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
import base64
import binascii
import hashlib
import hmac
import io
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import tempfile
import threading
import time
from typing import Literal
import uuid
import warnings

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field

SCOPE_PATTERN = r'^[a-zA-Z0-9:_.-]+$'
MAX_EVENT_LINE = 4 * 1024 * 1024
MAX_RESULT = 8 * 1024 * 1024
MAX_IMAGES = 3
MAX_IMAGE_BYTES = 4 * 1024 * 1024
MAX_TOTAL_IMAGE_BYTES = 12 * 1024 * 1024
MAX_IMAGE_PIXELS = 16_000_000
MAX_IMAGE_BASE64 = 4 * ((MAX_IMAGE_BYTES + 2) // 3)
IMAGE_FORMATS = {'image/png': ('PNG', '.png'), 'image/jpeg': ('JPEG', '.jpg'), 'image/webp': ('WEBP', '.webp')}


class TurnImage(BaseModel):
    model_config = ConfigDict(extra='forbid')
    mime_type: Literal['image/png', 'image/jpeg', 'image/webp']
    data_base64: str = Field(min_length=4, max_length=MAX_IMAGE_BASE64, repr=False)


@dataclass(frozen=True)
class PreparedImage:
    raw: bytes = field(repr=False)
    mime_type: str
    sha256: str
    width: int
    height: int

    def receipt(self):
        return {'mime_type': self.mime_type, 'sha256': self.sha256, 'width': self.width, 'height': self.height}


def prepare_images(items):
    """Decode and verify bounded raster bytes before any request/session DB write."""
    result, total = [], 0
    if len(items) > MAX_IMAGES:
        raise HTTPException(422, 'Invalid image input')
    try:
        for item in items:
            raw = base64.b64decode(item.data_base64, validate=True)
            total += len(raw)
            if not raw or len(raw) > MAX_IMAGE_BYTES or total > MAX_TOTAL_IMAGE_BYTES:
                raise ValueError('image_size')
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(raw)) as image:
                    width, height = image.size
                    if (image.format != IMAGE_FORMATS[item.mime_type][0] or width * height > MAX_IMAGE_PIXELS or
                            not 0 < width <= 16000 or not 0 < height <= 16000 or getattr(image, 'n_frames', 1) != 1):
                        raise ValueError('image_format_or_dimensions')
                    image.verify()
                with Image.open(io.BytesIO(raw)) as image:
                    image.load()  # Header recognition alone is not a decoded image.
            result.append(PreparedImage(raw, item.mime_type, hashlib.sha256(raw).hexdigest(), width, height))
    except (ValueError, KeyError, OSError, SyntaxError, binascii.Error, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(422, 'Invalid image input') from None
    return result


def request_digest(request, images):
    # Preserve historical text-only hashes, including model=None, across this extension.
    payload = request.model_dump(mode='json', exclude={'images'})
    if images:
        payload['images'] = [{'mime_type': image.mime_type, 'sha256': image.sha256} for image in images]
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


@contextmanager
def image_files(images):
    if not images:
        yield []
        return
    with tempfile.TemporaryDirectory(prefix='codex-turn-', dir='/tmp') as directory:
        paths = []
        for index, image in enumerate(images, 1):
            path = Path(directory) / f'image-{index}{IMAGE_FORMATS[image.mime_type][1]}'
            with os.fdopen(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'wb') as handle:
                handle.write(image.raw)
            paths.append(str(path))
        yield paths


@dataclass(frozen=True)
class Settings:
    database_url: str = field(repr=False)
    token: str = field(repr=False)
    database_schema: str = 'broker'
    codex_bin: str = 'codex'
    codex_home: str = '/codex'
    output_dir: str = '/outputs'
    timeout: float = 240
    failure_budget: int = 3

    @classmethod
    def from_env(cls):
        return cls(database_url=os.getenv('BROKER_DATABASE_URL', ''),
                   token=os.getenv('BROKER_TOKEN', ''),
                   database_schema=os.getenv('BROKER_DATABASE_SCHEMA', 'broker'),
                   codex_bin=os.getenv('CODEX_BIN', 'codex'),
                   codex_home=os.getenv('CODEX_HOME', '/codex'),
                   output_dir=os.getenv('BROKER_OUTPUT_DIR', '/outputs'),
                   timeout=max(1, float(os.getenv('TURN_TIMEOUT', '240'))),
                   failure_budget=max(1, int(os.getenv('BROKER_FAILURE_BUDGET', '3'))))


def db(settings):
    if not re.fullmatch(r'[a-z_][a-z0-9_]{0,62}', settings.database_schema):
        raise RuntimeError('Invalid broker database schema')
    if not settings.database_url:
        raise RuntimeError('Broker database is not configured')
    return psycopg.connect(settings.database_url, autocommit=True, row_factory=dict_row,
                           connect_timeout=3, options=f'-c statement_timeout=5000 -c search_path={settings.database_schema}')


def lock_key(scope):
    return int.from_bytes(hashlib.sha256(('personal-codex-broker:' + scope).encode()).digest()[:8], 'big', signed=True)


@contextmanager
def scope_lock(settings, scope):
    with db(settings) as connection:
        locked = connection.execute('SELECT pg_try_advisory_lock(%s) AS ok', (lock_key(settings.database_schema + ':' + scope),)).fetchone()['ok']
        if not locked:
            raise HTTPException(409, {'status': 'busy', 'message': 'A turn or decision is already active for this scope.'})
        try:
            yield connection
        finally:
            try:
                connection.execute('SELECT pg_advisory_unlock(%s)', (lock_key(settings.database_schema + ':' + scope),))
            except psycopg.Error:
                pass  # Closing a dead connection releases the session lock on PostgreSQL.


def initialize(settings):
    with db(settings) as connection:
        # Serialize schema initialization without touching another worker's running requests.
        with connection.transaction():
            connection.execute('SELECT pg_advisory_xact_lock(%s)', (lock_key(settings.database_schema + ':__schema__'),))
            connection.execute(sql.SQL('CREATE SCHEMA IF NOT EXISTS {}').format(sql.Identifier(settings.database_schema)))
            connection.execute('''CREATE TABLE IF NOT EXISTS sessions (
                scope text PRIMARY KEY, thread_id uuid UNIQUE, blocked boolean NOT NULL DEFAULT false,
                failure_count integer NOT NULL DEFAULT 0, failure_budget integer NOT NULL,
                paused_reason text, updated_at timestamptz NOT NULL DEFAULT now())''')
            connection.execute('''CREATE TABLE IF NOT EXISTS requests (
                id uuid PRIMARY KEY, scope text NOT NULL REFERENCES sessions(scope),
                payload_hash text NOT NULL, status text NOT NULL CHECK(status IN ('running','completed','unknown')),
                owner_token uuid NOT NULL, result jsonb, error_code text,
                created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now())''')
            connection.execute('''CREATE TABLE IF NOT EXISTS events (
                event_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                scope text NOT NULL REFERENCES sessions(scope), request_id uuid REFERENCES requests(id),
                event_type text NOT NULL, details jsonb NOT NULL DEFAULT '{}',
                created_at timestamptz NOT NULL DEFAULT now())''')
            connection.execute('CREATE INDEX IF NOT EXISTS broker_requests_scope ON requests(scope, created_at DESC)')
            connection.execute('CREATE INDEX IF NOT EXISTS broker_events_scope ON events(scope, event_id DESC)')


def event(connection, scope, request_id, event_type, details=None):
    connection.execute('INSERT INTO events(scope,request_id,event_type,details) VALUES(%s,%s,%s,%s)',
                       (scope, request_id, event_type, Jsonb(details or {})))


def pause_after_failure(connection, scope, request_id, code):
    session = connection.execute('''UPDATE sessions SET blocked=true,failure_count=failure_count+1,
        paused_reason=CASE WHEN failure_count+1>=failure_budget THEN 'retry_budget_exhausted' ELSE 'uncertain_outcome' END,
        updated_at=now() WHERE scope=%s RETURNING *''', (scope,)).fetchone()
    event(connection, scope, request_id, 'turn_unknown', {'code': code})
    if session['failure_count'] >= session['failure_budget']:
        event(connection, scope, request_id, 'retry_budget_exhausted',
              {'failures': session['failure_count'], 'budget': session['failure_budget'], 'requires_user_decision': True})
    return session


def recover_orphan(connection, scope):
    """Only call while owning scope's advisory lock; an active worker is never swept."""
    with connection.transaction():
        rows = connection.execute("UPDATE requests SET status='unknown',error_code='owner_disconnected',updated_at=now() WHERE scope=%s AND status='running' RETURNING id", (scope,)).fetchall()
        for row in rows:
            pause_after_failure(connection, scope, row['id'], 'owner_disconnected')


def mark_unknown(settings, request_id, owner, scope, code):
    with db(settings) as connection, connection.transaction():
        row = connection.execute("UPDATE requests SET status='unknown',error_code=%s,updated_at=now() WHERE id=%s AND owner_token=%s AND status='running' RETURNING id", (code, request_id, owner)).fetchone()
        if row:
            pause_after_failure(connection, scope, request_id, code)


def run_codex(settings, request, owner, existing_thread, lock_connection, images=()):
    # The inner runner terminates/joins its process before these private files are removed.
    with image_files(images) as paths:
        result = _run_codex(settings, request, owner, existing_thread, lock_connection, paths)
    result.update(image_count=len(images), images=[image.receipt() for image in images])
    return result


def _run_codex(settings, request, owner, existing_thread, lock_connection, image_paths):
    command = [settings.codex_bin, 'exec', '--ignore-user-config', '--ignore-rules', '--json',
               '--disable', 'shell_tool', '--disable', 'unified_exec',
               '--skip-git-repo-check', '-s', 'read-only', '-c', 'approval_policy="never"',
               '-C', settings.output_dir]
    if request.model:
        command.extend(['-m', request.model])
    if existing_thread:
        command.append('resume')
    for path in image_paths:
        command.extend(['--image', path])
    if image_paths:
        command.append('--')  # exec's variadic --image cannot consume stdin '-' or the resume UUID.
    if existing_thread:
        command.append(str(existing_thread))
    command.append('-')  # stdin prompt remains last; it cannot be consumed as an image path.
    env = {key: value for key, value in os.environ.items()
           if key in {'PATH', 'HOME', 'LANG', 'TMPDIR', 'SSL_CERT_FILE', 'SSL_CERT_DIR'}}
    env['CODEX_HOME'] = settings.codex_home
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, env=env, start_new_session=True,
                               cwd=settings.output_dir)
    state = {'thread': str(existing_thread) if existing_thread else None, 'complete': False,
             'chunks': [], 'size': 0, 'error': None}

    def protocol_reader():
        try:
            while True:
                line = process.stdout.readline(MAX_EVENT_LINE + 1)
                if not line:
                    break
                if len(line) > MAX_EVENT_LINE:
                    raise ValueError('event_too_large')
                try:
                    item = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(item, dict):
                    continue
                if item.get('type') == 'thread.started':
                    thread = str(uuid.UUID(item['thread_id']))
                    if state['thread'] and state['thread'] != thread:
                        raise ValueError('thread_mismatch')
                    # Commit before consuming the next event so a crash retains its original thread.
                    with db(settings) as connection, connection.transaction():
                        updated = connection.execute('''UPDATE sessions SET thread_id=%s,updated_at=now()
                            WHERE scope=%s AND (thread_id IS NULL OR thread_id=%s)
                            AND EXISTS(SELECT 1 FROM requests WHERE id=%s AND owner_token=%s AND status='running')
                            RETURNING thread_id''', (thread, request.scope, thread, request.request_id, owner)).fetchone()
                        if not updated:
                            raise ValueError('thread_mapping_lost')
                        event(connection, request.scope, request.request_id, 'thread_bound', {'thread_id': thread})
                    state['thread'] = thread
                if item.get('type') == 'item.completed' and item.get('item', {}).get('type') == 'agent_message':
                    text = item['item'].get('text')
                    if not isinstance(text, str):
                        raise ValueError('invalid_agent_message')
                    state['size'] += len(text)
                    if state['size'] > MAX_RESULT:
                        raise ValueError('result_too_large')
                    state['chunks'].append(text)
                if item.get('type') == 'turn.completed':
                    state['complete'] = True
                if item.get('type') in {'turn.failed', 'error'}:
                    state['error'] = 'codex_reported_failure'
        except Exception:
            state['error'] = 'protocol_or_persistence_failure'
        finally:
            process.stdout.close()

    def discard_errors():
        try:
            while process.stderr.read(8192):
                pass  # Never persist or print raw provider stderr.
        finally:
            process.stderr.close()

    def provide_input():
        try:
            process.stdin.write(request.prompt)
            process.stdin.close()
        except (OSError, ValueError):
            state['error'] = 'input_failed'

    threads = [threading.Thread(target=fn, daemon=True) for fn in (protocol_reader, discard_errors, provide_input)]
    for thread in threads:
        thread.start()
    deadline = time.monotonic() + settings.timeout
    try:
        while process.poll() is None:
            if state['error']:
                raise RuntimeError(state['error'])
            if time.monotonic() >= deadline:
                raise RuntimeError('timeout')
            # Losing the scope-lock DB connection must stop its model process. A new worker
            # can then classify the original request unknown, never automatically replay it.
            lock_connection.execute('SELECT 1')
            time.sleep(0.1)
        for thread in threads:
            thread.join(6)
        if any(thread.is_alive() for thread in threads):
            raise RuntimeError('stream_not_closed')
        if process.returncode or state['error'] or not state['complete'] or not state['thread'] or not state['chunks']:
            raise RuntimeError(state['error'] or 'completion_unconfirmed')
        return {'request_id': str(request.request_id), 'scope': request.scope,
                'thread_id': state['thread'], 'text': '\n'.join(state['chunks']), 'status': 'completed'}
    finally:
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=5)
        for thread in threads:
            thread.join(6)


class Turn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    scope: str = Field(min_length=1, max_length=180, pattern=SCOPE_PATTERN)
    request_id: uuid.UUID
    prompt: str = Field(min_length=1, max_length=160000)
    model: str | None = Field(default=None, max_length=100, pattern=r'^[a-zA-Z0-9_.:-]+$')
    images: list[TurnImage] = Field(default_factory=list, max_length=MAX_IMAGES, repr=False)


class Resolve(BaseModel):
    inspected: bool
    action: Literal['continue', 'stop'] = 'continue'
    reason: str = Field(min_length=1, max_length=4000)
    reset_budget: bool = False


def create_app(settings=None):
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(_app):
        try:
            initialize(settings)
        except Exception:
            raise RuntimeError('Broker database is unavailable; no local storage fallback is enabled.') from None
        yield

    service = FastAPI(title='Personal Codex Broker', lifespan=lifespan)

    @service.exception_handler(RequestValidationError)
    async def invalid_request(_request, _error):
        # Pydantic's default error includes rejected input (possibly image base64).
        return JSONResponse(status_code=422, content={'detail': 'Invalid broker request'})

    def auth(authorization: str = Header(default='')):
        if not settings.token or not hmac.compare_digest(authorization, 'Bearer ' + settings.token):
            raise HTTPException(401, 'Broker authentication required')

    @service.get('/health')
    def health():
        try:
            with db(settings) as connection:
                connection.execute('SELECT 1 FROM sessions LIMIT 1')
        except Exception:
            raise HTTPException(503, 'Broker database unavailable') from None
        present = (Path(settings.codex_home) / 'auth.json').is_file()
        return {'status': 'ok', 'engine': 'codex', 'credential_file_present': present,
                'authenticated': present, 'authentication_check': 'file_presence_only'}

    @service.get('/sessions', dependencies=[Depends(auth)])
    def sessions():
        try:
            with db(settings) as connection:
                return connection.execute('SELECT * FROM sessions ORDER BY updated_at DESC LIMIT 1000').fetchall()
        except psycopg.Error:
            raise HTTPException(503, 'Broker database unavailable') from None

    @service.get('/requests/{request_id}', dependencies=[Depends(auth)])
    def get_request(request_id: uuid.UUID):
        try:
            with db(settings) as connection:
                row = connection.execute('SELECT id,scope,status,result,error_code,created_at,updated_at FROM requests WHERE id=%s', (request_id,)).fetchone()
                if not row:
                    raise HTTPException(404, 'Request not found')
                return row
        except psycopg.Error:
            raise HTTPException(503, 'Broker database unavailable') from None

    @service.get('/sessions/{scope}/events', dependencies=[Depends(auth)])
    def events(scope: str):
        if not re.fullmatch(SCOPE_PATTERN, scope) or len(scope) > 180:
            raise HTTPException(422, 'Invalid scope')
        try:
            with db(settings) as connection:
                return connection.execute('SELECT event_id,scope,request_id,event_type,details,created_at FROM events WHERE scope=%s ORDER BY event_id DESC LIMIT 200', (scope,)).fetchall()
        except psycopg.Error:
            raise HTTPException(503, 'Broker database unavailable') from None

    @service.post('/turns', dependencies=[Depends(auth)])
    def turn(request: Turn):
        images = prepare_images(request.images)
        digest = request_digest(request, images)
        if images and not (Path(settings.codex_home) / 'auth.json').is_file():
            raise HTTPException(503, {'status': 'not_started', 'code': 'codex_authentication_required',
                                      'message': 'Complete the dedicated Codex login before image review.'})
        owner = uuid.uuid4()
        started = False
        try:
            with scope_lock(settings, request.scope) as connection:
                recover_orphan(connection, request.scope)
                with connection.transaction():
                    previous = connection.execute('SELECT * FROM requests WHERE id=%s', (request.request_id,)).fetchone()
                    if previous:
                        if previous['payload_hash'] != digest:
                            raise HTTPException(409, 'Request ID was already used with different content')
                        if previous['status'] == 'completed':
                            return previous['result']
                        raise HTTPException(409, {'request_id': str(request.request_id), 'status': previous['status'],
                                                  'message': 'This request will not be replayed. Inspect its retained session.'})
                    connection.execute('INSERT INTO sessions(scope,failure_budget) VALUES(%s,%s) ON CONFLICT(scope) DO NOTHING', (request.scope, settings.failure_budget))
                    session = connection.execute('SELECT * FROM sessions WHERE scope=%s', (request.scope,)).fetchone()
                    if session['blocked']:
                        raise HTTPException(409, {'status': session['paused_reason'], 'failures': session['failure_count'],
                                                  'budget': session['failure_budget'], 'requires_user_decision': True})
                    connection.execute('INSERT INTO requests(id,scope,payload_hash,status,owner_token) VALUES(%s,%s,%s,\'running\',%s)',
                                       (request.request_id, request.scope, digest, owner))
                    event(connection, request.scope, request.request_id, 'turn_started', {'resumed': session['thread_id'] is not None})
                started = True
                try:
                    result = run_codex(settings, request, owner, session['thread_id'], connection, images)
                except Exception as error:
                    # Internal codes only: never return raw provider/command errors or credentials.
                    code = str(error) if isinstance(error, RuntimeError) and str(error) in {
                        'timeout', 'input_failed', 'codex_reported_failure', 'protocol_or_persistence_failure',
                        'stream_not_closed', 'completion_unconfirmed'} else 'execution_unconfirmed'
                    mark_unknown(settings, request.request_id, owner, request.scope, code)
                    raise HTTPException(502, {'request_id': str(request.request_id), 'status': 'unknown',
                                              'message': 'Codex did not confirm completion. This request will not be replayed; inspect the session and submit an explicit decision.'}) from None
                with connection.transaction():
                    updated = connection.execute("UPDATE requests SET status='completed',result=%s,updated_at=now() WHERE id=%s AND owner_token=%s AND status='running' RETURNING id", (Jsonb(result), request.request_id, owner)).fetchone()
                    if not updated:
                        raise HTTPException(409, 'Request ownership changed; inspect its result before continuing')
                    connection.execute('UPDATE sessions SET failure_count=0,paused_reason=NULL,updated_at=now() WHERE scope=%s', (request.scope,))
                    event(connection, request.scope, request.request_id, 'turn_completed', {'thread_id': result['thread_id']})
                return result
        except HTTPException:
            raise
        except psycopg.errors.UniqueViolation:
            raise HTTPException(409, 'Request ID was claimed concurrently; inspect the existing request before continuing') from None
        except Exception:
            if started:
                try:
                    mark_unknown(settings, request.request_id, owner, request.scope, 'database_unavailable')
                except Exception:
                    pass
            raise HTTPException(503, {'request_id': str(request.request_id), 'status': 'unknown' if started else 'not_started',
                                      'message': 'Broker database unavailable. No automatic replay is performed.'}) from None

    @service.post('/sessions/{scope}/resolve', dependencies=[Depends(auth)])
    def resolve(scope: str, request: Resolve):
        if not re.fullmatch(SCOPE_PATTERN, scope) or len(scope) > 180:
            raise HTTPException(422, 'Invalid scope')
        if not request.inspected or not request.reason.strip():
            raise HTTPException(400, 'Inspect the retained Codex session and record the user decision first')
        try:
            with scope_lock(settings, scope) as connection:
                recover_orphan(connection, scope)
                with connection.transaction():
                    session = connection.execute('SELECT * FROM sessions WHERE scope=%s', (scope,)).fetchone()
                    if not session:
                        raise HTTPException(404, 'Session not found')
                    if not session['blocked']:
                        raise HTTPException(409, 'Session is not waiting for a user decision')
                    exhausted = session['failure_count'] >= session['failure_budget']
                    if request.action == 'continue' and exhausted and not request.reset_budget:
                        raise HTTPException(409, 'Retry budget is exhausted; explicit reset_budget=true is required to resume')
                    if request.action == 'stop':
                        connection.execute("UPDATE sessions SET paused_reason='user_stopped',updated_at=now() WHERE scope=%s", (scope,))
                    if request.action == 'continue':
                        connection.execute('UPDATE sessions SET blocked=false,paused_reason=NULL,failure_count=CASE WHEN %s THEN 0 ELSE failure_count END,updated_at=now() WHERE scope=%s', (request.reset_budget, scope))
                    event(connection, scope, None, 'user_decision', {'action': request.action, 'reason': request.reason.strip(),
                                                                   'reset_budget': request.reset_budget})
                return {'scope': scope, 'blocked': request.action == 'stop',
                        'thread_id': str(session['thread_id']) if session['thread_id'] else None,
                        'note': 'Original requests stay immutable. Continue with a new request ID in this exact scope.'}
        except HTTPException:
            raise
        except psycopg.Error:
            raise HTTPException(503, 'Broker database unavailable') from None

    return service


app = create_app()
