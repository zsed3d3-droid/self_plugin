"""Real PostgreSQL + a deterministic local fake Codex: no provider calls or credentials."""
import importlib.util
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import time
from concurrent.futures import ThreadPoolExecutor
import uuid

import psycopg
from psycopg import sql
import pytest
from PIL import Image
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('personal_broker_test_app', ROOT / 'broker/app.py')
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def database_url_for_tests():
    if os.getenv('TEST_DATABASE_URL'):
        return os.environ['TEST_DATABASE_URL']
    envfile = ROOT / '.env'
    if envfile.is_file():
        for line in envfile.read_text().splitlines():
            key, _, value = line.partition('=')
            if key.strip() == 'TEST_DATABASE_URL':
                return value.strip().strip('"').strip("'")
    return None


@pytest.fixture
def broker(tmp_path):
    url = database_url_for_tests()
    if not url:
        pytest.skip('TEST_DATABASE_URL required for PostgreSQL integration tests')
    home = tmp_path / 'codex-home'
    output = tmp_path / 'outputs'
    home.mkdir(); output.mkdir()
    fake = tmp_path / 'fake-codex'
    log = tmp_path / 'calls.jsonl'
    fake.write_text(f'''#!{sys.executable}
import hashlib,json,os,stat,sys,time,uuid
from pathlib import Path
args=sys.argv[1:]
prompt=sys.stdin.read()
attached=[]
for index,value in enumerate(args[:-1]):
 if value=='--image':
  path=Path(args[index+1]);raw=path.read_bytes()
  attached.append({{'path':str(path),'sha256':hashlib.sha256(raw).hexdigest(),'mode':stat.S_IMODE(path.stat().st_mode)}})
with open({str(log)!r},'a') as handle:handle.write(json.dumps({{'args':args,'prompt':prompt,'images':attached}})+'\\n')
root=Path(os.environ['CODEX_HOME'])/'sessions';root.mkdir(exist_ok=True)
previous=args[-2] if 'resume' in args else None
if previous and not (root/(previous+'.json')).is_file():sys.exit(3)
thread=previous or str(uuid.uuid4())
if prompt.startswith('reuse-thread:'):thread=prompt.partition(':')[2]
(root/(thread+'.json')).write_text(json.dumps({{'thread_id':thread}}))
print(json.dumps({{'type':'thread.started','thread_id':thread}}),flush=True)
if prompt=='slow':time.sleep(1)
if prompt=='hang':time.sleep(10)
if prompt=='fail':
 print('provider credential secret must never be returned',file=sys.stderr)
 sys.exit(1)
print(json.dumps({{'type':'item.completed','item':{{'type':'agent_message','text':'reply:'+prompt}}}}),flush=True)
print(json.dumps({{'type':'turn.completed','usage':{{'input_tokens':1,'output_tokens':1}}}}),flush=True)
''')
    fake.chmod(0o700)
    schema = 'broker_test_' + uuid.uuid4().hex
    settings = module.Settings(database_url=url, token='integration-test-only', database_schema=schema,
                               codex_bin=str(fake), codex_home=str(home), output_dir=str(output), timeout=4,
                               failure_budget=2)
    service = module.create_app(settings)
    with TestClient(service) as client:
        yield settings, client, log
    # Delete only this test's randomly named schema, never the application's broker schema.
    assert schema.startswith('broker_test_')
    with psycopg.connect(url, autocommit=True) as connection:
        connection.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))


def headers():
    return {'Authorization': 'Bearer integration-test-only'}


def payload(scope='meeting:one', prompt='hello', request_id=None):
    return {'scope': scope, 'request_id': request_id or str(uuid.uuid4()), 'prompt': prompt}


def calls(log):
    return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []


def post(client, data):
    return client.post('/turns', json=data, headers=headers())


def wait_running(settings, request_id, seconds=3):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        with module.db(settings) as connection:
            row = connection.execute('SELECT status FROM requests WHERE id=%s', (request_id,)).fetchone()
        if row and row['status'] == 'running':
            return
        time.sleep(0.03)
    raise AssertionError('The fake turn did not start')


