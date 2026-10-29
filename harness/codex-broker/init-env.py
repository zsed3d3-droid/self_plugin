#!/usr/bin/env python3
"""Create fresh private local configuration; never read an existing Codex login."""
import os
from pathlib import Path
import secrets

path = Path(__file__).resolve().parent / '.env'
password = secrets.token_hex(32)
content = (f'POSTGRES_PASSWORD={password}\n'
           f'BROKER_DATABASE_URL=postgresql://broker:{password}@db:5432/broker\n'
           f'BROKER_TOKEN={secrets.token_urlsafe(48)}\n')
try:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
except FileExistsError:
    raise SystemExit('Private .env already exists; preserved unchanged.')
with os.fdopen(fd, 'w') as output:
    output.write(content)
print('Created private .env with new local-only credentials. No values printed.')
