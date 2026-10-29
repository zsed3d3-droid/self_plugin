#!/usr/bin/env python3
"""Read-only, scoped design-contract checks. This is a token audit, not a UX verdict."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

FORMAT = 'scenario-design-contract/v1'
FENCE = re.compile(r'^```design-contract\s*\n(.*?)^```\s*$', re.M | re.S)
LINK = re.compile(r'<!-- design-contract: ([^\s<>]+) sha256:([a-f0-9]{64}) -->')
TOKEN = re.compile(r'^--[a-zA-Z][\w-]*$')
DECL = re.compile(r'(?P<name>--[\w-]+|[\w-]+)\s*:\s*(?P<value>[^;{}]+)(?:;|(?=}))')
COLOR = re.compile(r'#[\da-fA-F]{3,8}\b|(?:rgba?|hsla?|oklch|oklab|lab|lch|color)\([^()]*\)', re.I)
SIZE = re.compile(r'(?<![\w.-])-?(?:\d*\.)?\d+(?:px|rem|em|vh|vw|%)(?![\w-])', re.I)
VARS = re.compile(r'var\(\s*(--[\w-]+)')


class AuditError(ValueError):
    pass


def digest(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode()).hexdigest()


def design_hash(text):
    """Exact UTF-8 narrative after removing the machine block/link; LF is canonical."""
    return digest(LINK.sub('', FENCE.sub('', text.replace('\r\n', '\n'))).strip() + '\n')


def read_json(path):
    def unique(items):
        result = {}
        for key, value in items:
            if key in result:
                raise AuditError('duplicate_json_key')
            result[key] = value
        return result
    try:
        raw = path.read_bytes()
        if len(raw) > 2_000_000:
            raise AuditError('json_too_large')
        return json.loads(raw, object_pairs_hook=unique)
    except (ValueError, OSError, UnicodeError) as error:
        raise AuditError('invalid_json') from error


def relative_file(project, value):
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise AuditError('path_must_be_project_relative')
    path = project / value
    if '..' in Path(value).parts or any(part in {'.git', '.codex', '.claude', '.design-hooks'} or part.startswith('.env') for part in Path(value).parts):
        raise AuditError('protected_source_path')
    cursor = project
    for part in Path(value).parts:
        cursor /= part
        if cursor.is_symlink():
            raise AuditError('symlink_source')
    if not path.is_file() or not path.resolve().is_relative_to(project):
        raise AuditError('source_missing_or_outside_project')
    if path.stat().st_size > 2_000_000:
        raise AuditError('source_too_large')
    return path


def load_contract(project, contract_path=None):
    narrative_path = relative_file(project, 'DESIGN.md')
    text = narrative_path.read_text(encoding='utf-8')
    fences, links = list(FENCE.finditer(text)), list(LINK.finditer(text))
    if len(fences) + len(links) != 1:
        raise AuditError('exactly_one_design_contract_block_or_link_required')
    contract_file = None
    if fences:
        if contract_path and contract_path != 'DESIGN.md':
            raise AuditError('contract_location_conflict')
        try:
            # Reuse duplicate-key validation without writing any temporary source file.
            class Inline:
                def read_bytes(self):
                    return fences[0].group(1).encode()
            contract = read_json(Inline())
        except AuditError:
            raise AuditError('invalid_inline_contract') from None
    else:
        linked = links[0].group(1)
        if contract_path and contract_path != linked:
            raise AuditError('contract_location_conflict')
        contract_file = relative_file(project, linked)
        if digest(contract_file.read_bytes()) != links[0].group(2):
            raise AuditError('contract_file_hash_mismatch')
        contract = read_json(contract_file)
    if not isinstance(contract, dict) or contract.get('format') != FORMAT:
        raise AuditError('unsupported_contract_format')
    if not re.fullmatch(r'[\w.:-]{1,100}', str(contract.get('task_id', ''))):
        raise AuditError('stable_task_id_required')
    design = contract.get('design', {})
    if not isinstance(design, dict) or design.get('path') != 'DESIGN.md' or design.get('sha256') != design_hash(text):
        raise AuditError('design_narrative_hash_mismatch')
    if contract.get('max_repairs') not in {2, 3}:
        raise AuditError('max_repairs_must_be_2_or_3')
    scope = contract.get('scope', {})
    if not isinstance(scope, dict):
        raise AuditError('invalid_scope')
    paths = scope.get('paths')
    if not isinstance(paths, list) or not paths or len(paths) > 200 or any(not isinstance(name, str) for name in paths) or len(paths) != len(set(paths)):
        raise AuditError('explicit_unique_scope_paths_required')
    evidence = scope.get('evidence_paths', [])
    if not isinstance(evidence, list) or len(evidence) > 200 or any(not isinstance(name, str) for name in evidence):
        raise AuditError('invalid_evidence_paths')
    files = {name: relative_file(project, name) for name in list(dict.fromkeys(paths + evidence))}
    if any(path.suffix.lower() not in {'.css', '.html', '.js', '.mjs', '.ts', '.jsx', '.tsx'} for path in files.values()):
        raise AuditError('scope_must_contain_only_ui_source_files')
    if not isinstance(scope.get('allow', []), list):
        raise AuditError('invalid_allowances')
    for allowance in scope.get('allow', []):
        if (not isinstance(allowance, dict) or allowance.get('path') not in files or
                allowance.get('rule') not in {'color', 'spacing', 'typography', 'radius'} or
                not isinstance(allowance.get('values'), list) or not allowance['values'] or
                not str(allowance.get('reason', '')).strip()):
            raise AuditError('invalid_scoped_legacy_allowance')
    tokens = contract.get('tokens', {})
    if not isinstance(tokens, dict) or set(tokens) - {'color', 'spacing', 'typography', 'radius'}:
        raise AuditError('invalid_tokens')
    for kind in ('color', 'spacing', 'typography'):
        if not isinstance(tokens.get(kind), dict) or not tokens[kind]:
            raise AuditError('three_token_categories_required')
        if any(not TOKEN.fullmatch(name) or not isinstance(value, str) or not value.strip()
               for name, value in tokens[kind].items()):
            raise AuditError('invalid_token')
    token_names = [name for group in tokens.values() if isinstance(group, dict) for name in group]
    if len(token_names) != len(set(token_names)):
        raise AuditError('duplicate_token_category')
    if 'radius' in tokens and (not isinstance(tokens['radius'], dict) or not tokens['radius'] or
            any(not TOKEN.fullmatch(name) or not isinstance(value, str) or not value.strip() for name, value in tokens['radius'].items())):
        raise AuditError('invalid_radius_tokens')
    if not isinstance(contract.get('shapes', []), list):
        raise AuditError('invalid_shape_rules')
    utility = contract.get('utility_classes', {})
    if (not isinstance(utility, dict) or not isinstance(utility.get('enabled', False), bool) or
            any(key not in {'enabled', 'color', 'spacing', 'typography', 'radius'} for key in utility) or
            any(not isinstance(value, list) or any(not isinstance(item, str) for item in value)
                for key, value in utility.items() if key != 'enabled')):
        raise AuditError('invalid_utility_classes')
    for shape in contract.get('shapes', []):
        if (not isinstance(shape, dict) or shape.get('path') not in files or not shape.get('selector') or
                shape.get('radius') not in tokens.get('radius', {}) or not shape.get('role') or not shape.get('reason')):
            raise AuditError('invalid_scoped_shape_rule')
    checks = contract.get('checks', {})
    if not isinstance(checks, dict):
        raise AuditError('invalid_checks_configuration')
    command_inputs = []
    for stage in ('syntax', 'browser', 'critique'):
        config = checks.get(stage, {})
        if not isinstance(config, dict):
            raise AuditError('invalid_stage_configuration')
        inputs = config.get('input_paths', [])
        if (not isinstance(inputs, list) or len(inputs) > 500 or any(not isinstance(name, str) for name in inputs) or
                (config.get('argv') and not inputs)):
            raise AuditError('command_input_paths_required')
        command_inputs.extend(relative_file(project, name) for name in inputs)
    return contract, files, list(dict.fromkeys([narrative_path] + ([contract_file] if contract_file else []) + command_inputs))


def policy_check(project, policy):
    if not policy:
        return {'status': 'not_configured'}
    if not isinstance(policy, dict):
        raise AuditError('invalid_policy_configuration')
    try:
        paths = [Path(policy[name]) for name in ('decisions', 'applications')]
        paths = [p if p.is_absolute() else project / p for p in paths]
        if any(not p.is_file() or p.is_symlink() for p in paths):
            raise AuditError('policy_missing')
        original, applied = [read_json(p) for p in paths]
        if not isinstance(original, dict) or not isinstance(applied, dict) or original.get('format') != 'da-development-decisions/v1' or applied.get('format') != 'da-development-application/v1':
            raise AuditError('invalid_policy_format')
        decisions = original['decisions']
        applications = applied['applications']
        latest = {row['rule_id']: row for row in decisions}
        if len(latest) != len(decisions) or len(decisions) != original['source']['latest_decision_count']:
            raise AuditError('policy_decision_count_mismatch')
        if len(applications) != len(latest) or len({row['rule_id'] for row in applications}) != len(latest):
            raise AuditError('policy_application_count_mismatch')
        if applied['source_event_watermark'] != original['source']['event_watermark']:
            raise AuditError('policy_watermark_mismatch')
        for row in applications:
            raw = latest.get(row['rule_id'], {})
            if (raw.get('decision') not in {'adopt', 'reject'} or row.get('decision') != raw['decision'] or
                    row.get('source_event_id') != raw.get('event_id') or row.get('source_revision') != raw.get('revision') or
                    not row.get('scope') or not row.get('applied_behavior') or not row.get('reference')):
                raise AuditError('policy_application_stale')
        return {'status': 'pass', 'count': len(latest), 'event_watermark': applied['source_event_watermark'],
                'sha256': [digest(p.read_bytes()) for p in paths]}
    except (KeyError, TypeError, ValueError, OSError, AttributeError):
        return {'status': 'fail' if policy.get('required', True) else 'not_run', 'reason': 'policy_missing_invalid_or_stale'}


def normalize(value):
    return re.sub(r'\s+', ' ', value.strip()).lower()


def css_text(path):
    text = path.read_text(encoding='utf-8')
    if path.suffix.lower() == '.html':
        blocks = re.findall(r'<style\b[^>]*>(.*?)</style>', text, re.I | re.S)
        blocks += ['inline {' + match[1] + ';}' for match in re.findall(r'\bstyle\s*=\s*([\"\'])(.*?)\1', text, re.I | re.S)]
        return '\n'.join(blocks)
    return text if path.suffix.lower() == '.css' else ''


def css_syntax(text):
    """Conservative structural scan, not a browser CSS parser or JS/HTML validator."""
    stack, quote, comment, escape = [], None, False, False
    index = 0
    while index < len(text):
        char, pair = text[index], text[index:index + 2]
        if comment:
            if pair == '*/':
                comment = False
                index += 1
        elif quote:
            if escape:
                escape = False
            elif char == '\\':
                escape = True
            elif char == quote:
                quote = None
        elif pair == '/*':
            comment = True
            index += 1
        elif char in '\"\'':
            quote = char
        elif char == '{':
            stack.append(char)
        elif char == '}':
            if not stack:
                return False
            stack.pop()
        index += 1
    return not (stack or quote or comment)


def audit(project, contract_path=None, changed=None):
    contract, files, protected = load_contract(project, contract_path)
    selected = set(changed) if changed else set(contract['scope']['paths'])
    selected &= set(contract['scope']['paths'])
    findings, declarations = [], {}
    tokens = contract['tokens']
    css = {name: css_text(files[name]) for name in contract['scope']['paths']}
    for name, text in css.items():
        if name in selected and not css_syntax(text):
            findings.append({'path': name, 'rule': 'syntax', 'reason': 'unbalanced_css_structure'})
        for match in DECL.finditer(re.sub(r'/\*.*?\*/', '', text, flags=re.S)):
            if match['name'].startswith('--'):
                declarations.setdefault(match['name'], []).append((name, normalize(match['value'])))
    for category, group in tokens.items():
        for name, value in group.items():
            if name not in declarations:
                findings.append({'rule': 'token_missing', 'token': name})
            elif any(actual != normalize(value) for _, actual in declarations[name]):
                findings.append({'rule': 'token_drift', 'token': name, 'paths': sorted({p for p, _ in declarations[name]})})
    for name in sorted(selected):
        raw_source = files[name].read_text(encoding='utf-8')
        if re.search(r'\bstyle\s*=\s*\{|\.style(?:\.[A-Za-z]+|\[)|\bstyle\s*:\s*\{', raw_source):
            findings.append({'path': name, 'rule': 'unsupported_style_syntax',
                             'reason': 'dynamic_or_jsx_style_requires_ast_or_explicit_project_validator_not_covered_by_css_scan'})
        classes = (re.findall(r'\bclass(?:Name)?\s*=\s*(?:\{\s*)?[\"\'`]([^\"\'`]+)', raw_source)
                   if contract.get('utility_classes', {}).get('enabled', False) else [])
        for attribute in classes:
            for classname in attribute.split():
                last = classname.rsplit(':', 1)[-1]
                kind = None
                if re.match(r'^(?:p[trblxyse]?|m[trblxyse]?|gap|gap-[xy]|space-[xy]|inset|top|left|right|bottom)-', last):
                    kind = 'spacing'
                elif re.match(r'^(?:rounded)(?:-|$)', last):
                    kind = 'radius'
                elif re.match(r'^(?:font|leading|tracking)-|^text-(?:xs|sm|base|lg|[2-9]?xl|\[[\d.]+(?:px|rem|em)\])$', last):
                    kind = 'typography'
                elif re.match(r'^(?:bg|fill|stroke)-|^text-(?!left$|right$|center$|justify$|start$|end$|wrap$|nowrap$|balance$|pretty$)', last):
                    kind = 'color'
                elif '[' in last and re.search(r'#[\da-fA-F]{3,8}|(?:color|padding|margin|font|gap|radius):', last):
                    kind = 'color'
                if kind and classname not in contract.get('utility_classes', {}).get(kind, []):
                    findings.append({'path': name, 'rule': kind, 'reason': 'utility_class_not_in_contract', 'value': classname})
        if contract.get('utility_classes', {}).get('enabled', False) and re.search(r'\bclassName\s*=\s*\{(?!\s*[\"\'`])', raw_source):
            findings.append({'path': name, 'rule': 'unsupported_style_syntax',
                             'reason': 'dynamic_class_expression_requires_project_ast_validator'})
        text = re.sub(r'/\*.*?\*/', '', css[name], flags=re.S)
        for match in DECL.finditer(text):
            prop, value = match['name'].lower(), match['value']
            if prop.startswith('--'):
                continue
            kind = None
            if prop == 'border-radius' or re.fullmatch(r'border-(?:top|bottom)-(?:left|right)-radius', prop):
                kind, literals = 'radius', SIZE.findall(value)
                if not tokens.get('radius'):
                    continue
            elif (prop in {'color', 'background', 'fill', 'stroke', 'box-shadow', 'text-shadow'} or
                    prop.endswith('-color') or prop in {'border', 'border-top', 'border-right', 'border-bottom', 'border-left', 'outline'}):
                kind, literals = 'color', COLOR.findall(value)
                plain = re.sub(r'var\([^)]*\)', '', value).strip()
                if not literals and plain and plain.lower() not in {'inherit', 'initial', 'unset', 'revert', 'transparent', 'currentcolor', 'none'}:
                    if prop in {'color', 'fill', 'stroke'} or prop.endswith('-color') or re.fullmatch(r'[A-Za-z]+', plain):
                        literals = [plain]
            elif re.fullmatch(r'(?:margin|padding|gap|row-gap|column-gap|inset|top|right|bottom|left)(?:-[\w-]+)?', prop):
                kind, literals = 'spacing', SIZE.findall(value)
            elif prop in {'font', 'font-family', 'font-size', 'font-weight', 'line-height', 'letter-spacing'}:
                kind = 'typography'
                stripped = re.sub(r'var\([^)]*\)', '', value).strip()
                literals = [stripped] if stripped and stripped not in {'inherit', 'initial', 'unset', 'normal', '0'} else []
            if not kind:
                continue
            allowed = {normalize(v) for row in contract['scope'].get('allow', [])
                       if row['path'] == name and row['rule'] == kind for v in row['values']}
            for literal in literals:
                if normalize(literal) not in allowed:
                    findings.append({'path': name, 'line': text.count('\n', 0, match.start()) + 1,
                                     'rule': kind, 'reason': 'literal_requires_token_or_scoped_allowance', 'value': literal})
            for var in VARS.findall(value):
                if var not in tokens.get(kind, {}) and normalize(var) not in allowed:
                    findings.append({'path': name, 'rule': kind, 'reason': 'unmanaged_token_reference', 'token': var})
    for shape in contract.get('shapes', []):
        if shape['path'] not in selected:
            continue
        values = []
        for block in re.finditer(r'([^{}]+)\{([^{}]*)\}', css[shape['path']]):
            if shape['selector'] in [part.strip() for part in block[1].split(',')]:
                values += [normalize(match['value']) for match in DECL.finditer(block[2]) if match['name'] == 'border-radius']
        # A literal fallback is equivalent only when it equals this contract token.
        # CSS permits whitespace around the comma; do not mistake a valid fallback for drift.
        token_value = normalize(tokens['radius'][shape['radius']])
        expected = re.compile(r'var\(\s*' + re.escape(shape['radius']) +
                              r'\s*(?:,\s*' + re.escape(token_value) + r'\s*)?\)')
        if not values or any(not expected.fullmatch(value) for value in values):
            findings.append({'path': shape['path'], 'rule': 'shape', 'role': shape['role'],
                             'selector': shape['selector'], 'reason': 'declared_role_radius_missing_or_different'})
    policy = policy_check(project, contract.get('policy'))
    if policy['status'] == 'fail':
        findings.append({'rule': 'personal_policy', 'reason': policy['reason']})
    source_hashes = {str(path.relative_to(project)): digest(path.read_bytes()) for path in [*files.values(), *protected]}
    report = {'format': 'scenario-design-audit/v1', 'status': 'fail' if findings else 'pass',
              'task_id': contract['task_id'], 'scope': sorted(selected), 'findings': findings,
              'evidence_only_paths': sorted(set(files) - set(contract['scope']['paths'])),
              'utility_class_scan': 'enabled' if contract.get('utility_classes', {}).get('enabled', False) else 'not_configured',
              'source_hashes': source_hashes, 'policy': policy,
              'coverage': 'CSS/static HTML declarations, declared utility classes, and structure only; dynamic/JSX styles fail closed. No complete syntax, browser, UX, or user preference verdict'}
    return report, contract, files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--contract')
    parser.add_argument('--changed', action='append')
    parser.add_argument('--print-design-hash', action='store_true')
    args = parser.parse_args()
    try:
        project = args.project.resolve(strict=True)
        if args.print_design_hash:
            print(design_hash((project / 'DESIGN.md').read_text(encoding='utf-8')))
            return 0
        report, _, _ = audit(project, args.contract, args.changed)
    except (AuditError, OSError, UnicodeError, TypeError, AttributeError) as error:
        report = {'format': 'scenario-design-audit/v1', 'status': 'fail', 'reason': str(error) if isinstance(error, AuditError) else 'invalid_project_input'}
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report['status'] == 'pass' else 1


if __name__ == '__main__':
    sys.exit(main())
