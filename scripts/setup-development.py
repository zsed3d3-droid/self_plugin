#!/usr/bin/env python3
"""Install a routed project profile without replacing repository-owned instructions."""
import argparse
import hashlib
import json
import os
from pathlib import Path

SKILLS = {
    'da-development-method': 'da-development-method',
    'scenario-ui-ux': 'scenario-ui-ux',
    'ux-judgment': 'scenario-ui-ux',
    'text-wireframe-planner': 'text-wireframe-planner',
    'plain-writing': 'plain-writing',
    'unbox-ui': 'unbox-ui',
    'live-browser-session': 'live-browser-session',
    'craft-ui-motion': 'craft-ui-motion',
    'responsive-layout-guard': 'craft-ui-motion',
}
MARKER = '<!-- da-development-profile: managed -->'
OWNER = 'da-development-profile'
MANIFEST = '.devtools/profile-manifest.json'
# Previous installer copied this exact checker without recording a manifest.
# Only the known unmodified legacy copy may be adopted when its source changes.
LEGACY_CHECKER_HASHES = {'46b077f856feb641085d58b0ab5e91f7ea4dd6f7c27d0a63582f00d77f1bb219'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def skill_description(path):
    """Read only the supported scalar/block description field; no general YAML parser."""
    lines = path.read_text().splitlines()
    if not lines or lines[0] != '---':
        raise ValueError(f'Skill frontmatter missing: {path}')
    try:
        end = lines.index('---', 1)
    except ValueError:
        raise ValueError(f'Skill frontmatter is not closed: {path}')
    for index, line in enumerate(lines[1:end], 1):
        if not line.startswith('description:'):
            continue
        value = line.partition(':')[2].strip()
        if value in {'>', '>-', '>+', '|', '|-', '|+'}:
            body = []
            for continuation in lines[index + 1:end]:
                if continuation and not continuation.startswith((' ', '\t')):
                    break
                body.append(continuation.strip())
            value = ' '.join(body).strip()
        elif value.startswith('"'):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                raise ValueError(f'Use a JSON-compatible quoted description in {path}')
        elif value.startswith("'") and value.endswith("'"):
            value = value[1:-1].replace("''", "'")
        if not value:
            raise ValueError(f'Skill description is empty: {path}')
        return value
    raise ValueError(f'Skill description missing: {path}')


def assert_local_destination(path, project):
    # Generated regular files never follow existing destination symlinks.
    if path.is_symlink():
        raise ValueError(f'Unmanaged destination symlink: {path}')
    if not path.parent.resolve().is_relative_to(project):
        raise ValueError(f'Destination parent escapes project: {path}')


def install(project, source):
    project = project.resolve()
    source = source.resolve()
    if not project.is_dir():
        raise ValueError(f'Project does not exist: {project}')
    manifest_path = project / MANIFEST
    assert_local_destination(manifest_path, project)
    previous = {}
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text())
        except (OSError, json.JSONDecodeError):
            raise ValueError(f'Invalid management manifest: {manifest_path}')
        if manifest.get('managed_by') != OWNER or not isinstance(manifest.get('files'), dict):
            raise ValueError(f'Unmanaged manifest: {manifest_path}')
        previous = manifest['files']
    files = {}

    def add(relative, text):
        files[project / relative] = text.encode()

    add('.cursor/rules/da-development.mdc', f'''---
description: Automatically route scenario-driven gstack development and container delivery
alwaysApply: true
---
{MARKER}
Read repository AGENTS.md and its service harness first, then `.agents/skills/da-development-method/SKILL.md` and its source. Classify the actual request and automatically select its workflow with `python3 .devtools/route-development.py --request '{{"work_type":"ui","new_flow":true}}'` (replace the fields with this task). Do not ask the user to pick skills. The router returns a plan, not executed work or a semantic-search result; retrieve scoped user evidence and verify the selected skills are available. Keep gstack as the base flow; use only the required TDD practice from Superpowers, without its second full workflow. Small authorized fixes need no extra approval/model gate. Run one appropriate browser verification path.
New services require Dockerfile, Compose, healthcheck and persistent-volume declarations; the approved MLX Metal host engine is the explicit exception. Run `.devtools/check-containers.py` for new-service delivery. Follow accepted user reasons, project/action permissions and paid-tool approval scope. Do not force fixed density, theme, color or card layouts. Verify gstack discovery before claiming its review or QA ran.
''')
    for skill, plugin in SKILLS.items():
        source_skill = source / 'plugins' / plugin / 'skills' / skill
        skill_file = source_skill / 'SKILL.md'
        if not skill_file.is_file():
            raise ValueError(f'Source skill missing: {skill_file}')
        description = skill_description(skill_file)
        relative = os.path.relpath(source_skill, project)
        add(f'.agents/skills/{skill}/SKILL.md', f'''---
name: {skill}
description: {json.dumps(description, ensure_ascii=False)}
---
{MARKER}
Apply this skill automatically when the actual task matches its description or the project routing plan selects it. Read `{relative}/SKILL.md` relative to the project root. Resolve scripts/assets/references relative to that source skill directory. This wrapper is discovery metadata, not a replacement for the source instructions. If the source is missing, run `bash .devtools/setup.sh /path/to/self_plugin`; do not claim it was loaded or executed.
''')
    relative_source = os.path.relpath(source, project)
    add('.devtools/setup.sh', f'''#!/usr/bin/env bash
# {MARKER}
set -euo pipefail
PROJECT="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE="${{1:-${{PROJECT}}/{relative_source}}}"
python3 "$SOURCE/scripts/setup-development.py" --project "$PROJECT"
''')
    add('.devtools/README.md', f'''{MARKER}
# Development profile

Run `bash .devtools/setup.sh /path/to/self_plugin` after moving/cloning this checkout. Root AGENTS.md, CLAUDE.md and service harnesses remain repository-owned.

The agent classifies the request, retrieves scoped user evidence, then uses `python3 .devtools/route-development.py --request '{{"work_type":"ui","new_flow":true}}'` to choose the relevant workflow automatically. Supported work_type values: feature, ui, bugfix, review, backend, copy, motion, feedback. Optional boolean fields: new_flow, ambiguous, behavior_change, has_ui. framework is descriptive context, not permission to install a library. A plan does not mean a skill was run, and this deterministic router does not perform semantic retrieval.

Cursor and Codex discover the project skills. gstack commands require a verified installation (`self_plugin/scripts/setup-gstack.sh`); the agent checks this before using them. Superpowers contributes TDD practices only. Small authorized fixes avoid repeated role, approval and model gates.

All new services must be declared in `.devtools/services.json` and pass `python3 .devtools/check-containers.py`. This static checker requires PyYAML in the development environment; runtime container verification is separate. Existing services are adopted incrementally and have not implicitly passed a container audit.

`.devtools/profile-manifest.json` records generated file hashes. Reinstallation updates unchanged managed files; a user edit or unmanaged destination causes preflight failure before any generated file changes. No production service is started by installation.
''')
    helpers = {'check-containers.py': source / 'scripts/check-containers.py',
               'route-development.py': source / 'scripts/route-development.py'}
    for name, helper in helpers.items():
        if not helper.is_file():
            raise ValueError(f'Source helper missing: {helper}')
        files[project / '.devtools' / name] = helper.read_bytes()

    # Preflight all file and link conflicts before creating directories or writing.
    for path, content in files.items():
        assert_local_destination(path, project)
        if not path.exists():
            continue
        if not path.is_file():
            raise ValueError(f'Destination is not a file: {path}')
        actual = path.read_bytes()
        relative = path.relative_to(project).as_posix()
        if relative in previous:
            if digest(actual) != previous[relative]:
                raise ValueError(f'Managed file was edited; preserve/reconcile before reinstalling: {path}')
        elif actual == content:
            continue
        elif relative == '.devtools/check-containers.py' and digest(actual) in LEGACY_CHECKER_HASHES:
            continue
        elif MARKER.encode() in actual:
            # Migrate the old installer's explicitly managed text files once.
            continue
        else:
            raise ValueError(f'Unmanaged destination: {path}')
    links = {}
    for skill in SKILLS:
        link = project / '.cursor/skills' / skill
        if not link.parent.resolve().is_relative_to(project):
            raise ValueError(f'Skill discovery parent escapes project: {link}')
        target = f'../../.agents/skills/{skill}'
        if (link.exists() or link.is_symlink()) and not (link.is_symlink() and os.readlink(link) == target):
            raise ValueError(f'Unmanaged skill destination: {link}')
        links[link] = target

    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    for link, target in links.items():
        link.parent.mkdir(parents=True, exist_ok=True)
        if not link.is_symlink():
            link.symlink_to(target, target_is_directory=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({'managed_by': OWNER, 'schema_version': 1,
        'files': {path.relative_to(project).as_posix(): digest(content) for path, content in files.items()}},
        ensure_ascii=False, indent=2) + '\n')
    print(f'Installed {len(SKILLS)} automatically routed skills in {project}; repository harness preserved')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        install(args.project, args.source)
    except (ValueError, OSError) as error:
        parser.exit(2, f'Install failed: {error}\n')


if __name__ == '__main__':
    main()