def test_scope_thread_resume_and_idempotent_result_survive_fresh_app(broker):
    settings, client, log = broker
    first = payload()
    result = post(client, first)
    assert result.status_code == 200
    thread = result.json()['thread_id']
    assert post(client, first).json() == result.json()
    assert len(calls(log)) == 1
    different = dict(first, prompt='different content')
    assert post(client, different).status_code == 409
    with TestClient(module.create_app(settings)) as restarted:
        follow = post(restarted, payload(prompt='followup'))
        assert follow.status_code == 200
        assert follow.json()['thread_id'] == thread
    args = calls(log)[-1]['args']
    assert args[args.index('resume') + 1] == thread
    assert '--last' not in args and '--ephemeral' not in args
    assert '-s' in args and args[args.index('-s') + 1] == 'read-only'
    disabled = [args[index + 1] for index, value in enumerate(args[:-1]) if value == '--disable']
    assert set(disabled) == {'shell_tool', 'unified_exec'}
    assert '--ignore-user-config' in args and '--ignore-rules' in args
    assert (Path(settings.codex_home) / 'sessions' / (thread + '.json')).is_file()
    other = post(client, payload(scope='task:one'))
    assert other.status_code == 200 and other.json()['thread_id'] != thread


def test_active_scope_is_serialized_across_app_instances_and_startup_does_not_sweep_it(broker):
    settings, client, log = broker
    data = payload(prompt='slow')
    with ThreadPoolExecutor(max_workers=1) as pool:
        running = pool.submit(post, client, data)
        wait_running(settings, data['request_id'])
        with TestClient(module.create_app(settings)) as other_worker:
            still_running = other_worker.get('/requests/' + data['request_id'], headers=headers())
            assert still_running.json()['status'] == 'running'
            competing = post(other_worker, payload(prompt='competing'))
            assert competing.status_code == 409
            assert competing.json()['detail']['status'] == 'busy'
        assert running.result(timeout=5).status_code == 200
    assert len(calls(log)) == 1


def test_unknown_request_and_failure_budget_require_explicit_user_decision(broker):
    settings, client, log = broker
    first = payload(prompt='fail')
    assert post(client, first).status_code == 502
    session = client.get('/sessions', headers=headers()).json()[0]
    assert session['thread_id'] and session['blocked'] and session['failure_count'] == 1
    assert post(client, first).status_code == 409
    assert post(client, payload(prompt='new id cannot bypass')).status_code == 409
    assert len(calls(log)) == 1
    assert client.post('/sessions/meeting:one/resolve', json={'inspected': True}, headers=headers()).status_code == 422
    decision = {'inspected': True, 'action': 'continue', 'reason': 'Inspected the failure; try a new turn.'}
    assert client.post('/sessions/meeting:one/resolve', json=decision, headers=headers()).status_code == 200
    assert post(client, payload(prompt='fail')).status_code == 502
    events = client.get('/sessions/meeting:one/events', headers=headers()).json()
    assert any(item['event_type'] == 'retry_budget_exhausted' for item in events)
    assert 'credential secret' not in json.dumps(events)
    assert client.post('/sessions/meeting:one/resolve', json=decision, headers=headers()).status_code == 409
    assert post(client, payload()).status_code == 409
    assert len(calls(log)) == 2
    decision['reset_budget'] = True
    resolved = client.post('/sessions/meeting:one/resolve', json=decision, headers=headers())
    assert resolved.status_code == 200
    success = post(client, payload(prompt='recovered'))
    assert success.status_code == 200 and success.json()['thread_id'] == session['thread_id']
    assert client.get('/requests/' + first['request_id'], headers=headers()).json()['status'] == 'unknown'


def test_orphan_is_recovered_only_when_its_scope_lock_is_obtainable(broker):
    settings, client, _ = broker
    abandoned = uuid.uuid4()
    with module.db(settings) as connection:
        connection.execute('INSERT INTO sessions(scope,failure_budget) VALUES(%s,2)', ('meeting:abandoned',))
        connection.execute("INSERT INTO requests(id,scope,payload_hash,status,owner_token) VALUES(%s,%s,'old','running',%s)", (abandoned, 'meeting:abandoned', uuid.uuid4()))
    # New worker startup alone never sweeps potentially active work.
    with TestClient(module.create_app(settings)) as another:
        assert another.get('/requests/' + str(abandoned), headers=headers()).json()['status'] == 'running'
        assert post(another, payload(scope='meeting:abandoned')).status_code == 409
    old = client.get('/requests/' + str(abandoned), headers=headers()).json()
    assert old['status'] == 'unknown' and old['error_code'] == 'owner_disconnected'


