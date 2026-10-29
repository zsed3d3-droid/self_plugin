#!/usr/bin/env python3
"""Validate declared container delivery contracts, not runtime health or all source code.

Missing mode retains legacy checks. Explicit mode=service adds PostgreSQL/SQLite
policy checks for declared databases and inline Compose environment values.
It does not inspect env_file contents, external databases, or execute queries.
"""
import argparse
import json
from pathlib import Path, PurePosixPath
import re


OFFICIAL_POSTGRES = {'postgres', 'library/postgres', 'docker.io/postgres',
                     'docker.io/library/postgres', 'index.docker.io/library/postgres'}
STABLE_POSTGRES_TAG = re.compile(
    r'^(\d+)\.(\d+)(?:-(?:alpine(?:\d+(?:\.\d+)*)?|bookworm|bullseye|trixie))?$'
)
SQLITE_URL = re.compile(r'(?i)(?:\bsqlite(?:\+[a-z0-9_]+)?\s*:|\bjdbc:sqlite\s*:)')


def project_file(root, value, label):
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise ValueError(f'{label}: use a project-relative file path')
    path = (root / value).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f'{label}: file path escapes the project')
    if not path.is_file():
        raise ValueError(f'{label}: file missing: {value}')
    return path


def environment(entry):
    values = entry.get('environment') or {}
    if isinstance(values, dict):
        return values
    if isinstance(values, list) and all(isinstance(v, str) for v in values):
        return dict(item.split('=', 1) if '=' in item else (item, None) for item in values)
    raise ValueError('Compose environment must be a mapping or a string list')


def postgres_image(image):
    """Return official-image recognition and the tag, without registry access."""
    if not isinstance(image, str):
        return False, ''
    image = image.split('@', 1)[0]
    name, separator, tag = image.rpartition(':')
    if not separator:
        name, tag = image, ''
    return name in OFFICIAL_POSTGRES, tag


def healthcheck(entry, name):
    health = entry.get('healthcheck') or {}
    test = health.get('test')
    if health.get('disable') or not test or test == 'NONE' or test == ['NONE']:
        raise ValueError(f'{name}: enabled healthcheck missing')


def container_path(value):
    if not isinstance(value, str) or not value.startswith('/') or '${' in value:
        raise ValueError('PGDATA and mount targets must be explicit absolute container paths')
    path = PurePosixPath(value)
    if '..' in path.parts:
        raise ValueError('Container path must not contain parent traversal')
    return path


def durable_mounts(entry, named_volumes):
    """Yield writable, explicitly backed volume targets; anonymous/tmpfs do not count."""
    for mount in entry.get('volumes') or []:
        if isinstance(mount, str):
            parts = mount.split(':')
            if len(parts) not in (2, 3):
                continue  # anonymous mount or ambiguous syntax
            source, target = parts[:2]
            readonly = len(parts) == 3 and 'ro' in parts[2].split(',')
            kind = 'bind' if source.startswith(('/', '.', '~')) else 'volume'
        elif isinstance(mount, dict):
            source, target = mount.get('source'), mount.get('target')
            readonly = bool(mount.get('read_only'))
            kind = mount.get('type', 'volume')
        else:
            continue
        if readonly or not isinstance(source, str) or not source or '${' in source:
            continue
        if kind == 'volume' and source not in named_volumes:
            continue
        if kind not in ('volume', 'bind'):
            continue
        # A long bind explicitly declares a host path. Named volumes must be
        # declared at Compose top level so an unrelated/anonymous mount cannot
        # masquerade as the database persistence contract.
        path = container_path(target)
        if path == PurePosixPath('/'):
            continue
        yield path


def check_postgres(entry, compose, name):
    official, tag = postgres_image(entry.get('image'))
    version = STABLE_POSTGRES_TAG.fullmatch(tag)
    if not official or not version:
        raise ValueError(f'{name}: use an official postgres image with an explicit stable major.minor tag (no latest/rc/beta)')
    major = int(version.group(1))
    default = f'/var/lib/postgresql/{major}/docker' if major >= 18 else '/var/lib/postgresql/data'
    data = container_path(environment(entry).get('PGDATA', default))
    named = compose.get('volumes') or {}
    if not isinstance(named, dict):
        raise ValueError('Compose named volumes must be a mapping')
    if not any(data == target or target in data.parents for target in durable_mounts(entry, named)):
        raise ValueError(f'{name}: writable named volume or explicit bind must cover PGDATA ({data})')


def check(root):
    root = Path(root).resolve()
    profile = project_file(root, '.devtools/services.json', 'Service manifest')
    manifest = json.loads(profile.read_text())
    mode = manifest.get('mode', 'legacy')
    if ('mode' in manifest and mode not in ('demo', 'service')):
        raise ValueError('mode must be demo or service; omit it only for a legacy manifest')
    services = manifest.get('services', [])
    if not isinstance(services, list) or not services:
        raise ValueError('Declare at least one service')
    import yaml
    compose = yaml.safe_load(project_file(root, manifest.get('compose', 'compose.yaml'), 'Compose').read_text())
    if not isinstance(compose, dict) or not isinstance(compose.get('services'), dict):
        raise ValueError('Compose must declare a services mapping')
    declared = set()
    for service in services:
        if not isinstance(service, dict) or not isinstance(service.get('name'), str) or not service['name']:
            raise ValueError('Each service requires a name')
        name = service['name']
        if name in declared:
            raise ValueError(f'Duplicate service: {name}')
        declared.add(name)
        database = service.get('database')
        if database not in (None, 'postgres', 'sqlite'):
            raise ValueError(f'{name}: database must be postgres or sqlite')
        if mode == 'service' and database == 'sqlite':
            raise ValueError(f'{name}: SQLite is permitted only for explicit demo or legacy manifests')
        if service.get('host_exception'):
            if name != 'mlx-transcriber' or not service.get('reason') or not service.get('health_url'):
                raise ValueError('Only explicitly approved mlx-transcriber Metal host exception is allowed')
            continue
        entry = compose['services'].get(name)
        if not isinstance(entry, dict):
            raise ValueError(f'{name}: Compose service missing')
        official, _ = postgres_image(entry.get('image'))
        if service.get('dockerfile'):
            project_file(root, service['dockerfile'], f'{name} Dockerfile')
        elif not (service.get('image') and service['image'] == entry.get('image') and official):
            raise ValueError(f'{name}: Dockerfile required; only explicitly declared official PostgreSQL infrastructure may use image alone')
        healthcheck(entry, name)
        if service.get('persistent') and not entry.get('volumes'):
            raise ValueError(f'{name}: persistent volume missing')
        if mode == 'service':
            env = environment(entry)
            if any(SQLITE_URL.search(str(value or '')) or str(key).upper().startswith('SQLITE') for key, value in env.items()):
                raise ValueError(f'{name}: inline Compose environment declares SQLite in service mode')
            if database == 'postgres' or official:
                check_postgres(entry, compose, name)
    undeclared = set(compose['services']) - declared
    if undeclared:
        raise ValueError(f'Undeclared Compose services: {sorted(undeclared)}')
    print(f'PASS container contract: {len(services)} declared services (mode={mode}; static checks only)')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('project', nargs='?', default='.')
    try:
        check(Path(parser.parse_args().project))
    except (ValueError, KeyError, OSError, ImportError) as error:
        raise SystemExit(f'FAIL: {error}')
