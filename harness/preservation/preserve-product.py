#!/usr/bin/env python3
"""Create a private, additive source snapshot and retain running Compose image IDs.

No build, container lifecycle, registry, deletion, or prune command is executed.
Requires POSIX directory descriptors and O_NOFOLLOW (macOS/Linux).
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fnmatch
import fcntl
from functools import lru_cache
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tarfile
import uuid


FORMAT = 'uxlab-product-preservation/v1'
DIRECTORIES = {
    '.git', 'node_modules', 'bower_components', '.venv', 'venv', 'env',
    'virtualenv', '.cache', 'cache', 'caches', '__pycache__', '.pytest_cache',
    '.mypy_cache', '.ruff_cache', '.hypothesis', '.next', '.nuxt', '.svelte-kit',
    '.turbo', '.parcel-cache', '.vite', '.tox', '.nox',
    '.agents', '.claude', '.codex', '.cursor',
    '.auth', '.credentials', '.secrets', '.tokens', '.sessions',
    '.ssh', '.aws', '.azure', '.gcloud', '.kube', '.docker',
    'pgdata', 'postgres-data', 'postgresql-data', 'dumps', 'backups',
}
PRIVATE_NAMES = {
    '.env', '.envrc', '.netrc', '.npmrc', '.pypirc', '.git-credentials',
    'auth.json', 'credentials.json', 'credential.json', 'config-secrets.json',
    'keychain', 'keychain-db', 'login.keychain-db',
}
PRIVATE_SUFFIXES = ('.pem', '.key', '.p12', '.pfx', '.jks', '.keystore',
                    '.keychain', '.keychain-db', '.kdbx')
DATA_SUFFIXES = ('.dump', '.pgdump', '.backup', '.bak', '.sqlite', '.sqlite3',
                 '.db', '.db3', '.dmp', '.rdb', '.aof')
PACKED_SUFFIXES = ('.tar', '.tgz', '.tbz', '.tbz2', '.txz', '.zip', '.7z',
                   '.rar', '.gz', '.bz2', '.xz', '.zst')
CREDENTIAL_WORD = re.compile(
    r'(^|[._-])(auth|oauth|credentials?|secrets?|passwords?|tokens?|sessions?)(?=$|[._-])', re.I)
SOURCE_SUFFIXES = {
    '.py', '.pyi', '.js', '.mjs', '.cjs', '.ts', '.tsx', '.jsx', '.css', '.scss',
    '.sass', '.less', '.vue', '.svelte', '.html', '.htm', '.svg', '.xml', '.md',
    '.mdx', '.rst', '.adoc', '.sh', '.bash', '.zsh', '.ps1', '.sql', '.go', '.rs',
    '.c', '.h', '.cc', '.cpp', '.hpp', '.cs', '.java', '.kt', '.swift', '.rb',
    '.php', '.ex', '.exs', '.erl', '.clj', '.cljs', '.dart', '.proto', '.graphql',
}
CONTAINER_ID = re.compile(r'^[a-f0-9]{64}$')
IMAGE_ID = re.compile(r'^sha256:[a-f0-9]{64}$')
LABEL = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,119}$')
INSPECT_FORMAT = (
    '{"id":{{json .Id}},"image_id":{{json .Image}},'
    '"running":{{json .State.Running}},'
    '"compose_project":{{json (index .Config.Labels "com.docker.compose.project")}},'
    '"service":{{json (index .Config.Labels "com.docker.compose.service")}},'
    '"working_dir":{{json (index .Config.Labels "com.docker.compose.project.working_dir")}}}'
)


class PreserveError(Exception):
    """Only a fixed error code is emitted; raw subprocess errors may contain secrets."""

    def __init__(self, code, snapshot=None):
        self.code, self.snapshot = code, snapshot
        super().__init__(code)


def timestamp():
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')


def snapshot_id():
    return timestamp() + '-' + uuid.uuid4().hex


def root_path(value):
    if not value or any(c in str(value) for c in '\x00\r\n'):
        raise PreserveError('invalid_root_path')
    raw = Path(value).expanduser()
    if '..' in raw.parts:
        raise PreserveError('parent_traversal_in_root')
    return Path(os.path.abspath(raw))


def directory_flags():
    if not hasattr(os, 'O_NOFOLLOW') or os.name != 'posix':
        raise PreserveError('posix_no_follow_required')
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


@contextmanager
def open_root(path, create=False):
    """Resolve one directory component at a time, never following a symlink."""
    fd = os.open(path.anchor, directory_flags())
    try:
        for part in path.parts[1:]:
            try:
                child = os.open(part, directory_flags(), dir_fd=fd)
            except FileNotFoundError:
                if not create:
                    raise PreserveError('root_missing') from None
                try:
                    os.mkdir(part, 0o700, dir_fd=fd)
                except FileExistsError:
                    pass  # A racing creator still has to pass the no-follow open.
                child = os.open(part, directory_flags(), dir_fd=fd)
            except OSError:
                raise PreserveError('root_symlink_or_not_directory') from None
            os.close(fd)
            fd = child
        yield fd
    finally:
        os.close(fd)


def identity(info):
    return info.st_dev, info.st_ino


def version(info):
    return identity(info), info.st_size, info.st_mtime_ns, info.st_ctime_ns


def verify_root(path, original_fd):
    with open_root(path) as current:
        if identity(os.fstat(current)) != identity(os.fstat(original_fd)):
            raise PreserveError('root_replaced_during_snapshot')


def validate_glob(value):
    if (not value or value.startswith('/') or value.startswith('!') or '\\' in value
            or any(c in value for c in '\x00\r\n') or '..' in value.split('/')):
        raise PreserveError('exclude_must_be_relative_glob')
    value = value.removeprefix('./').rstrip('/')
    if not value or any(not p or (p != '**' and '**' in p) for p in value.split('/')):
        raise PreserveError('invalid_exclude_glob')
    return value


def glob_matches(relative, pattern):
    parts, patterns = PurePosixPath(relative).parts, tuple(pattern.split('/'))

    @lru_cache(maxsize=None)
    def match(i, j):
        if j == len(patterns):
            return i == len(parts)
        if patterns[j] == '**':
            return match(i, j + 1) or (i < len(parts) and match(i + 1, j))
        return i < len(parts) and fnmatch.fnmatchcase(parts[i], patterns[j]) and match(i + 1, j + 1)

    return match(0, 0)


def excluded(relative, user_globs, is_directory=False):
    """Conservative name policy. This is not a content-based secret detector."""
    name = PurePosixPath(relative).name.lower()
    for pattern in user_globs:
        if glob_matches(relative, pattern):
            return 'explicit_glob:' + pattern
    if name in DIRECTORIES:
        return 'builtin_private_generated_or_cache_tree'
    if name in PRIVATE_NAMES or name.startswith('.env') or name.endswith('.env'):
        return 'builtin_environment_or_auth_file'
    if name.startswith(('id_rsa', 'id_ed25519', 'id_ecdsa', 'id_dsa', 'sk-proj-', 'sk-')):
        return 'builtin_private_key_or_token_name'
    if name.endswith(PRIVATE_SUFFIXES) or (not is_directory and
            PurePosixPath(name).suffix not in SOURCE_SUFFIXES and CREDENTIAL_WORD.search(name)):
        return 'builtin_credential_name'
    if name.endswith(DATA_SUFFIXES):
        return 'builtin_database_or_backup_file'
    if name.endswith(PACKED_SUFFIXES):
        return 'builtin_packed_data_or_nested_archive'
    if name.endswith(('.pyc', '.pyo', '.class', '.swp', '.swo')) or name == '.ds_store':
        return 'builtin_cache_file'
    return None


def private_fd(directory_fd, name, flags=os.O_WRONLY):
    fd = os.open(name, flags | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                 0o600, dir_fd=directory_fd)
    os.fchmod(fd, 0o600)
    return fd


def write_json(directory_fd, name, data):
    fd = private_fd(directory_fd, name)
    with os.fdopen(fd, 'wb') as target:
        target.write((json.dumps(data, sort_keys=True, indent=2, ensure_ascii=True) + '\n').encode())
        target.flush()
        os.fsync(target.fileno())
    os.fsync(directory_fd)


class Journal:
    def __init__(self, directory_fd, name):
        self.file = os.fdopen(private_fd(directory_fd, name), 'wb')

    def append(self, value):
        self.file.write((json.dumps(value, sort_keys=True, ensure_ascii=True) + '\n').encode())
        self.file.flush()
        os.fsync(self.file.fileno())

    def close(self):
        self.file.close()


def artifact_digest(directory_fd, name):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory_fd)
    with os.fdopen(fd, 'rb') as source:
        digest = hashlib.sha256()
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
        return {'path': name, 'bytes': source.tell(), 'sha256': digest.hexdigest()}


class DigestReader:
    def __init__(self, file):
        self.file, self.digest, self.count = file, hashlib.sha256(), 0

    def read(self, size=-1):
        value = self.file.read(size)
        self.digest.update(value)
        self.count += len(value)
        return value


def tar_entry(relative, info, directory=False):
    name = 'source/' + relative + ('/' if directory and relative else '')
    entry = tarfile.TarInfo(name)
    entry.uid = entry.gid = 0
    entry.uname = entry.gname = ''
    entry.mtime = info.st_mtime_ns // 1_000_000_000
    entry.mode = 0o700 if directory or info.st_mode & 0o111 else 0o600
    entry.type = tarfile.DIRTYPE if directory else tarfile.REGTYPE
    entry.size = 0 if directory else info.st_size
    return entry


def copy_source(source_fd, snapshot_fd, files, events, user_globs, state):
    raw = os.fdopen(private_fd(snapshot_fd, 'source.tar.gz'), 'wb')
    try:
        with gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as packed:
            with tarfile.open(fileobj=packed, mode='w|', format=tarfile.PAX_FORMAT) as archive:
                archive.addfile(tar_entry('', os.fstat(source_fd), directory=True))

                def walk(directory_fd, prefix=''):
                    before_directory = os.fstat(directory_fd)
                    for name in sorted(os.listdir(directory_fd)):
                        relative = (prefix + '/' + name).lstrip('/')
                        info = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                        reason = excluded(relative, user_globs, stat.S_ISDIR(info.st_mode))
                        if reason:
                            state['excluded'].append({'path': relative, 'reason': reason})
                            events.append({'event': 'excluded', 'path': relative, 'reason': reason})
                            continue
                        if stat.S_ISLNK(info.st_mode):
                            events.append({'event': 'source_refused', 'path': relative, 'reason': 'source_symlink'})
                            raise PreserveError('source_symlink_refused')
                        if stat.S_ISDIR(info.st_mode):
                            child = os.open(name, directory_flags(), dir_fd=directory_fd)
                            try:
                                if identity(os.fstat(child)) != identity(info):
                                    raise PreserveError('source_directory_replaced')
                                if 'pyvenv.cfg' in os.listdir(child):
                                    reason = 'builtin_detected_python_virtual_environment'
                                    state['excluded'].append({'path': relative, 'reason': reason})
                                    events.append({'event': 'excluded', 'path': relative, 'reason': reason})
                                    continue
                                archive.addfile(tar_entry(relative, info, directory=True))
                                files.append({'path': relative, 'type': 'directory', 'original_mode': oct(stat.S_IMODE(info.st_mode))})
                                walk(child, relative)
                            finally:
                                os.close(child)
                            continue
                        if not stat.S_ISREG(info.st_mode):
                            raise PreserveError('special_source_file_refused')
                        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                                     dir_fd=directory_fd)
                        with os.fdopen(fd, 'rb') as source:
                            before = os.fstat(source.fileno())
                            if not stat.S_ISREG(before.st_mode) or identity(before) != identity(info):
                                raise PreserveError('source_file_replaced')
                            if before.st_nlink != 1:
                                raise PreserveError('source_hardlink_refused')
                            header = source.read(512)
                            source.seek(0)
                            if (header.startswith((b'PGDMP', b'SQLite format 3\x00'))
                                    or b'-- PostgreSQL database dump' in header
                                    or b'-- MySQL dump' in header):
                                reason = 'builtin_detected_database_dump'
                                state['excluded'].append({'path': relative, 'reason': reason})
                                events.append({'event': 'excluded', 'path': relative, 'reason': reason})
                                continue
                            reader = DigestReader(source)
                            archive.addfile(tar_entry(relative, before), reader)
                            if version(os.fstat(source.fileno())) != version(before) or reader.count != before.st_size:
                                raise PreserveError('source_changed_while_reading')
                            files.append({'path': relative, 'type': 'file', 'bytes': reader.count,
                                          'sha256': reader.digest.hexdigest(),
                                          'original_mode': oct(stat.S_IMODE(before.st_mode)),
                                          'mtime_ns': before.st_mtime_ns})
                            state['files'] += 1
                            state['source_bytes'] += reader.count
                    if version(os.fstat(directory_fd)) != version(before_directory):
                        raise PreserveError('source_directory_changed_while_reading')

                walk(source_fd)
        raw.flush()
        os.fsync(raw.fileno())
        state['source_tar_complete'] = True
    finally:
        raw.close()


class Docker:
    """Only allowlisted metadata and local tags; never raw inspect/config/env output."""

    def run(self, arguments):
        try:
            result = subprocess.run(['docker', *arguments], capture_output=True,
                                    timeout=30, check=False)
        except (OSError, subprocess.TimeoutExpired):
            raise PreserveError('docker_unavailable_or_timed_out') from None
        if result.returncode:
            # Do not forward stdout/stderr: daemon/Compose error text can contain secrets.
            raise PreserveError('docker_command_failed')
        try:
            return result.stdout.decode('utf-8')
        except UnicodeDecodeError:
            raise PreserveError('invalid_docker_metadata') from None

    def containers(self, project):
        output = self.run(['container', 'ls', '--filter', 'status=running', '--filter',
                           'label=com.docker.compose.project.working_dir=' + str(project),
                           '--no-trunc', '--format', '{{.ID}}'])
        ids = sorted(set(output.splitlines()))
        if not ids or any(not CONTAINER_ID.fullmatch(value) for value in ids):
            raise PreserveError('no_scoped_running_compose_containers')
        rows = []
        for cid in ids:
            try:
                row = json.loads(self.run(['container', 'inspect', '--format', INSPECT_FORMAT, cid]))
            except ValueError:
                raise PreserveError('invalid_docker_metadata') from None
            if (not isinstance(row, dict)
                    or set(row) != {'id', 'image_id', 'running', 'compose_project', 'service', 'working_dir'}
                    or row['id'] != cid or not isinstance(row['image_id'], str)
                    or not IMAGE_ID.fullmatch(row['image_id'])
                    or row['running'] is not True or row['working_dir'] != str(project)
                    or not isinstance(row['compose_project'], str) or not LABEL.fullmatch(row['compose_project'])
                    or not isinstance(row['service'], str) or not LABEL.fullmatch(row['service'])):
                raise PreserveError('docker_scope_or_metadata_mismatch')
            rows.append(row)
        return rows

    def tag(self, image_id, reference):
        existing = self.run(['image', 'ls', '--quiet', '--no-trunc', '--filter', 'reference=' + reference])
        if existing.strip():
            raise PreserveError('preservation_tag_already_exists')
        self.run(['image', 'tag', image_id, reference])
        actual = self.run(['image', 'inspect', '--format', '{{.Id}}', reference]).strip()
        if actual != image_id:
            raise PreserveError('preservation_tag_verification_failed')


def preserve(project, archive_root, *, no_docker=False, exclude=(), docker=None):
    project, archive_root = root_path(project), root_path(archive_root)
    if project == Path(project.anchor) or Path.home().is_relative_to(project):
        raise PreserveError('project_root_too_broad')
    if archive_root.is_relative_to(project):
        raise PreserveError('archive_must_be_outside_project')
    user_globs = [validate_glob(value) for value in exclude]
    slug = re.sub(r'[^a-z0-9]+', '-', project.name.lower()).strip('-')[:70] or 'product'
    with open_root(project) as source_fd, open_root(archive_root, create=True) as archive_fd:
        if identity(os.fstat(source_fd)) == identity(os.fstat(archive_fd)):
            raise PreserveError('archive_and_project_same_directory')
        root_info = os.fstat(archive_fd)
        if root_info.st_uid != os.getuid() or root_info.st_mode & 0o022:
            raise PreserveError('archive_root_must_be_owned_and_not_shared_writable')
        # Persistent lock is never removed. Lock only serializes this harness, not other Docker clients.
        lock_fd = os.open('.preserve-product.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC,
                          0o600, dir_fd=archive_fd)
        try:
            lock_info = os.fstat(lock_fd)
            if (not stat.S_ISREG(lock_info.st_mode) or lock_info.st_uid != os.getuid()
                    or lock_info.st_nlink != 1 or stat.S_IMODE(lock_info.st_mode) != 0o600):
                raise PreserveError('unsafe_archive_lock')
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            sid = snapshot_id()
            name = slug + '-' + sid
            os.mkdir(name, 0o700, dir_fd=archive_fd)  # No collision retry, reuse or overwrite.
            snapshot_fd = os.open(name, directory_flags(), dir_fd=archive_fd)
            os.fchmod(snapshot_fd, 0o700)
            snapshot = archive_root / name
            events = files = None
            state = {'files': 0, 'source_bytes': 0, 'source_tar_complete': False,
                     'excluded': [], 'containers': [], 'image_tags': []}
            policy = {'tree_names': sorted(DIRECTORIES), 'private_names': sorted(PRIVATE_NAMES),
                      'private_suffixes': PRIVATE_SUFFIXES, 'database_suffixes': DATA_SUFFIXES,
                      'packed_suffixes': PACKED_SUFFIXES, 'credential_name_pattern': CREDENTIAL_WORD.pattern,
                      'ordinary_source_suffixes': sorted(SOURCE_SUFFIXES), 'explicit_globs': user_globs,
                      'database_signatures': ['PGDMP', 'SQLite format 3', 'PostgreSQL database dump', 'MySQL dump']}
            initial = {'format': FORMAT, 'status': 'started', 'snapshot_id': sid,
                       'project': str(project), 'snapshot': str(snapshot),
                       'created_at': datetime.now(timezone.utc).isoformat(),
                       'docker_mode': 'explicitly_skipped' if no_docker else 'running_compose_images',
                       'explicit_excludes': user_globs,
                       'tool_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                       'exclusion_policy': policy,
                       'exclusion_policy_sha256': hashlib.sha256(json.dumps(policy, sort_keys=True).encode()).hexdigest(),
                       'symlink_policy': 'refuse_nonexcluded_links_and_all_root_symlink_components',
                       'limits': ['Filtered source only; excluded material requires separate secure preservation.',
                                  'Local tags are references, not an image export, volume/DB backup, or writable-layer backup.',
                                  'Independent Docker clients can overwrite/remove tags; the daemon has no atomic create-only tag API.',
                                  'Change detection is not an atomic filesystem snapshot; stop editing while preserving.']}
            success = False
            error = None
            try:
                write_json(snapshot_fd, 'manifest.initial.json', initial)
                events, files = Journal(snapshot_fd, 'events.jsonl'), Journal(snapshot_fd, 'files.jsonl')
                events.append({'event': 'started', 'snapshot_id': sid})
                if not no_docker:
                    engine = docker or Docker()
                    state['containers'] = engine.containers(project)
                    events.append({'event': 'running_images_observed', 'containers': state['containers']})
                    for image_id in sorted({row['image_id'] for row in state['containers']}):
                        reference = 'uxlab-preserved/' + slug + ':' + sid + '-' + image_id[7:19]
                        planned = {'image_id': image_id, 'reference': reference, 'verified': False}
                        state['image_tags'].append(planned)
                        events.append({'event': 'image_tag_planned', **planned})
                        engine.tag(image_id, reference)
                        planned['verified'] = True
                        events.append({'event': 'image_tag_verified', **planned})
                copy_source(source_fd, snapshot_fd, files, events, user_globs, state)
                verify_root(project, source_fd)
                verify_root(archive_root, archive_fd)
                if identity(os.stat(name, dir_fd=archive_fd, follow_symlinks=False)) != identity(os.fstat(snapshot_fd)):
                    raise PreserveError('snapshot_directory_replaced')
                events.append({'event': 'completed', 'files': state['files']})
                success = True
            except (Exception, KeyboardInterrupt) as failure:
                error = failure.code if isinstance(failure, PreserveError) else type(failure).__name__
                if events:
                    events.append({'event': 'failed', 'error_code': error})
            finally:
                if files:
                    files.close()
                if events:
                    events.close()
                final = {**initial, **state, 'status': 'complete' if success else 'failed',
                         'finished_at': datetime.now(timezone.utc).isoformat(), 'error_code': error,
                         'artifacts': []}
                try:
                    for artifact in ('source.tar.gz', 'files.jsonl', 'events.jsonl'):
                        try:
                            final['artifacts'].append(artifact_digest(snapshot_fd, artifact))
                        except FileNotFoundError:
                            pass
                    write_json(snapshot_fd, 'manifest.json', final)
                except Exception:
                    raise PreserveError('final_manifest_write_failed', str(snapshot)) from None
                finally:
                    os.close(snapshot_fd)
            return final
        finally:
            os.close(lock_fd)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True, help='Explicit canonical product directory')
    parser.add_argument('--archive-root', required=True, help='Owned archive directory outside the product')
    parser.add_argument('--no-docker', action='store_true', help='Explicit source-only snapshot; no Docker command')
    parser.add_argument('--exclude', action='append', default=[], metavar='RELATIVE_GLOB',
                        help='Additional relative exclusion; repeatable; ** matches any directory depth')
    args = parser.parse_args(argv)
    try:
        result = preserve(args.project, args.archive_root, no_docker=args.no_docker, exclude=args.exclude)
        print(json.dumps({'format': FORMAT, 'status': result['status'], 'snapshot': result['snapshot'],
                          'files': result['files'], 'excluded': len(result['excluded']),
                          'docker_mode': result['docker_mode'], 'error_code': result['error_code']}))
        return 0 if result['status'] == 'complete' else 1
    except (Exception, KeyboardInterrupt) as error:
        code = error.code if isinstance(error, PreserveError) else type(error).__name__
        print(json.dumps({'format': FORMAT, 'status': 'failed',
                          'snapshot': getattr(error, 'snapshot', None), 'error_code': code}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