def test_thread_id_cannot_be_reassigned_to_a_different_topic(broker):
    _, client, _ = broker
    original = post(client, payload()).json()['thread_id']
    conflict = post(client, payload(scope='meeting:different', prompt='reuse-thread:' + original))
    assert conflict.status_code == 502
    sessions = {item['scope']: item for item in client.get('/sessions', headers=headers()).json()}
    assert sessions['meeting:one']['thread_id'] == original
    assert sessions['meeting:different']['thread_id'] is None
    assert sessions['meeting:different']['blocked']


def test_timeout_retains_thread_and_never_auto_replays(broker):
    settings, _, log = broker
    bounded = module.Settings(**{**settings.__dict__, 'timeout': 1.0})
    with TestClient(module.create_app(bounded)) as client:
        data = payload(prompt='hang')
        started = time.monotonic()
        response = post(client, data)
        assert time.monotonic() - started < 4
        assert response.status_code == 502
        assert post(client, payload()).status_code == 409
        session = client.get('/sessions', headers=headers()).json()[0]
        assert session['thread_id'] is not None and session['blocked']
        assert client.get('/requests/' + data['request_id'], headers=headers()).json()['error_code'] == 'timeout'
    assert len(calls(log)) == 1


def test_auth_and_db_readiness_have_no_provider_or_local_storage_fallback(broker):
    settings, client, _ = broker
    assert client.get('/sessions').status_code == 401
    assert client.get('/requests/' + str(uuid.uuid4()), headers=headers()).status_code == 404
    health = client.get('/health').json()
    assert health['status'] == 'ok' and health['credential_file_present'] is False
    assert health['authentication_check'] == 'file_presence_only'
    absent = module.Settings(database_url='', token='test')
    with pytest.raises(RuntimeError, match='no local storage fallback'):
        with TestClient(module.create_app(absent)):
            pass


def raster(format='PNG', color='red'):
    output = io.BytesIO()
    Image.new('RGB', (2, 2), color).save(output, format=format)
    raw = output.getvalue()
    mime = {'PNG': 'image/png', 'JPEG': 'image/jpeg', 'WEBP': 'image/webp'}[format]
    return {'mime_type': mime, 'data_base64': base64.b64encode(raw).decode()}, raw


def test_decode_rasters_bounds_and_text_digest_are_offline(monkeypatch):
    for format in ('PNG', 'JPEG', 'WEBP'):
        wire, raw = raster(format)
        prepared = module.prepare_images([module.TurnImage(**wire)])[0]
        assert prepared.raw == raw and prepared.width == prepared.height == 2
        assert prepared.sha256 == hashlib.sha256(raw).hexdigest()
    text = module.Turn(**payload())
    old = hashlib.sha256(json.dumps({key: value for key, value in text.model_dump(mode='json').items() if key != 'images'}, sort_keys=True).encode()).hexdigest()
    assert module.request_digest(text, []) == old
    wire, _ = raster()
    monkeypatch.setattr(module, 'MAX_IMAGE_PIXELS', 1)
    with pytest.raises(module.HTTPException):
        module.prepare_images([module.TurnImage(**wire)])
    monkeypatch.setattr(module, 'MAX_IMAGE_PIXELS', 16_000_000)
    monkeypatch.setattr(module, 'MAX_TOTAL_IMAGE_BYTES', 1)
    with pytest.raises(module.HTTPException):
        module.prepare_images([module.TurnImage(**wire)])


