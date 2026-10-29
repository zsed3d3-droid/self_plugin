#!/usr/bin/env python3
"""Generate independent local credentials. Refuse to replace an existing file."""
import os, secrets
from pathlib import Path
path = Path(__file__).resolve().parent / '.env'
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as stream:
    stream.write('MEMORY_PORT=8852\nMEMORY_DB_PASSWORD=' + secrets.token_hex(32) + '\nMEMORY_API_TOKEN=' + secrets.token_hex(32) + '\n')
print('Created private .env with new credentials. Values are not printed.')
