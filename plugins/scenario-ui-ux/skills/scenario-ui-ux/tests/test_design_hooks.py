"""Offline contract/gate tests; no real provider calls or original user data."""
import base64
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import struct
import unittest
import uuid
import zlib
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


hook = load('hook_under_test', 'design-hook.py')
audit = hook.audit_module
installer = load('install_under_test', 'install-design-hooks.py')
def chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)


PNG = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 6, 0, 0, 0)) +
       chunk(b'IDAT', zlib.compress(b'\x00\xff\xff\xff\xff')) + chunk(b'IEND', b''))


def visual_reply(payload, **changes):
    context = json.loads(payload['prompt'].split('\n', 1)[1])
    ids = [item['id'] for item in context['evidence'] if item['kind'] == 'image']
    receipts = []
    for image in payload['images']:
        raw = base64.b64decode(image['data_base64'], validate=True)
        width, height = struct.unpack('>II', raw[16:24])
        receipts.append({'mime_type': image['mime_type'], 'sha256': hashlib.sha256(raw).hexdigest(), 'width': width, 'height': height})
    review = {'status': 'pass', 'checked_evidence': ['O1', 'S1', *ids], 'observations': [],
              'preference_status': 'not_reviewed', 'visual_coverage': 'inspected_supplied_images'}
    review.update(changes)
    return {'scope': payload['scope'], 'request_id': payload['request_id'], 'status': 'completed',
            'text': json.dumps(review), 'image_count': len(receipts), 'images': receipts}


class HooksTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name).resolve()
        self.css = ':root {--ink: #222222;--space: 8px;--font: 16px;--round: 10px;}\n.input {color:var(--ink);padding:var(--space);font-size:var(--font);border-radius:var(--round);}\n'
        (self.project / 'style.css').write_text(self.css)
        (self.project / 'index.html').write_text('<input class="input" aria-label="Title">')
        self.narrative = '# Task\n\nAdd and save a task. Preserve the praised feedback dialog.\n'
        self.contract = {'format': audit.FORMAT, 'task_id': 'task-1',
            'design': {'path': 'DESIGN.md', 'sha256': audit.design_hash(self.narrative)},
            'scope': {'paths': ['style.css', 'index.html'], 'allow': []},
            'tokens': {'color': {'--ink': '#222222'}, 'spacing': {'--space': '8px'},
                       'typography': {'--font': '16px'}, 'radius': {'--round': '10px'}},
            'shapes': [{'path': 'style.css', 'selector': '.input', 'radius': '--round', 'role': 'input', 'reason': 'Shared input geometry.'}],
            'checks': {'browser': {'required': True, 'argv': [sys.executable, 'browser.py'], 'timeout': 5,
                                   'input_paths': ['browser.py'],
                                   'record': '.design-audit/browser/observation.json'},
                       'critique': {'enabled': False, 'required': False}}, 'max_repairs': 2}
        self.browser_source = '''from pathlib import Path
import hashlib,json,base64
root=Path('.design-audit/browser');root.mkdir(parents=True,exist_ok=True)
path=root/'after.png';path.write_bytes(base64.b64decode(PNG))
count=Path('.design-audit/count');count.write_text(str(int(count.read_text())+1) if count.exists() else '1')
record={'format':'scenario-browser-observation/v1','status':'pass','task':'Add task','expected':'Dialog opens and save adds row','observed':'Dialog opened and saved fixture row','screenshots':[{'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}]}
(root/'observation.json').write_text(json.dumps(record))
'''.replace('PNG', repr(base64.b64encode(PNG).decode()))
        (self.project / 'browser.py').write_text(self.browser_source)
        self.seal()

    def seal(self):
        raw = (json.dumps(self.contract, indent=2) + '\n').encode()
        (self.project / 'design-contract.json').write_bytes(raw)
        (self.project / 'DESIGN.md').write_text(self.narrative + '\n<!-- design-contract: design-contract.json sha256:' + audit.digest(raw) + ' -->\n')

    def run_gate(self, **kwargs):
        return hook.pipeline(self.project, **kwargs)

    def test_good_gate_executes_once_and_preserves_source(self):
        before = {name: (self.project / name).read_bytes() for name in ('style.css', 'index.html', 'DESIGN.md', 'design-contract.json')}
        report = self.run_gate()
        self.assertEqual(report['status'], 'pass')
        self.assertEqual(report['stages']['browser']['status'], 'pass')
        self.assertEqual(report['stages']['critique']['status'], 'not_run')
        self.assertEqual(report['preference_status'], 'not_reviewed')
        self.assertTrue(self.run_gate()['cached'])
        self.assertEqual((self.project / '.design-audit/count').read_text(), '1')
        self.assertEqual(before, {name: (self.project / name).read_bytes() for name in before})

    def test_browser_runs_preserve_old_pixels_and_records_after_new_run(self):
        first = self.run_gate()['stages']['browser']
        folder = self.project / first['browser_run_path']
        snapshot = {path: path.read_bytes() for path in folder.iterdir()}
        alternate = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 6, 0, 0, 0)) +
                     chunk(b'IDAT', zlib.compress(b'\x00\x00\x00\x00\xff')) + chunk(b'IEND', b''))
        (self.project / 'browser.py').write_text(self.browser_source.replace(base64.b64encode(PNG).decode(), base64.b64encode(alternate).decode()))
        second = self.run_gate()['stages']['browser']
        self.assertNotEqual(first['browser_run_path'], second['browser_run_path'])
        self.assertEqual(snapshot, {path: path.read_bytes() for path in folder.iterdir()})
        self.assertEqual((self.project / first['record']['screenshots'][0]['path']).read_bytes(), PNG)
        self.assertEqual((self.project / second['record']['screenshots'][0]['path']).read_bytes(), alternate)
        self.assertEqual((self.project / '.design-audit/browser/after.png').read_bytes(), alternate)
        # A producer's mutable staging files are no longer the report's evidence.
        (self.project / '.design-audit/browser/after.png').write_bytes(b'producer overwrote staging')
        (self.project / '.design-audit/browser/observation.json').write_text('{}')
        self.assertTrue(self.run_gate()['cached'])
        self.assertTrue(hook.browser_evidence_current(self.project / '.design-audit', first))
        images, _, _ = hook.visual_attachments(self.project, first)
        self.assertEqual(base64.b64decode(images[0]['data_base64']), PNG)

    def test_failed_browser_record_is_preserved_and_tamper_checked(self):
        (self.project / 'browser.py').write_text(self.browser_source.replace("'status':'pass'", "'status':'fail'"))
        report = self.run_gate()
        browser = report['stages']['browser']
        self.assertEqual(browser['status'], 'fail')
        self.assertEqual(browser['archive_status'], 'preserved')
        self.assertEqual(json.loads((self.project / browser['record_path']).read_text())['status'], 'fail')
        path = self.project / browser['archive_provenance']['original_record_copy']
        path.write_bytes(path.read_bytes() + b' ')
        with self.assertRaisesRegex(audit.AuditError, 'cached_browser'):
            self.run_gate()

    def test_archive_does_not_make_stale_producer_evidence_fresh(self):
        root = hook.artifact_root(self.project)
        first = hook.browser_stage(self.project, root, self.contract['checks']['browser'])
        before = list((root / 'browser-runs').iterdir())
        (self.project / 'browser.py').write_text('pass')
        os.utime(self.project / '.design-audit/browser/observation.json', (1, 1))
        stale = hook.browser_stage(self.project, root, self.contract['checks']['browser'])
        self.assertEqual(stale['status'], 'fail')
        self.assertEqual(list((root / 'browser-runs').iterdir()), before)
        self.assertTrue(hook.browser_evidence_current(root, first))

    def test_archive_symlink_directory_and_run_collision_refuse_overwrite(self):
        root = hook.artifact_root(self.project)
        outside = self.project / 'outside';outside.mkdir()
        (root / 'browser-runs').symlink_to(outside, target_is_directory=True)
        refused = hook.browser_stage(self.project, root, self.contract['checks']['browser'])
        self.assertEqual(refused['status'], 'fail')
        self.assertEqual(list(outside.iterdir()), [])
        (root / 'browser-runs').unlink()
        with patch.object(hook.uuid, 'uuid4', return_value=uuid.UUID(int=0)):
            first = hook.browser_stage(self.project, root, self.contract['checks']['browser'])
            folder = self.project / first['browser_run_path']
            snapshot = {path: path.read_bytes() for path in folder.iterdir()}
            collision = hook.browser_stage(self.project, root, self.contract['checks']['browser'])
        self.assertEqual(first['status'], 'pass')
        self.assertEqual(collision['status'], 'fail')
        self.assertEqual(collision['archive_status'], 'incomplete')
        self.assertEqual(snapshot, {path: path.read_bytes() for path in folder.iterdir()})

    def test_archive_file_creation_is_exclusive_and_rejects_links(self):
        root = hook.artifact_root(self.project)
        run = hook.new_browser_run(root)
        path = hook.append_artifact_bytes(root, run + '/kept.bin', b'first')
        with self.assertRaises(FileExistsError):
            hook.append_artifact_bytes(root, run + '/kept.bin', b'second')
        self.assertEqual(path.read_bytes(), b'first')
        outside = self.project / 'untouched.bin';outside.write_bytes(b'original')
        (root / run / 'linked.bin').symlink_to(outside)
        with self.assertRaises(audit.AuditError):
            hook.append_artifact_bytes(root, run + '/linked.bin', b'changed')
        self.assertEqual(outside.read_bytes(), b'original')

    def test_changed_source_during_copy_keeps_partial_archive_without_promotion(self):
        (self.project / 'browser.py').write_text(self.browser_source.replace("'screenshots':[", "'screenshots':2*["))
        append = hook.append_artifact_bytes
        def change_after_first_copy(root, relative, raw):
            path = append(root, relative, raw)
            if relative.endswith('screenshot-001.png'):
                (self.project / '.design-audit/browser/after.png').write_bytes(b'changed after initial validation')
            return path
        with patch.object(hook, 'append_artifact_bytes', side_effect=change_after_first_copy):
            report = self.run_gate()
        browser = report['stages']['browser']
        self.assertEqual(browser['status'], 'fail')
        self.assertEqual(browser['archive_status'], 'incomplete')
        folder = self.project / browser['browser_run_path']
        self.assertTrue((folder / 'source-record.json').is_file())
        self.assertEqual((folder / 'screenshot-001.png').read_bytes(), PNG)
        self.assertFalse((folder / 'screenshot-002.png').exists())
        self.assertFalse((folder / 'observation.json').exists())

    def test_contract_and_human_hash_drift_fail(self):
        (self.project / 'DESIGN.md').write_text((self.project / 'DESIGN.md').read_text().replace('Add and save', 'Delete'))
        with self.assertRaisesRegex(audit.AuditError, 'narrative_hash'):
            self.run_gate()
        self.seal()
        (self.project / 'design-contract.json').write_text('{}')
        with self.assertRaisesRegex(audit.AuditError, 'file_hash'):
            self.run_gate()

    def test_new_color_blocked_scoped_legacy_allowed(self):
        (self.project / 'style.css').write_text(self.css + '.old {color: #123456;}')
        self.contract['scope']['allow'] = [{'path': 'style.css', 'rule': 'color', 'values': ['#123456'], 'reason': 'Legacy scoped value.'}]
        self.seal()
        self.assertEqual(audit.audit(self.project)[0]['status'], 'pass')
        (self.project / 'style.css').write_text(self.css + '.old {color: #123456; background: #fe0102;}')
        report = audit.audit(self.project)[0]
        self.assertEqual(report['status'], 'fail')
        self.assertIn('#fe0102', str(report['findings']))
        (self.project / 'style.css').write_text(self.css + '.new {color: rebeccapurple;}')
        self.assertEqual(audit.audit(self.project)[0]['status'], 'fail')

    def test_shape_accepts_matching_token_fallback(self):
        (self.project / 'style.css').write_text(self.css.replace('var(--round)', 'var(--round, 10px)'))
        self.contract['scope']['allow'] = [{'path': 'style.css', 'rule': 'radius', 'values': ['10px'], 'reason': 'Matching fallback.'}]
        self.seal()
        report, _, _ = audit.audit(self.project)
        self.assertEqual(report['status'], 'pass', report)

    def test_shape_rejects_different_token_fallback(self):
        (self.project / 'style.css').write_text(self.css.replace('var(--round)', 'var(--round, 99px)'))
        self.contract['scope']['allow'] = [{'path': 'style.css', 'rule': 'radius', 'values': ['99px'], 'reason': 'Must still fail the role geometry.'}]
        self.seal()
        report, _, _ = audit.audit(self.project)
        self.assertTrue(any(item['rule'] == 'shape' for item in report['findings']))

    def test_radius_shape_and_syntax_fail(self):
        (self.project / 'style.css').write_text(self.css.replace('var(--round)', '4px'))
        self.assertEqual(audit.audit(self.project)[0]['status'], 'fail')
        (self.project / 'style.css').write_text(self.css + '.broken {')
        self.assertIn('unbalanced_css_structure', str(audit.audit(self.project)[0]))

    def test_percentage_literals_and_fake_png_are_rejected(self):
        (self.project / 'style.css').write_text(self.css + '.bad {margin:25%; border-radius:50%;}')
        report = audit.audit(self.project)[0]
        self.assertEqual(report['status'], 'fail')
        self.assertIn('25%', str(report))
        self.assertIn('50%', str(report))
        self.assertFalse(hook.valid_png(b'\x89PNG\r\n\x1a\n' + b'x' * 24))
        self.assertTrue(hook.valid_png(PNG))

    def test_jsx_and_unconfigured_tailwind_do_not_silently_pass(self):
        path = self.project / 'view.tsx'
        self.contract['utility_classes'] = {'enabled': True}
        path.write_text('<div style={{color: "#fff"}} className="p-4 text-red-500" />')
        self.contract['scope']['paths'].append('view.tsx');self.seal()
        report = audit.audit(self.project)[0]
        self.assertEqual(report['status'], 'fail')
        self.assertIn('unsupported_style_syntax', str(report))
        path.write_text('<div className="p-4 text-red-500" />')
        self.contract['utility_classes'] = {'enabled': True, 'spacing': ['p-4'], 'color': ['text-red-500']};self.seal()
        self.assertEqual(audit.audit(self.project)[0]['status'], 'pass')

    def test_vanilla_class_is_not_tailwind_and_arbitrary_tailwind_is_blocked(self):
        (self.project / 'index.html').write_text('<button class="text-button">Save</button>')
        self.assertEqual(audit.audit(self.project)[0]['status'], 'pass')
        self.contract['utility_classes'] = {'enabled': True};self.seal()
        (self.project / 'index.html').write_text('<button class="bg-[#ff0000]">Save</button>')
        self.assertEqual(audit.audit(self.project)[0]['status'], 'fail')

    def test_evidence_only_js_invalidates_cache_without_css_claim(self):
        (self.project / 'controls.js').write_text('node.style.left = "0px";')
        self.contract['scope']['evidence_paths'] = ['controls.js'];self.seal()
        first = self.run_gate()
        self.assertEqual(first['status'], 'pass')
        self.assertEqual(first['stages']['static']['evidence_only_paths'], ['controls.js'])
        (self.project / 'controls.js').write_text('node.style.left = "1px";')
        second = self.run_gate()
        self.assertNotEqual(first['fingerprint'], second['fingerprint'])
        self.assertEqual((self.project / '.design-audit/count').read_text(), '2')

    def test_required_not_run_is_failure_no_live_broker(self):
        self.contract['checks']['critique'] = {'enabled': True, 'required': True};self.seal()
        with patch.dict(os.environ, {'BROKER_URL': '', 'BROKER_TOKEN': ''}):
            report = self.run_gate()
        self.assertEqual(report['status'], 'fail')
        self.assertEqual(report['stages']['critique']['status'], 'not_run')
        self.assertEqual(report['next_action'], 'needs_user')
        self.assertEqual(self.run_gate()['next_action'], 'needs_user')

    def test_fake_broker_sees_design_and_validates_evidence(self):
        self.contract['checks']['critique'] = {'enabled': True, 'required': True};self.seal()
        requests = []
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return None
            def read(self, limit): return self.body
        class Opener:
            def open(self, request, timeout):
                payload = json.loads(request.data);requests.append(payload)
                review = {'status': 'pass', 'checked_evidence': ['O1', 'S1'], 'observations': [],
                          'preference_status': 'not_reviewed', 'visual_coverage': 'not_inspected'}
                result = Response();result.body = json.dumps({**payload, 'status': 'completed', 'text': json.dumps(review)}).encode()
                return result
        with patch.dict(os.environ, {'BROKER_URL': 'http://localhost:8030', 'BROKER_TOKEN': 'fake-test-only'}), patch.object(hook.urllib.request, 'build_opener', return_value=Opener()):
            report = self.run_gate()
        self.assertEqual(report['status'], 'pass')
        self.assertEqual(len(requests), 1)
        context = json.loads(requests[0]['prompt'].split('\n', 1)[1])
        self.assertIn(self.narrative.strip(), context['design_agreement'])
        self.assertIn('machine_contract', requests[0]['prompt'])
        self.assertIn('Token audit pass is NOT UX pass', requests[0]['prompt'])
        self.assertNotIn('fake-test-only', requests[0]['prompt'])

    def test_visual_critique_forwards_pixels_ids_and_hash_receipt(self):
        (self.project / 'browser.py').write_text(self.browser_source.replace("'screenshots':[", "'screenshots':3*["))
        self.contract['checks']['critique'] = {'enabled': True, 'required': True, 'require_visual': True};self.seal()
        requests = []
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return None
            def read(self, limit): return self.body
        class Opener:
            def open(self, request, timeout):
                payload = json.loads(request.data);requests.append(payload)
                result = Response();result.body = json.dumps(visual_reply(payload)).encode()
                return result
        with patch.dict(os.environ, {'BROKER_URL': 'http://localhost:8030', 'BROKER_TOKEN': 'fake-test-only'}), patch.object(hook.urllib.request, 'build_opener', return_value=Opener()):
            report = self.run_gate()
        self.assertEqual(report['status'], 'pass')
        self.assertEqual(len(requests), 1)
        self.assertEqual(base64.b64decode(requests[0]['images'][0]['data_base64']), PNG)
        self.assertEqual(len(requests[0]['images']), 3)
        context = json.loads(requests[0]['prompt'].split('\n', 1)[1])
        image = next(item for item in context['evidence'] if item['id'] == 'I1')
        self.assertEqual(image['sha256'], hashlib.sha256(PNG).hexdigest())
        self.assertIn('recorded_behavior', requests[0]['prompt'])
        self.assertIn('source_inference', requests[0]['prompt'])
        self.assertNotIn(requests[0]['images'][0]['data_base64'], requests[0]['prompt'])
        self.assertEqual(report['stages']['critique']['images'][0]['sha256'], image['sha256'])
        self.assertEqual(report['stages']['critique']['image_count'], 3)
        self.assertTrue({'I1', 'I2', 'I3'} <= set(report['stages']['critique']['review']['checked_evidence']))
        self.assertNotIn('data_base64', json.dumps(report))
        self.assertEqual((self.project / image['path']).read_bytes(), PNG)

    def test_visual_invalid_or_changed_images_never_contact_broker(self):
        self.contract['checks']['critique'] = {'enabled': True, 'required': True, 'require_visual': True};self.seal()
        _, contract, files = audit.audit(self.project)
        root = hook.artifact_root(self.project)
        browser = hook.browser_stage(self.project, root, contract['checks']['browser'])
        self.assertEqual(browser['status'], 'pass')
        (self.project / browser['record']['screenshots'][0]['path']).write_bytes(b'not a PNG')
        with patch.object(hook.urllib.request, 'build_opener', side_effect=AssertionError('invalid pixels were sent')):
            result = hook.critique_stage(self.project, contract, files, browser, 'image-case')
        self.assertEqual(result['status'], 'not_run')
        self.assertEqual(result['reason'], 'visual_images_missing_invalid_or_changed')

    def test_visual_review_cannot_pass_without_receipt_coverage_and_image_ids(self):
        self.contract['checks']['critique'] = {'enabled': True, 'required': True, 'require_visual': True};self.seal()
        _, contract, files = audit.audit(self.project)
        browser = hook.browser_stage(self.project, hook.artifact_root(self.project), contract['checks']['browser'])
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return None
            def read(self, limit): return self.body
        for mode in ('receipt', 'boolean_receipt', 'coverage', 'image_ids', 'unproven_image_claim', 'inconclusive'):
            class Opener:
                def open(self, request, timeout):
                    payload = json.loads(request.data)
                    if mode == 'coverage':
                        result = visual_reply(payload, visual_coverage='inconclusive')
                    elif mode == 'image_ids':
                        result = visual_reply(payload, checked_evidence=['O1', 'S1'])
                    elif mode == 'unproven_image_claim':
                        result = visual_reply(payload, observations=[{'issue':'Invisible state','basis':'image_observation','evidence_ids':['S1'],'reason':'source only','suggested_change':'unproven'}])
                    elif mode == 'inconclusive':
                        result = visual_reply(payload, status='inconclusive', visual_coverage='inconclusive')
                    elif mode == 'boolean_receipt':
                        result = visual_reply(payload);result['image_count'] = True;result['images'][0]['width'] = True
                    else:
                        result = visual_reply(payload);result['images'][0]['sha256'] = '0' * 64
                    response = Response();response.body = json.dumps(result).encode();return response
            with patch.dict(os.environ, {'BROKER_URL': 'http://localhost:8030', 'BROKER_TOKEN': 'fake-test-only'}), patch.object(hook.urllib.request, 'build_opener', return_value=Opener()):
                result = hook.critique_stage(self.project, contract, files, browser, 'case-' + mode)
            self.assertNotEqual(result['status'], 'pass', mode)
            if mode == 'inconclusive':
                self.assertEqual(result['review']['visual_coverage'], 'inconclusive')
            else:
                self.assertTrue(result['requires_user_decision'])

    def test_visual_required_without_credentials_fails_gate(self):
        self.contract['checks']['critique'] = {'enabled': True, 'required': True, 'require_visual': True};self.seal()
        with patch.dict(os.environ, {'BROKER_URL': '', 'BROKER_TOKEN': ''}):
            report = self.run_gate()
        self.assertEqual(report['status'], 'fail')
        self.assertEqual(report['stages']['critique']['status'], 'not_run')
        self.assertEqual(report['next_action'], 'needs_user')

    def test_visual_auth_not_started_is_distinct_from_unknown_completion(self):
        self.contract['checks']['critique'] = {'enabled': True, 'required': True, 'require_visual': True};self.seal()
        class Opener:
            def open(self, request, timeout):
                body = json.dumps({'detail': {'status': 'not_started', 'code': 'codex_authentication_required'}}).encode()
                raise hook.urllib.error.HTTPError(request.full_url, 503, 'not started', {}, io.BytesIO(body))
        with patch.dict(os.environ, {'BROKER_URL': 'http://localhost:8030', 'BROKER_TOKEN': 'fake-test-only'}), patch.object(hook.urllib.request, 'build_opener', return_value=Opener()):
            report = self.run_gate()
        critique = report['stages']['critique']
        self.assertEqual(critique['reason'], 'broker_authentication_not_ready')
        self.assertFalse(critique['request_started'])
        self.assertNotIn('requires_user_decision', critique)
        self.assertEqual(report['status'], 'fail')
        self.assertEqual(report['repairs_requested'], 0)

    def test_personal_policy_checks_both_adopt_reject_and_stale(self):
        raw = {'format': 'da-development-decisions/v1', 'source': {'event_watermark': 2, 'latest_decision_count': 2},
               'decisions': [{'rule_id': 'a', 'event_id': 1, 'revision': 1, 'decision': 'adopt', 'reason': 'Keep shared controls'},
                             {'rule_id': 'b', 'event_id': 2, 'revision': 1, 'decision': 'reject', 'reason': 'Reject blanket exclusion'}]}
        applied = {'format': 'da-development-application/v1', 'source_event_watermark': 2,
                   'applications': [{'rule_id': row['rule_id'], 'source_event_id': row['event_id'], 'source_revision': 1,
                                     'decision': row['decision'], 'scope': 'Same role only', 'applied_behavior': row['reason'],
                                     'reference': 'personal-ui.md'} for row in raw['decisions']]}
        paths = [self.project / name for name in ('decisions.json', 'applications.json')]
        for path, data in zip(paths, (raw, applied)): path.write_text(json.dumps(data))
        original = [path.read_bytes() for path in paths]
        self.contract['policy'] = {'decisions': 'decisions.json', 'applications': 'applications.json', 'required': True};self.seal()
        report = audit.audit(self.project)[0]
        self.assertEqual(report['policy']['status'], 'pass')
        self.assertEqual(report['policy']['count'], 2)
        self.assertEqual(original, [path.read_bytes() for path in paths])
        applied['applications'][1]['source_revision'] = 0
        paths[1].write_text(json.dumps(applied))
        self.assertEqual(audit.audit(self.project)[0]['status'], 'fail')

    def test_stop_reentry_no_change_stops_without_extra_attempt(self):
        (self.project / 'style.css').write_text(self.css + '.bad {color:#ff0000;}')
        first = self.run_gate(event='Stop')
        second = self.run_gate(event='Stop', stop_active=True)
        self.assertEqual(first['repairs_requested'], second['repairs_requested'])
        output = hook.hook_output(second, 'Stop')
        self.assertFalse(output['continue'])
        self.assertNotIn('decision', output)

    def test_budget_persists_no_id_reset_and_user_resolution_retains_history(self):
        for index in range(3):
            (self.project / 'style.css').write_text(self.css + f'.bad {{color: #12345{index};}}')
            report = self.run_gate()
            self.assertEqual(report['repairs_requested'], min(index + 1, 2))
        self.assertEqual(report['next_action'], 'needs_user')
        self.contract['task_id'] = 'new-alias';self.seal()
        with self.assertRaisesRegex(audit.AuditError, 'task_id_changed'):
            self.run_gate()
        self.contract['task_id'] = 'task-1';self.seal()
        hook.resolve_after_user_decision(self.project, None, 'User requested another inspected attempt.', 'conversation:event-99', 2)
        (self.project / 'style.css').write_text(self.css)
        self.assertEqual(self.run_gate()['status'], 'pass')
        state = json.loads((self.project / '.design-audit/state.json').read_text())
        retained = next(iter(state['tasks'].values()))
        self.assertEqual(retained['generation'], 1)
        self.assertEqual(retained['resolutions'][0]['previous_repairs_requested'], 2)

    def test_unresolved_task_cannot_rename_and_edit_narrative(self):
        (self.project / 'style.css').write_text(self.css + '.bad {color:#ff0000;}')
        self.run_gate()
        self.narrative += '\nReworded task.\n'
        self.contract['design']['sha256'] = audit.design_hash(self.narrative)
        self.contract['task_id'] = 'alias';self.seal()
        with self.assertRaisesRegex(audit.AuditError, 'unresolved_active'):
            self.run_gate()
        hook.activate_after_user_decision(self.project, None, 'User explicitly moved to a new task.', 'conversation:event-100')
        self.assertEqual(self.run_gate()['repairs_requested'], 1)

    def test_cache_tampering_and_missing_capture_fail(self):
        first = self.run_gate()
        (self.project / first['stages']['browser']['record']['screenshots'][0]['path']).unlink()
        with self.assertRaisesRegex(audit.AuditError, 'cached_browser'):
            self.run_gate()
        # Regenerate in a separate task/project to isolate managed state.
        self.tmp.cleanup();self.setUp()
        self.run_gate()
        state = json.loads((self.project / '.design-audit/state.json').read_text())
        entry = next(iter(state['tasks'].values()))
        path = self.project / '.design-audit' / entry['report']
        body = json.loads(path.read_text());body['status'] = 'fail';path.write_text(json.dumps(body))
        with self.assertRaisesRegex(audit.AuditError, 'cached_report_hash'):
            self.run_gate()

    def test_missing_record_and_process_failure_not_pass(self):
        (self.project / 'browser.py').write_text('pass')
        report = self.run_gate()
        self.assertEqual(report['stages']['browser']['status'], 'fail')
        self.assertEqual(report['status'], 'fail')

    def test_command_implementation_change_invalidates_cached_pass(self):
        self.assertEqual(self.run_gate()['status'], 'pass')
        (self.project / 'browser.py').write_text('raise RuntimeError("broken test implementation")')
        report = self.run_gate()
        self.assertNotEqual(report['status'], 'pass')
        self.assertEqual(report['stages']['browser']['status'], 'fail')

    def test_new_static_failure_never_promoted_from_cached_success(self):
        self.assertEqual(self.run_gate()['status'], 'pass')
        original = hook.audit_module.audit
        def changed_audit(*args, **kwargs):
            report, contract, files = original(*args, **kwargs)
            report['status'] = 'fail'
            report['findings'].append({'rule': 'new_guard', 'reason': 'new violation discovered'})
            return report, contract, files
        with patch.object(hook.audit_module, 'audit', side_effect=changed_audit):
            report = self.run_gate()
        self.assertEqual(report['status'], 'fail')
        self.assertEqual(report['stages']['static']['status'], 'fail')

    def test_nested_schema_and_host_array_return_json_failure(self):
        self.contract['tokens']['extra'] = [];self.seal()
        command = [sys.executable, str(ROOT / 'scripts/design-hook.py'), '--project', str(self.project)]
        result = subprocess.run(command, input='[]', capture_output=True, text=True)
        self.assertEqual(result.stderr, '')
        self.assertIn('needs_user', json.loads(result.stdout)['stopReason'])
        result = subprocess.run(command + ['--event', 'CI'], capture_output=True, text=True)
        self.assertEqual(result.stderr, '')
        self.assertEqual(json.loads(result.stdout)['status'], 'fail')

    def test_output_symlink_shell_and_unmanaged_overwrite_rejected(self):
        outside = self.project / 'untouched';outside.mkdir()
        (self.project / '.design-audit').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(audit.AuditError):
            self.run_gate()
        self.assertEqual(list(outside.iterdir()), [])
        (self.project / '.design-audit').unlink()
        self.contract['checks']['browser']['argv'] = ['sh', '-c', 'echo unsafe'];self.seal()
        with self.assertRaisesRegex(audit.AuditError, 'shell_or_env'):
            self.run_gate()

    def test_invalid_json_shape_fails_cli_as_json(self):
        self.contract['scope'] = []
        self.seal()
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/design-hook.py'), '--project', str(self.project), '--event', 'CI'], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)['status'], 'fail')
        self.assertEqual(result.stderr, '')

    def test_installer_bootstraps_owned_artifacts_and_preserves_later_budget_and_observations(self):
        report = installer.install(self.project)
        root = self.project / '.design-audit'
        marker = root / 'managed.json'
        self.assertTrue(marker.is_file(), 'A successful first install must initialize artifact ownership')
        self.assertEqual(json.loads(marker.read_text()), {'format': hook.ROOT_FORMAT})
        self.assertEqual([path.name for path in root.iterdir()], ['managed.json'])
        self.assertEqual(report['trust'], 'pending_host_review')
        # A real unit gate failure consumes one repair and retains browser artifacts.
        # Reinstalling must neither rerun the gate nor reset its budget or evidence.
        (self.project / 'browser.py').write_text(self.browser_source.replace("'status':'pass'", "'status':'fail'"))
        failed = self.run_gate()
        self.assertEqual(failed['status'], 'fail')
        self.assertEqual(failed['repairs_requested'], 1)
        before = {str(path.relative_to(self.project)): (path.read_bytes(), path.stat().st_mtime_ns)
                  for directory in (root, self.project / '.design-hooks', self.project / '.claude', self.project / '.codex')
                  for path in directory.rglob('*') if path.is_file()}
        installer.install(self.project)
        after = {str(path.relative_to(self.project)): (path.read_bytes(), path.stat().st_mtime_ns)
                 for directory in (root, self.project / '.design-hooks', self.project / '.claude', self.project / '.codex')
                 for path in directory.rglob('*') if path.is_file()}
        self.assertEqual(after, before)

    def test_installer_rejects_nonempty_unmanaged_artifacts_before_output_changes(self):
        root = self.project / '.design-audit'
        (root / 'browser').mkdir(parents=True)
        observed = root / 'browser' / 'observation.json'
        observed.write_bytes(b'{"unclaimed":"retained observation"}\n')
        (self.project / '.claude').mkdir()
        (self.project / '.codex').mkdir()
        claude = self.project / '.claude/settings.json'
        codex = self.project / '.codex/hooks.json'
        claude.write_text('{"permissions":{"allow":["Read"]}}\n')
        codex.write_text('{"hooks":{}}\n')
        before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in (observed, claude, codex)}
        with self.assertRaisesRegex(installer.hook.AuditError, 'nonempty_unmanaged_artifact_directory'):
            installer.install(self.project)
        self.assertEqual(before, {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in before})
        self.assertFalse((root / 'managed.json').exists())
        self.assertFalse((self.project / '.design-hooks').exists())

    def test_installer_rejects_symlink_artifacts_before_output_changes(self):
        outside = self.project / 'external-artifacts'
        outside.mkdir()
        sentinel = outside / 'retained.txt'
        sentinel.write_bytes(b'external evidence must remain unchanged\n')
        (self.project / '.design-audit').symlink_to(outside, target_is_directory=True)
        (self.project / '.claude').mkdir()
        settings = self.project / '.claude/settings.json'
        settings.write_text('{"permissions":{"allow":["Read"]}}\n')
        before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in (sentinel, settings)}
        with self.assertRaisesRegex(installer.hook.AuditError, 'symlink_artifact_root'):
            installer.install(self.project)
        self.assertEqual(before, {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in before})
        self.assertEqual([path.name for path in outside.iterdir()], ['retained.txt'])
        self.assertFalse((self.project / '.design-hooks').exists())
        self.assertFalse((self.project / '.codex').exists())

    def test_installer_config_preflight_failure_creates_no_artifact_root(self):
        (self.project / '.claude').mkdir()
        settings = self.project / '.claude/settings.json'
        settings.write_text(json.dumps({'hooks': {'Stop': [{'hooks': [{'type': 'command',
            'command': '.design-hooks/design-hook.py --unmanaged'}]}]}}))
        before = settings.read_bytes()
        with self.assertRaisesRegex(installer.hook.AuditError, 'conflicting_managed_design_hook'):
            installer.install(self.project)
        self.assertEqual(settings.read_bytes(), before)
        self.assertFalse((self.project / '.design-audit').exists())
        self.assertFalse((self.project / '.design-hooks').exists())
        self.assertFalse((self.project / '.codex').exists())

    def test_installed_adoption_guidance_is_preserved_and_tampering_blocks_reinstall(self):
        installer.install(self.project)
        guidance = self.project / '.design-hooks/references/reference-adoption.md'
        self.assertTrue(guidance.is_file(), 'New adoption guidance must reach installed hooks')
        manifest = json.loads((self.project / '.design-hooks/managed.json').read_text())
        self.assertEqual(manifest['references']['reference-adoption.md'], audit.digest(guidance.read_bytes()))
        settings = self.project / '.claude/settings.json'
        before = settings.read_bytes()
        guidance.write_text(guidance.read_text() + '\nLocal modification retained.\n')
        with self.assertRaisesRegex(installer.hook.AuditError, 'modified_managed_hook_reference'):
            installer.install(self.project)
        self.assertEqual(settings.read_bytes(), before)
        self.assertIn('Local modification retained.', guidance.read_text())

    def test_installer_preserves_idempotent_conflict_and_trust(self):
        (self.project / '.claude').mkdir()
        existing = {'permissions': {'allow': ['Read']}, 'hooks': {'SessionStart': [{'hooks': [{'type': 'command', 'command': 'echo preserved'}]}]}}
        settings = self.project / '.claude/settings.json';settings.write_text(json.dumps(existing))
        report = installer.install(self.project)
        self.assertEqual(report['trust'], 'pending_host_review')
        saved = settings.read_bytes()
        installer.install(self.project)
        self.assertEqual(settings.read_bytes(), saved)
        current = json.loads(saved)
        self.assertEqual(current['permissions'], existing['permissions'])
        self.assertEqual(current['hooks']['SessionStart'], existing['hooks']['SessionStart'])
        self.assertTrue((self.project / '.design-hooks/references/personal-ui.md').is_file())
        current['hooks']['Stop'][0]['hooks'][0]['command'] += ' --modified'
        settings.write_text(json.dumps(current))
        before = settings.read_bytes()
        with self.assertRaisesRegex(installer.hook.AuditError, 'conflicting_managed'):
            installer.install(self.project)
        self.assertEqual(settings.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