def test_invalid_images_rejected_before_db_and_never_echo_base64(monkeypatch):
    def forbidden_db(*args, **kwargs):
        raise AssertionError('invalid image reached database')
    monkeypatch.setattr(module, 'scope_lock', forbidden_db)
    client = TestClient(module.create_app(module.Settings(database_url='', token='integration-test-only')))
    good, raw = raster()
    secret_marker = base64.b64encode(b'<svg>secret-image-content</svg>').decode()
    invalid = [
        [{'mime_type': 'image/svg+xml', 'data_base64': secret_marker}],
        [{'mime_type': 'image/png', 'data_base64': secret_marker}],
        [{'mime_type': 'image/png', 'data_base64': '../private/file'}],
        [{**good, 'path': '/private/file'}],
        [{**good, 'data_base64': 'data:image/png;base64,' + good['data_base64']}],
        [{**good, 'data_base64': base64.b64encode(raw[:30]).decode()}],
        [{**good, 'mime_type': 'image/jpeg'}],
        [good] * 4,
        [{**good, 'data_base64': 'A' * (module.MAX_IMAGE_BASE64 + 4)}],
        [{**good, 'data_base64': base64.b64encode(b'\x00' * (module.MAX_IMAGE_BYTES + 1)).decode()}],
    ]
    for images in invalid:
        response = post(client, {**payload(), 'images': images})
        assert response.status_code == 422
        assert secret_marker not in response.text and 'secret-image-content' not in response.text
    assert post(client, {**payload(), 'image_path': '/private/file'}).status_code == 422


def test_image_auth_preflight_does_not_claim_a_request(tmp_path, monkeypatch):
    def forbidden_db(*args, **kwargs):
        raise AssertionError('unauthenticated image turn reached database')
    monkeypatch.setattr(module, 'scope_lock', forbidden_db)
    client = TestClient(module.create_app(module.Settings(database_url='', token='integration-test-only', codex_home=str(tmp_path))))
    image, _ = raster()
    response = post(client, {**payload(), 'images': [image]})
    assert response.status_code == 503
    assert response.json()['detail']['status'] == 'not_started'
    assert response.json()['detail']['code'] == 'codex_authentication_required'


def test_temp_images_removed_even_if_process_cannot_start(tmp_path, monkeypatch):
    wire, raw = raster()
    prepared = module.prepare_images([module.TurnImage(**wire)])
    attached = []
    def unavailable(command, **kwargs):
        path = Path(command[command.index('--image') + 1])
        attached.append(path)
        assert path.read_bytes() == raw and path.stat().st_mode & 0o777 == 0o600
        assert command[-1] == '-'
        raise OSError('offline test: executable unavailable')
    monkeypatch.setattr(module.subprocess, 'Popen', unavailable)
    settings = module.Settings(database_url='', token='test', output_dir=str(tmp_path))
    with pytest.raises(OSError):
        module.run_codex(settings, module.Turn(**payload()), uuid.uuid4(), None, None, prepared)
    assert attached and all(not path.exists() and not path.parent.exists() for path in attached)


def test_image_exec_resume_receipts_and_uuid_conflict(broker):
    settings, client, log = broker
    # Synthetic marker in this test's private home; never uses real credentials.
    (Path(settings.codex_home) / 'auth.json').write_text('{}')
    red, red_raw = raster(color='red')
    blue, _ = raster(color='blue')
    first = {**payload(scope='design:images'), 'images': [red]}
    response = post(client, first)
    assert response.status_code == 200
    result = response.json()
    assert result['image_count'] == 1 and result['images'][0]['sha256'] == hashlib.sha256(red_raw).hexdigest()
    assert post(client, first).json() == result
    assert post(client, {**first, 'images': [blue]}).status_code == 409
    follow = post(client, {**payload(scope='design:images', prompt='followup'), 'images': [blue, red]})
    assert follow.status_code == 200 and follow.json()['thread_id'] == result['thread_id']
    recorded = calls(log)
    assert len(recorded) == 2
    assert 'resume' not in recorded[0]['args'] and 'resume' in recorded[1]['args']
    assert recorded[0]['args'][-2:] == ['--', '-']
    assert recorded[1]['args'][-3:] == ['--', result['thread_id'], '-']
    assert recorded[1]['args'][-2:] == [result['thread_id'], '-']
    for call in recorded:
        assert call['args'][-1] == '-'
        for image in call['images']:
            assert image['mode'] == 0o600
            assert not Path(image['path']).exists() and not Path(image['path']).parent.exists()
    assert len(recorded[1]['images']) == 2
    failed = post(client, {**payload(scope='design:image-failure', prompt='fail'), 'images': [red]})
    assert failed.status_code == 502
    assert all(not Path(image['path']).exists() for image in calls(log)[-1]['images'])
