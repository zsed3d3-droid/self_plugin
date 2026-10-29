#!/usr/bin/env python3
"""Install project-local hooks without changing user settings or hook trust."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import re
import shlex
import sys

spec = importlib.util.spec_from_file_location('design_hook', Path(__file__).with_name('design-hook.py'))
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)
MARKER = 'scenario-ui-ux/design-hooks/v1'


def guarded(project, value):
    target = project / value
    cursor = project
    for part in Path(value).parts:
        cursor /= part
        if cursor.is_symlink():
            raise hook.AuditError('symlink_install_target')
    return target


def planned_config(project, host, command):
    relative = '.codex/hooks.json' if host == 'codex' else '.claude/settings.json'
    path = guarded(project, relative)
    current = hook.read_json(path) if path.exists() else {}
    if not isinstance(current, dict) or not isinstance(current.get('hooks', {}), dict):
        raise hook.AuditError('invalid_existing_hook_configuration')
    if host == 'codex':
        toml = guarded(project, '.codex/config.toml')
        if toml.is_file() and re.search(r'^\s*\[\[?hooks(?:[.\]])', toml.read_text(), re.M):
            raise hook.AuditError('existing_inline_codex_hooks_require_manual_merge')
    hooks = current.setdefault('hooks', {})
    desired = {}
    for event in ('PostToolUse', 'Stop'):
        handler = {'type': 'command', 'command': command, 'timeout': 180, 'statusMessage': MARKER}
        group = {'hooks': [handler]}
        if event == 'PostToolUse':
            group['matcher'] = 'Write|Edit|apply_patch|Bash|exec_command|shell_command'
        desired[event] = group
        existing = hooks.setdefault(event, [])
        if not isinstance(existing, list):
            raise hook.AuditError('invalid_existing_hook_event')
        found = []
        for index, item in enumerate(existing):
            for configured in item.get('hooks', []) if isinstance(item, dict) else []:
                if not isinstance(configured, dict):
                    raise hook.AuditError('invalid_existing_hook_handler')
                if configured.get('statusMessage') == MARKER or '.design-hooks/design-hook.py' in str(configured.get('command', '')):
                    found.append(index)
        if found:
            if len(found) != 1 or existing[found[0]] != group:
                raise hook.AuditError('conflicting_managed_design_hook')
        else:
            existing.append(group)
    return path, current


def install(project, host='both', contract=None):
    # Validate every source/target before mutating any config. No hook executes during installation.
    hook.audit_module.load_contract(project, contract)
    runtime = guarded(project, '.design-hooks')
    manifest_path = guarded(project, '.design-hooks/managed.json')
    old = hook.read_json(manifest_path) if manifest_path.exists() else None
    if old and (not isinstance(old, dict) or old.get('format') != MARKER):
        raise hook.AuditError('unmanaged_hook_runtime')
    if runtime.exists() and not old and any(runtime.iterdir()):
        raise hook.AuditError('nonempty_unmanaged_hook_runtime')
    sources = {}
    for name in ('design-audit.py', 'design-hook.py'):
        source = Path(__file__).with_name(name)
        target = guarded(project, '.design-hooks/' + name)
        if target.exists() and (not old or hook.digest(target.read_bytes()) != old.get('files', {}).get(name)):
            raise hook.AuditError('modified_managed_hook_runtime')
        sources[name] = source.read_bytes()
    references = {}
    for name in ('runtime-ux-method.md', 'designer-judgment.md', 'personal-ui.md'):
        source = Path(__file__).parent.parent / 'references' / name
        if not source.is_file():
            raise hook.AuditError('required_ux_reference_missing')
        target = guarded(project, '.design-hooks/references/' + name)
        if target.exists() and (not old or hook.digest(target.read_bytes()) != old.get('references', {}).get(name)):
            raise hook.AuditError('modified_managed_hook_reference')
        references[name] = source.read_bytes()
    command = shlex.join([sys.executable, str(runtime / 'design-hook.py'), '--project', str(project)] +
                         (['--contract', contract] if contract else []))
    hosts = ('codex', 'claude') if host == 'both' else (host,)
    plans = [planned_config(project, item, command) for item in hosts]
    # Hook/config files are install outputs only; source files and DESIGN.md are untouched.
    runtime.mkdir(exist_ok=True)
    for name, data in sources.items():
        target = runtime / name
        if not target.exists() or target.read_bytes() != data:
            target.write_bytes(data)
    (runtime / 'references').mkdir(exist_ok=True)
    for name, data in references.items():
        target = runtime / 'references' / name
        if not target.exists() or target.read_bytes() != data:
            target.write_bytes(data)
    manifest = {'format': MARKER, 'files': {name: hook.digest(data) for name, data in sources.items()},
                'references': {name: hook.digest(data) for name, data in references.items()}}
    runtime_marker = runtime / 'managed.json'
    if not runtime_marker.exists() or hook.read_json(runtime_marker) != manifest:
        runtime_marker.write_text(json.dumps(manifest, indent=2) + '\n')
    for path, config in plans:
        if path.exists() and hook.read_json(path) == config:
            continue
        path.parent.mkdir(exist_ok=True)
        # Existing host configuration has no managed format: preserve all keys and replace atomically.
        import os
        import tempfile
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as output:
            json.dump(config, output, ensure_ascii=False, indent=2)
            output.write('\n')
            temp = output.name
        os.replace(temp, path)
    return {'format': 'scenario-design-install/v1', 'hosts': list(hosts), 'configs': [str(p.relative_to(project)) for p, _ in plans],
            'trust': 'pending_host_review', 'ci_argv': [sys.executable, '.design-hooks/design-hook.py', '--project', '.', '--event', 'CI'],
            'notes': 'No trust or permission setting was changed. Review exact hook definition in the host. Existing CI can invoke ci_argv directly.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('--host', choices=('codex', 'claude', 'both'), default='both')
    parser.add_argument('--contract')
    args = parser.parse_args()
    try:
        report = install(args.project.resolve(strict=True), args.host, args.contract)
    except (hook.AuditError, OSError, ValueError, TypeError, KeyError, AttributeError) as error:
        print(json.dumps({'status': 'fail', 'reason': str(error) if isinstance(error, hook.AuditError) else 'invalid_install_input'}))
        return 1
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
