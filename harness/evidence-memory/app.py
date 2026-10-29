"""Container adapter for the scoped evidence library; no model or session service."""
import os, uuid, secrets
from pathlib import Path
from contextlib import asynccontextmanager
import psycopg
from psycopg.rows import dict_row
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from memory import import_events, search, redact


def db():
    return psycopg.connect(os.environ['DATABASE_URL'], row_factory=dict_row, connect_timeout=5)


@asynccontextmanager
async def lifespan(_):
    if len(os.environ.get('MEMORY_API_TOKEN', '')) < 32:
        raise RuntimeError('Set a new MEMORY_API_TOKEN of at least 32 characters')
    with db() as connection:
        connection.execute((Path(__file__).parent / 'schema.sql').read_text(), prepare=False)
    yield


app = FastAPI(title='Scoped evidence memory', lifespan=lifespan)


@app.middleware('http')
async def authenticate(request: Request, call_next):
    if request.url.path.startswith('/api/'):
        expected = os.environ.get('MEMORY_API_TOKEN', '')
        supplied = request.headers.get('Authorization', '')
        if not expected or not secrets.compare_digest(supplied, 'Bearer ' + expected):
            return JSONResponse({'detail': 'Authentication required'}, 401)
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


@app.exception_handler(psycopg.Error)
async def database_error(_, error):
    return JSONResponse({'detail': 'Database operation could not be completed. No partial change was accepted.'}, 503)


@app.get('/health')
def health():
    with db() as connection:
        connection.execute('SELECT 1')
    return {'status': 'ok'}


class MemoryScope(BaseModel):
    project: str = Field(default='personal', min_length=1, max_length=100)
    topic: str = Field(default='general', min_length=1, max_length=100)
    purpose: str = Field(default='development', min_length=1, max_length=100)


class Import(MemoryScope):
    text: str = Field(min_length=1, max_length=1000000)
    source: str = Field(min_length=1, max_length=200)
    format: str = Field(default='text', pattern='^(text|jsonl)$')


@app.post('/api/memory/import')
def memory_import(data: Import):
    try:
        with db() as connection:
            return import_events(connection, data.text, data.source, data.format, data.project, data.topic, data.purpose)
    except (ValueError, TypeError, KeyError):
        raise HTTPException(422, 'Invalid import format; nothing was stored')


@app.get('/api/memory/search')
def memory_search(q: str = '', project: str = 'personal', topic: str | None = None, purpose: str | None = None):
    with db() as connection:
        return search(connection, q, project, 8, topic, purpose)


class RetrievalFeedback(MemoryScope):
    evidence_id: str = Field(min_length=1, max_length=100)
    kind: str = Field(pattern='^(suppress|correct|unsuppress)$')
    reason: str = Field(min_length=1, max_length=8000)
    correction: str | None = Field(default=None, max_length=12000)


@app.post('/api/memory/retrieval-feedback')
def retrieval_feedback(data: RetrievalFeedback):
    if not data.reason.strip() or (data.kind == 'correct' and not (data.correction or '').strip()):
        raise HTTPException(422, 'A reason and corrected meaning are required')
    with db() as connection:
        evidence = connection.execute('SELECT id FROM evidence WHERE id=%s AND project=%s AND topic=%s AND purpose=%s',
            (data.evidence_id, data.project, data.topic, data.purpose)).fetchone()
        if not evidence:
            raise HTTPException(404, 'Evidence not found in this scope')
        identifier = str(uuid.uuid4())
        connection.execute('''INSERT INTO retrieval_feedback(id,evidence_id,project,topic,purpose,kind,reason,correction)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s)''',
            (identifier, data.evidence_id, data.project, data.topic, data.purpose, data.kind, redact(data.reason), redact(data.correction) if data.correction else None))
    return {'id': identifier, 'evidence_id': data.evidence_id, 'kind': data.kind, 'original_preserved': True}
