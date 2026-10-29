#!/usr/bin/env python3
"""Check the distributable source tree without printing potentially private values."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SKIP = {'.git', '.venv', 'node_modules', '__pycache__', '.runtime', '.data',
        '.design-audit', 'archive', 'verification', 'runs', 'state'}
PRIVATE = {'auth.json', 'credentials.json', 'personal-decisions.json',
           'decision-application.json', 'scope.json', 'state.json'}
PATTERNS = [re.compile(r'\b(?:ghp|gho|github_pat|sk-proj)[_-][A-Za-z0-9_-]{30,}'),
            re.compile(r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----'),
            re.compile(r'/Users/(?!user(?:/|\b)|me(?:/|\b)|example(?:/|\b)|your-user(?:/|\b))[A-Za-z0-9_.-]+/')]


def main():
    # Once staged, examine exactly what Git would publish; ignored runtime files stay local.
    staged = subprocess.run(['git', 'ls-files', '--cached', '-z'], cwd=ROOT,
                            capture_output=True, check=True).stdout
    paths = [ROOT / p.decode() for p in staged.split(b'\0') if p]
    if not paths:
        visible = subprocess.run(['git', 'ls-files', '--others', '--exclude-standard', '-z'],
                                 cwd=ROOT, capture_output=True, check=True).stdout
        paths = [ROOT / p.decode() for p in visible.split(b'\0') if p]
    findings, count = [], 0
    for path in sorted(paths):
        name = path.relative_to(ROOT).as_posix()
        if path.is_symlink():
            findings.append({'path': name, 'reason': 'symlink_requires_explicit_review'})
            continue
        if (path.name in PRIVATE or path.name.startswith('.env') and path.name != '.env.example'
                or path.suffix in {'.db', '.dump', '.sqlite', '.pem', '.key'}
                or SKIP.intersection(path.relative_to(ROOT).parts)):
            findings.append({'path': name, 'reason': 'private_or_generated_path'})
            continue
        raw = path.read_bytes()
        try:
            body = raw.decode('utf-8')
        except UnicodeDecodeError:
            findings.append({'path': name, 'reason': 'binary_requires_explicit_review'})
            continue
        for index, line in enumerate(body.splitlines(), 1):
            if any(pattern.search(line) for pattern in PATTERNS):
                findings.append({'path': name, 'line': index, 'reason': 'sensitive_pattern_requires_review'})
        count += 1
    plugins = json.loads((ROOT / '.agents/plugins/marketplace.json').read_text())['plugins']
    for plugin in plugins:
        path = ROOT / plugin['source']['path']
        if not (path / 'plugin.json').is_file():
            findings.append({'path': str(path.relative_to(ROOT)), 'reason': 'marketplace_source_missing'})
    print(json.dumps({'status': 'fail' if findings else 'pass', 'files_checked': count,
                      'plugins_checked': len(plugins), 'findings': findings,
                      'limits': 'Name and high-confidence pattern checks plus explicit source review; not a complete secret detector.'}, ensure_ascii=False, indent=2))
    return bool(findings)


if __name__ == '__main__':
    sys.exit(main())
