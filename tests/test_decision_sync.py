"""Review evidence export invariants; fixtures never write to the user's journal."""
import copy
from contextlib import closing
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'plugins/da-development-method/skills/da-development-method/scripts/sync-decisions.py'
spec = importlib.util.spec_from_file_location('sync_decisions', SCRIPT)
syncer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(syncer)


class DecisionSyncTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.db = self.root / 'review.sqlite'
        self.catalog = self.root / 'catalog.json'
        self.output = self.root / 'profile.json'
        self.catalog_data = {
            'version': 'review-1',
            'experts': [{
                'name': 'Fixture expert', 'field': 'Fixture domain',
                'sources': [{'title': 'Original source', 'url': 'https://example.org/source'}],
                'rules': [
                    {'id': f'rule-{i:02}', 'title': f'Title {i}', 'rule': f'Original rule {i}',
                     'when': 'Only for fixture work', 'test': 'An observable result',
                     'recommendation': 'Candidate'}
                    for i in range(30)
                ],
            }],
        }
        self.catalog.write_text(json.dumps(self.catalog_data), encoding='utf-8')
        with closing(sqlite3.connect(self.db)) as connection, connection:
            connection.execute('''CREATE TABLE decision_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_id TEXT, report_version TEXT, decision TEXT, reason TEXT,
                revision INTEGER, created_at TEXT, rule_snapshot TEXT)''')
        for i in range(30):
            self.add_event(i, 1, 'reject' if i < 5 else 'adopt')
        # 33 events, 30 current decisions. Revision, not insertion order, determines current state.
        self.add_event(0, 2, 'reject', '  Exact user reason with spaces\nand a second line.  ')
        self.add_event(1, 2, 'reject')
        self.add_event(2, 2, 'reject')

    def snapshot(self, i):
        expert = self.catalog_data['experts'][0]
        return {'expert': expert['name'], 'field': expert['field'],
                'sources': expert['sources'], **expert['rules'][i]}

    def add_event(self, i, revision, decision='adopt', reason='Fixture reason', snapshot=None, version='review-1'):
        with closing(sqlite3.connect(self.db)) as connection, connection:
            connection.execute(
                'INSERT INTO decision_events(rule_id,report_version,decision,reason,revision,created_at,rule_snapshot) VALUES(?,?,?,?,?,?,?)',
                (f'rule-{i:02}', version, decision, reason, revision,
                 '2026-10-28T00:00:00+00:00', json.dumps(self.snapshot(i) if snapshot is None else snapshot)),
            )

    def test_latest_revision_and_portable_exact_evidence(self):
        before = hashlib.sha256(self.db.read_bytes()).hexdigest()
        profile = syncer.sync(self.db, self.catalog, self.output)
        self.assertEqual(profile['counts'], {'adopt': 25, 'reject': 5})
        self.assertEqual(profile['source'], {
            'journal': 'decision_events', 'event_watermark': 33,
            'history_event_count': 33, 'latest_decision_count': 30})
        first = profile['decisions'][0]
        self.assertEqual(first['revision'], 2)
        self.assertEqual(first['event_id'], 31)
        self.assertEqual(first['decision'], 'reject')
        self.assertEqual(first['reason'], '  Exact user reason with spaces\nand a second line.  ')
        self.assertEqual(first['rule_snapshot'], self.snapshot(0))
        self.assertEqual(first['snapshot_sha256'], syncer.fingerprint(self.snapshot(0)))
        self.assertEqual(first['prior_events'][0]['event_id'], 1)
        self.assertEqual(first['prior_events'][0]['revision'], 1)
        serialized = self.output.read_text()
        self.assertNotIn(str(self.db), serialized)
        self.assertNotIn('request_id', serialized)
        self.assertNotIn('body_hash', serialized)
        self.assertEqual(hashlib.sha256(self.db.read_bytes()).hexdigest(), before)

    def test_check_is_deterministic_and_detects_changes(self):
        profile = syncer.sync(self.db, self.catalog, self.output)
        before = self.output.read_bytes()
        self.assertEqual(syncer.sync(self.db, self.catalog, self.output, check=True), profile)
        self.assertEqual(self.output.read_bytes(), before)
        self.add_event(3, 2, 'adopt', 'A later user decision')
        with self.assertRaisesRegex(syncer.SyncError, 'differs'):
            syncer.sync(self.db, self.catalog, self.output, check=True)
        self.assertEqual(self.output.read_bytes(), before)
        refreshed = syncer.sync(self.db, self.catalog, self.output)
        self.assertEqual(refreshed['source']['event_watermark'], 34)
        self.assertEqual(refreshed['counts'], {'adopt': 26, 'reject': 4})

    def test_incomplete_review_leaves_output_untouched(self):
        syncer.sync(self.db, self.catalog, self.output)
        before = self.output.read_bytes()
        self.add_event(4, 2, 'undecided')
        with self.assertRaisesRegex(syncer.SyncError, 'incomplete'):
            syncer.sync(self.db, self.catalog, self.output)
        self.assertEqual(self.output.read_bytes(), before)
        missing_output = self.root / 'not-created' / 'profile.json'
        with self.assertRaises(syncer.SyncError):
            syncer.sync(self.db, self.catalog, missing_output)
        self.assertFalse(missing_output.parent.exists())

    def test_missing_rule_and_empty_reason_are_not_complete(self):
        with closing(sqlite3.connect(self.db)) as connection, connection:
            connection.execute("DELETE FROM decision_events WHERE rule_id='rule-29'")
        with self.assertRaisesRegex(syncer.SyncError, 'missing decisions'):
            syncer.sync(self.db, self.catalog, self.output)
        self.add_event(29, 1, reason='   ')
        with self.assertRaisesRegex(syncer.SyncError, 'no reason'):
            syncer.sync(self.db, self.catalog, self.output)
        self.assertFalse(self.output.exists())

    def test_unknown_rule_is_not_silently_ignored(self):
        with closing(sqlite3.connect(self.db)) as connection, connection:
            connection.execute("UPDATE decision_events SET rule_id='unknown' WHERE event_id=1")
        with self.assertRaisesRegex(syncer.SyncError, 'absent from catalog'):
            syncer.sync(self.db, self.catalog, self.output)
        self.assertFalse(self.output.exists())

    def test_changed_scope_source_and_review_version_are_stale(self):
        for field, new_value in [('when', 'A different scope'), ('rule', 'Changed rule')]:
            changed = copy.deepcopy(self.catalog_data)
            changed['experts'][0]['rules'][0][field] = new_value
            self.catalog.write_text(json.dumps(changed), encoding='utf-8')
            with self.assertRaisesRegex(syncer.SyncError, 'Stale review'):
                syncer.sync(self.db, self.catalog, self.output)
        changed = copy.deepcopy(self.catalog_data)
        changed['experts'][0]['sources'][0]['url'] = 'https://example.org/new-source'
        self.catalog.write_text(json.dumps(changed), encoding='utf-8')
        with self.assertRaisesRegex(syncer.SyncError, 'Stale review'):
            syncer.sync(self.db, self.catalog, self.output)
        changed = copy.deepcopy(self.catalog_data)
        changed['version'] = 'review-2'
        self.catalog.write_text(json.dumps(changed), encoding='utf-8')
        with self.assertRaisesRegex(syncer.SyncError, 'Stale review'):
            syncer.sync(self.db, self.catalog, self.output)
        self.assertFalse(self.output.exists())

    def test_protected_and_unmanaged_targets_are_preserved(self):
        unmanaged = self.root / 'unmanaged.json'
        unmanaged.write_text('{"user":"configuration"}')
        before = unmanaged.read_bytes()
        for target in [unmanaged, self.catalog, self.db, self.root / 'auth.json',
                       self.root / '.ssh' / 'profile.json', self.root / '.docker' / 'profile.json',
                       self.root / 'config.json']:
            with self.assertRaises(syncer.SyncError):
                syncer.sync(self.db, self.catalog, target)
        self.assertEqual(unmanaged.read_bytes(), before)
        link = self.root / 'link.json'
        link.symlink_to(unmanaged)
        with self.assertRaisesRegex(syncer.SyncError, 'symlink'):
            syncer.sync(self.db, self.catalog, link)
        self.assertEqual(unmanaged.read_bytes(), before)

    def test_atomic_write_failure_preserves_previous_profile(self):
        syncer.sync(self.db, self.catalog, self.output)
        before = self.output.read_bytes()
        self.add_event(4, 2, 'adopt', 'Changed preference')
        with patch.object(syncer.os, 'replace', side_effect=OSError('simulated replace failure')):
            with self.assertRaises(OSError):
                syncer.sync(self.db, self.catalog, self.output)
        self.assertEqual(self.output.read_bytes(), before)
        self.assertFalse(list(self.root.glob('.decision-profile-*.tmp')))

    def test_check_missing_output_never_creates_directories(self):
        output = self.root / 'missing' / 'profile.json'
        with self.assertRaisesRegex(syncer.SyncError, 'missing or differs'):
            syncer.sync(self.db, self.catalog, output, check=True)
        self.assertFalse(output.parent.exists())

    def test_cli_reports_counts_without_printing_user_reasons(self):
        command = [sys.executable, str(SCRIPT), '--db', str(self.db),
                   '--catalog', str(self.catalog), '--output', str(self.output)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('30 rules, 25 adopted, 5 rejected', result.stdout)
        self.assertNotIn('Exact user reason', result.stdout + result.stderr)
        self.assertEqual(subprocess.run(command + ['--check'], capture_output=True).returncode, 0)


if __name__ == '__main__':
    unittest.main()
