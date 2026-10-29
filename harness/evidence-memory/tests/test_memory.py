import importlib.util
import json
import os
import uuid
from pathlib import Path
import urllib.request
import urllib.error
import pytest

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('evidence_memory_test', HERE / 'memory.py')
memory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(memory)


def test_roles_and_invalid_import_are_preserved():
    source = '\n'.join(json.dumps(x) for x in [
        {'id': 'u1', 'role': 'user', 'content': 'User synthetic correction'},
        {'id': 'a1', 'role': 'assistant', 'content': 'Assistant synthetic experiment'},
        {'role': 'system', 'content': 'Must not become user evidence'}])
    assert [x['role'] for x in memory.normalize(source, 'jsonl')] == ['user', 'assistant']
    class NoWrites:
        def execute(self, *args):
            raise AssertionError('Malformed JSONL must fail before a write')
    with pytest.raises(ValueError):
        memory.import_events(NoWrites(), source + '\ninvalid', 'synthetic', 'jsonl', 'test')


def test_excerpt_is_an_exact_source_substring():
    source = 'prefix ' * 200 + 'keyboard focus consequence' + ' suffix' * 200
    excerpt = memory.evidence_excerpt(source, ['keyboard focus'], 120)
    assert excerpt['text'] == source[excerpt['start']:excerpt['end']]
    assert 'keyboard focus' in excerpt['text'] and excerpt['truncated']


def test_secret_redaction():
    value = 'api_key=synthetic-secret-value password=synthetic-password-value'
    result = memory.redact(value)
    assert 'synthetic-secret-value' not in result and 'synthetic-password-value' not in result


@pytest.mark.skipif(not os.getenv('MEMORY_TEST_URL'), reason='Explicit synthetic integration service required')
def test_live_scope_idempotency_and_retrieval_correction():
    base = os.environ['MEMORY_TEST_URL'].rstrip('/')
    token = os.environ['MEMORY_API_TOKEN']
    def request(path, body=None, authenticate=True):
        headers = {'Authorization': 'Bearer ' + token} if authenticate else {}
        if body is not None:
            headers['Content-Type'] = 'application/json'
        req = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.load(response)
    assert request('/health', authenticate=False)['status'] == 'ok'
    with pytest.raises(urllib.error.HTTPError) as error:
        request('/api/memory/search?q=synthetic', authenticate=False)
    assert error.value.code == 401
    scope = {'project': 'synthetic-' + uuid.uuid4().hex, 'topic': 'packaging-test', 'purpose': 'verification'}
    body = {**scope, 'source': 'synthetic-public-packaging-test', 'format': 'jsonl',
            'text': json.dumps({'id': 'synthetic-message', 'role': 'assistant', 'content': 'synthetic keyboard focus recovery'})}
    added = request('/api/memory/import', body)
    assert added['added'] == 1 and request('/api/memory/import', body)['added'] == 0
    path = '/api/memory/search?q=keyboard&project=' + scope['project'] + '&topic=packaging-test&purpose=verification'
    found = request(path)
    assert len(found) == 1 and found[0]['role'] == 'assistant'
    assert request('/api/memory/search?q=keyboard&project=' + uuid.uuid4().hex) == []
    feedback = {**scope, 'evidence_id': found[0]['id'], 'kind': 'suppress', 'reason': 'Synthetic excluded cause'}
    request('/api/memory/retrieval-feedback', feedback)
    assert request(path) == []
    feedback.update(kind='unsuppress', reason='Synthetic restore decision')
    request('/api/memory/retrieval-feedback', feedback)
    assert len(request(path)) == 1
    feedback.update(kind='correct', reason='Synthetic scoped correction', correction='Synthetic corrected meaning')
    request('/api/memory/retrieval-feedback', feedback)
    assert request(path)[0]['correction'] == 'Synthetic corrected meaning'
