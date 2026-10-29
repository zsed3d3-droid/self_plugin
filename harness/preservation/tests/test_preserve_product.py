#!/usr/bin/env python3
"""Synthetic, retained fixtures only. No Docker daemon or existing product is used."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tarfile
import unittest
from unittest import mock
import uuid

sys.dont_write_bytecode = True
TOOLS = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('preserve_product', TOOLS / 'preserve-product.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
RUN = TOOLS / 'tests' / 'runs' / (p.timestamp() + '-' + uuid.uuid4().hex)
RUN.mkdir(parents=True, mode=0o700)
RUN.chmod(0o700)


class FakeDocker(p.Docker):
    def __init__(self, project, *, existing=False, fail=False, mismatch=False):
        self.project, self.existing, self.fail, self.mismatch = project, existing, fail, mismatch
        self.calls, self.tags = [], {}
        self.cid, self.image = 'c' * 64, 'sha256:' + 'a' * 64

    def run(self, args):
        self.calls.append(args)
        if self.fail:
            raise p.PreserveError('docker_command_failed')
        if args[:2] == ['container', 'ls']:
            return self.cid + '\n'
        if args[:2] == ['container', 'inspect']:
            return json.dumps({'id': self.cid, 'image_id': self.image, 'running': True,
                               'compose_project': 'qa-compose', 'service': 'app',
                               'working_dir': str(self.project)})
        if args[:2] == ['image', 'ls']:
            return self.image if self.existing else ''
        if args[:2] == ['image', 'tag']:
            assert args[3] not in self.tags, 'Fake Docker refuses a tag overwrite.'
            self.tags[args[3]] = args[2]
            return ''
        if args[:2] == ['image', 'inspect']:
            return ('sha256:' + 'b' * 64) if self.mismatch else self.tags[args[-1]]
        raise AssertionError('Unapproved Docker operation: ' + repr(args[:2]))


class PreservationTests(unittest.TestCase):
    def setUp(self):
        self.root = RUN / self._testMethodName
        self.project, self.archive = self.root / 'synthetic-product', self.root / 'archives'
        self.project.mkdir(parents=True, mode=0o700)
        (self.project / 'app.py').write_text('print("synthetic source")\n')

    def source(self, path, data='FAKE_PRIVATE_MARKER_DO_NOT_ARCHIVE', mode=None):
        target = self.project / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data.encode() if isinstance(data, str) else data)
        if mode is not None:
            target.chmod(mode)
        return target

    def preserve(self, **kwargs):
        return p.preserve(self.project, self.archive, no_docker=True, **kwargs)

    def entries(self, result):
        with tarfile.open(Path(result['snapshot']) / 'source.tar.gz') as archive:
            return {item.name: archive.extractfile(item).read() for item in archive if item.isfile()}

    def test_source_hashes_tar_and_private_permissions(self):
        self.source('web/hello 한글.txt', '한글 synthetic content\n')
        self.source('scripts/run.sh', '#!/bin/sh\ntrue\n', mode=0o755)
        (self.project / 'empty').mkdir()
        result = self.preserve()
        self.assertEqual(result['status'], 'complete')
        directory = Path(result['snapshot'])
        self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o700)
        for file in directory.iterdir():
            self.assertEqual(stat.S_IMODE(file.stat().st_mode), 0o600)
        entries = self.entries(result)
        manifest = [json.loads(line) for line in (directory / 'files.jsonl').read_text().splitlines()]
        for item in manifest:
            if item['type'] == 'file':
                self.assertEqual(item['sha256'], hashlib.sha256(entries['source/' + item['path']]).hexdigest())
                self.assertEqual(item['bytes'], len(entries['source/' + item['path']]))
        for artifact in result['artifacts']:
            self.assertEqual(artifact['sha256'], hashlib.sha256((directory / artifact['path']).read_bytes()).hexdigest())
        with tarfile.open(directory / 'source.tar.gz') as archive:
            self.assertTrue(all(not x.name.startswith('/') and '..' not in Path(x.name).parts for x in archive))
            self.assertEqual(archive.getmember('source/scripts/run.sh').mode, 0o700)
            self.assertEqual(archive.getmember('source/app.py').mode, 0o600)
            self.assertTrue(archive.getmember('source/empty').isdir())

    def test_sensitive_generated_cache_and_dump_exclusions(self):
        paths = ['.env', '.env.example', '.env-local', 'config/prod.env', '.envrc', 'auth/session.json',
                 'credentials.json', '.codex/auth.json', '.claude/settings.json',
                 '.agents/skills/link', '.cursor/rules/agent', '.ssh/id_ed25519',
                 '.docker/config.json', 'service-token.json', 'auth-prod.json',
                 'keys/client.pem', 'node_modules/library.js', '.git/config',
                 '.venv/bin/python', 'cache/response.txt', '__pycache__/x.pyc',
                 'backups/private.sql', 'db/latest.dump', 'db/live.sqlite3',
                 'nested-source.tar.gz', 'backup.zip']
        for path in paths:
            self.source(path)
        self.source('migrations/001.sql', 'CREATE TABLE synthetic(id integer);\n')
        source_code = ['auth/session.py', 'tests/test_sessions.py', 'secret_config.py',
                       'credentials/helper.ts', 'tokens/ui.js', 'auth/styles.css']
        for path in source_code:
            self.source(path, '/* synthetic application source, no credential */\n')
        self.source('innocent.sql', '--\n-- PostgreSQL database dump\n--\nSELECT private;')
        self.source('opaque.bin', b'PGDMP' + b'FAKE_PRIVATE_MARKER_DO_NOT_ARCHIVE')
        self.source('tool-runtime/pyvenv.cfg', 'home = /synthetic')
        self.source('tool-runtime/lib/anything.txt')
        result = self.preserve()
        self.assertEqual(result['status'], 'complete')
        entries = self.entries(result)
        self.assertEqual(set(entries), {'source/app.py', 'source/migrations/001.sql',
                                      *('source/' + x for x in source_code)})
        self.assertFalse(any(b'FAKE_PRIVATE_MARKER' in value for value in entries.values()))
        reasons = {x['reason'] for x in result['excluded']}
        self.assertIn('builtin_detected_database_dump', reasons)
        self.assertIn('builtin_detected_python_virtual_environment', reasons)

    def test_repeated_explicit_relative_globs_are_recorded(self):
        for path in ['research/raw/page.html', 'research/raw/deep/page.txt',
                     'references/full.html', 'references/nested/other.html']:
            self.source(path)
        self.source('references/notes.md', 'Keep this synthetic source note.')
        result = self.preserve(exclude=['research/raw/**', '**/*.html'])
        self.assertEqual(set(self.entries(result)), {'source/app.py', 'source/references/notes.md'})
        self.assertEqual(result['explicit_excludes'], ['research/raw/**', '**/*.html'])
        self.assertTrue(all(x['reason'].startswith('explicit_glob:') for x in result['excluded']))

    def test_bad_exclude_roots_and_parent_traversal_fail_before_writing(self):
        for pattern in ['../private/**', '/absolute/**', r'windows\secret', '!include', 'x/**bad']:
            with self.subTest(pattern=pattern), self.assertRaises(p.PreserveError):
                self.preserve(exclude=[pattern])
        self.assertFalse(self.archive.exists())

    def test_archive_inside_product_and_broad_root_are_refused(self):
        with self.assertRaisesRegex(p.PreserveError, 'archive_must_be_outside_project'):
            p.preserve(self.project, self.project / 'archive', no_docker=True)
        self.assertFalse((self.project / 'archive').exists())
        with self.assertRaisesRegex(p.PreserveError, 'project_root_too_broad'):
            p.preserve('/', self.archive, no_docker=True)
        with self.assertRaisesRegex(p.PreserveError, 'project_root_too_broad'):
            p.preserve(Path.home(), self.archive, no_docker=True)

    def test_project_root_symlink_and_symlink_ancestor_are_refused(self):
        link = self.root / 'project-link'
        link.symlink_to(self.project, target_is_directory=True)
        with self.assertRaisesRegex(p.PreserveError, 'root_symlink_or_not_directory'):
            p.preserve(link, self.archive, no_docker=True)
        self.source('subdir/file.py', 'synthetic')
        with self.assertRaisesRegex(p.PreserveError, 'root_symlink_or_not_directory'):
            p.preserve(link / 'subdir', self.archive, no_docker=True)

    def test_archive_root_symlink_is_refused(self):
        outside = self.root / 'outside'
        outside.mkdir()
        self.archive.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(p.PreserveError, 'root_symlink_or_not_directory'):
            self.preserve()
        self.assertEqual(list(outside.iterdir()), [])

    def test_source_symlink_escape_keeps_failed_partial_manifest(self):
        outside = self.root / 'outside-private.txt'
        outside.write_text('OUTSIDE_FAKE_SECRET_MUST_NOT_BE_READ')
        (self.project / 'z-escape').symlink_to(outside)
        result = self.preserve()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['error_code'], 'source_symlink_refused')
        self.assertFalse(result['source_tar_complete'])
        self.assertTrue((Path(result['snapshot']) / 'manifest.initial.json').exists())
        self.assertTrue((Path(result['snapshot']) / 'manifest.json').exists())
        self.assertFalse(any(b'OUTSIDE_FAKE_SECRET' in v for v in self.entries(result).values()))

    def test_in_bounds_symlink_is_also_explicitly_refused(self):
        (self.project / 'linked.py').symlink_to('app.py')
        self.assertEqual(self.preserve()['error_code'], 'source_symlink_refused')

    def test_excluded_generated_symlink_never_follows_target(self):
        outside = self.root / 'outside-private'
        outside.mkdir()
        (outside / 'secret.txt').write_text('OUTSIDE_FAKE_SECRET')
        (self.project / '.agents').symlink_to(outside, target_is_directory=True)
        result = self.preserve()
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(set(self.entries(result)), {'source/app.py'})

    def test_source_hardlink_and_special_file_are_refused(self):
        outside = self.root / 'outside-private.txt'
        outside.write_text('OUTSIDE_FAKE_SECRET')
        os.link(outside, self.project / 'z-hardlink')
        self.assertEqual(self.preserve()['error_code'], 'source_hardlink_refused')
        other = self.root / 'fifo-product'
        other.mkdir()
        os.mkfifo(other / 'fifo')
        result = p.preserve(other, self.archive, no_docker=True)
        self.assertEqual(result['error_code'], 'special_source_file_refused')

    def test_append_only_new_versions_do_not_change_first_snapshot(self):
        first = self.preserve()
        old = {f.name: f.read_bytes() for f in Path(first['snapshot']).iterdir()}
        self.source('app.py', 'print("synthetic revision")\n')
        second = self.preserve()
        self.assertNotEqual(first['snapshot'], second['snapshot'])
        for name, content in old.items():
            self.assertEqual((Path(first['snapshot']) / name).read_bytes(), content)
        self.assertNotEqual(self.entries(first)['source/app.py'], self.entries(second)['source/app.py'])

    def test_destination_collision_never_reuses_or_overwrites(self):
        with mock.patch.object(p, 'snapshot_id', return_value='fixed-synthetic-collision'):
            first = self.preserve()
            old = {f.name: f.read_bytes() for f in Path(first['snapshot']).iterdir()}
            with self.assertRaises(FileExistsError):
                self.preserve()
        self.assertEqual(old, {f.name: f.read_bytes() for f in Path(first['snapshot']).iterdir()})

    def test_file_changed_during_copy_is_not_reported_complete(self):
        original = p.DigestReader.read
        changed = False

        def modify(reader, size=-1):
            nonlocal changed
            value = original(reader, size)
            if not changed:
                changed = True
                info = (self.project / 'app.py').stat()
                os.utime(self.project / 'app.py', ns=(info.st_atime_ns, info.st_mtime_ns + 1_000_000))
            return value

        with mock.patch.object(p.DigestReader, 'read', modify):
            result = self.preserve()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['error_code'], 'source_changed_while_reading')

    def test_shared_writable_archive_root_is_refused(self):
        self.archive.mkdir(mode=0o700)
        self.archive.chmod(0o777)
        with self.assertRaisesRegex(p.PreserveError, 'archive_root_must_be_owned'):
            self.preserve()

    def test_no_docker_does_not_call_docker(self):
        with mock.patch.object(p.Docker, 'run', side_effect=AssertionError('Docker must not run')):
            result = self.preserve()
        self.assertEqual(result['docker_mode'], 'explicitly_skipped')
        self.assertEqual(result['containers'], [])

    def test_initial_empty_product_source_only_snapshot(self):
        empty = self.root / 'never-run-empty-product'
        empty.mkdir()
        result = p.preserve(empty, self.archive, no_docker=True)
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(result['files'], 0)
        self.assertTrue(result['source_tar_complete'])
        self.assertEqual(self.entries(result), {})

    def test_fake_docker_scopes_metadata_and_creates_unique_verified_tags(self):
        engine = FakeDocker(self.project)
        first = p.preserve(self.project, self.archive, docker=engine)
        second = p.preserve(self.project, self.archive, docker=engine)
        self.assertEqual(first['status'], 'complete')
        self.assertEqual(second['status'], 'complete')
        self.assertEqual(len(engine.tags), 2)
        self.assertNotEqual(first['image_tags'][0]['reference'], second['image_tags'][0]['reference'])
        self.assertTrue(first['image_tags'][0]['verified'])
        self.assertIn('label=com.docker.compose.project.working_dir=' + str(self.project), engine.calls[0])
        for call in engine.calls:
            self.assertIn(call[:2], [['container', 'ls'], ['container', 'inspect'], ['image', 'ls'], ['image', 'tag'], ['image', 'inspect']])
            self.assertNotIn('{{json .Config}}', call)
            self.assertNotIn('{{json .Config.Env}}', call)

    def test_preexisting_tag_is_not_tagged_over(self):
        engine = FakeDocker(self.project, existing=True)
        result = p.preserve(self.project, self.archive, docker=engine)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['error_code'], 'preservation_tag_already_exists')
        self.assertFalse(any(args[:2] == ['image', 'tag'] for args in engine.calls))
        self.assertTrue((Path(result['snapshot']) / 'manifest.json').exists())

    def test_failed_tag_verification_retains_partial_state_without_cleanup(self):
        engine = FakeDocker(self.project, mismatch=True)
        result = p.preserve(self.project, self.archive, docker=engine)
        self.assertEqual(result['error_code'], 'preservation_tag_verification_failed')
        self.assertEqual(len(engine.tags), 1)
        self.assertFalse(result['image_tags'][0]['verified'])
        self.assertFalse(any(args[0] in {'rm', 'rmi', 'prune'} for args in engine.calls))

    def test_unavailable_docker_fails_with_private_partial_manifest(self):
        result = p.preserve(self.project, self.archive, docker=FakeDocker(self.project, fail=True))
        self.assertEqual(result['error_code'], 'docker_command_failed')
        self.assertFalse(result['source_tar_complete'])
        self.assertTrue((Path(result['snapshot']) / 'manifest.initial.json').exists())

    def test_docker_scope_mismatch_is_refused(self):
        engine = FakeDocker(self.root / 'different-product')
        result = p.preserve(self.project, self.archive, docker=engine)
        self.assertEqual(result['error_code'], 'no_scoped_running_compose_containers' if not engine.calls else 'docker_scope_or_metadata_mismatch')
        self.assertEqual(engine.tags, {})

    def test_raw_docker_errors_are_never_forwarded(self):
        result = subprocess.CompletedProcess(['docker'], 1, b'FAKE_ENV_PASSWORD=private', b'FAKE_TOKEN=private')
        with mock.patch.object(p.subprocess, 'run', return_value=result):
            with self.assertRaisesRegex(p.PreserveError, '^docker_command_failed$') as caught:
                p.Docker().run(['container', 'ls'])
        self.assertNotIn('private', str(caught.exception))

    def test_cli_exit_status_and_failed_artifact_path(self):
        (self.project / 'escape').symlink_to(self.root / 'not-followed')
        command = [sys.executable, str(TOOLS / 'preserve-product.py'), '--project', str(self.project),
                   '--archive-root', str(self.archive), '--no-docker']
        result = subprocess.run(command, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 1)
        output = json.loads(result.stdout)
        self.assertEqual(output['status'], 'failed')
        self.assertTrue((Path(output['snapshot']) / 'manifest.json').exists())
        self.assertEqual(result.stderr, '')


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(PreservationTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {'status': 'pass' if result.wasSuccessful() else 'fail', 'tests': result.testsRun,
              'failures': len(result.failures), 'errors': len(result.errors),
              'fixture_policy': 'All synthetic fixtures and snapshots retained; no existing product or real Docker used.',
              'run_directory': str(RUN)}
    fd = os.open(RUN / 'test-result.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as target:
        json.dump(report, target, indent=2)
        target.write('\n')
    print(json.dumps(report))
    raise SystemExit(0 if result.wasSuccessful() else 1)
