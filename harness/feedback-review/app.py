"""Local expert-rule review journal. Every saved decision appends an immutable SQLite event."""
import json,sqlite3,os,uuid,hashlib,datetime
from pathlib import Path
from fastapi import FastAPI,HTTPException,Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel,Field

HERE=Path(__file__).resolve().parent
DATA=Path(os.getenv('REVIEW_DATA',str(HERE/'.data')));DATA.mkdir(parents=True,exist_ok=True)
CATALOG=Path(os.getenv('REVIEW_CATALOG',str(HERE/'catalog.json')))
app=FastAPI(title='Development Rule Review Journal')
app.add_middleware(TrustedHostMiddleware,allowed_hosts=['localhost','127.0.0.1','expert-review','testserver'])
def db():
 c=sqlite3.connect(DATA/'review.sqlite',timeout=20);c.row_factory=sqlite3.Row;c.execute('PRAGMA journal_mode=WAL');c.execute('PRAGMA foreign_keys=ON');return c
with db() as c:
 c.executescript('''CREATE TABLE IF NOT EXISTS decision_events(
 event_id INTEGER PRIMARY KEY AUTOINCREMENT, request_id TEXT UNIQUE NOT NULL, body_hash TEXT NOT NULL,
 rule_id TEXT NOT NULL, report_version TEXT NOT NULL, decision TEXT NOT NULL CHECK(decision IN ('adopt','reject','undecided')),
 reason TEXT NOT NULL, revision INTEGER NOT NULL, created_at TEXT NOT NULL, UNIQUE(rule_id,revision));
 CREATE INDEX IF NOT EXISTS decisions_by_rule ON decision_events(rule_id,event_id DESC);''')
with db() as c:
 if 'rule_snapshot' not in {row[1] for row in c.execute('PRAGMA table_info(decision_events)')}:
  c.execute("ALTER TABLE decision_events ADD COLUMN rule_snapshot TEXT NOT NULL DEFAULT '{}'")
def catalog():return json.loads(CATALOG.read_text())
def latest(c):
 return [dict(r) for r in c.execute('SELECT d.* FROM decision_events d JOIN (SELECT rule_id,MAX(revision) rev FROM decision_events GROUP BY rule_id) x ON x.rule_id=d.rule_id AND x.rev=d.revision ORDER BY d.event_id DESC')]
@app.middleware('http')
async def protect(request:Request,call_next):
 if request.method in ('POST','PUT','PATCH','DELETE'):
  origin=request.headers.get('origin')
  allowed=set(os.getenv('REVIEW_ORIGINS','http://localhost:8840,http://127.0.0.1:8840').split(','))
  if origin and origin not in allowed:return JSONResponse({'detail':'허용하지 않은 출처입니다.'},403)
  if not request.headers.get('content-type','').startswith('application/json'):return JSONResponse({'detail':'JSON 요청만 허용합니다.'},415)
 response=await call_next(request)
 response.headers['X-Content-Type-Options']='nosniff'
 response.headers['Cache-Control']='no-store'
 response.headers['Referrer-Policy']='no-referrer'
 response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
 return response
@app.get('/health')
def health():
 with db() as c:c.execute('SELECT 1')
 return {'status':'ok'}
@app.get('/api/catalog')
def get_catalog():return catalog()
@app.get('/api/decisions')
def decisions():
 with db() as c:return {'decisions':latest(c)}
class Decision(BaseModel):
 request_id:uuid.UUID
 rule_id:str=Field(min_length=1,max_length=100)
 decision:str=Field(pattern='^(adopt|reject|undecided)$')
 reason:str=Field(max_length=8000)
 expected_revision:int=Field(ge=0)
 report_version:str=Field(max_length=80)
@app.put('/api/decisions')
def save(d:Decision):
 report=catalog();snapshots={r['id']:{'expert':e['name'],'field':e['field'],'sources':e['sources'],**r} for e in report['experts'] for r in e['rules']};ids=set(snapshots)
 if d.rule_id not in ids:raise HTTPException(404,'규칙을 찾지 못했습니다.')
 if d.report_version!=report['version']:raise HTTPException(409,'보고서가 갱신됐습니다. 새 내용을 확인한 뒤 저장하세요.')
 if d.decision!='undecided' and not d.reason.strip():raise HTTPException(422,'채택 또는 거절 이유를 직접 입력해 주세요.')
 digest=hashlib.sha256(json.dumps(d.model_dump(mode='json'),sort_keys=True,ensure_ascii=False).encode()).hexdigest()
 with db() as c:
  c.execute('BEGIN IMMEDIATE')
  old=c.execute('SELECT * FROM decision_events WHERE request_id=?',(str(d.request_id),)).fetchone()
  if old:
   if old['body_hash']!=digest:raise HTTPException(409,'동일 요청 ID에 다른 내용이 있습니다.')
   return dict(old)
  current=c.execute('SELECT MAX(revision) FROM decision_events WHERE rule_id=?',(d.rule_id,)).fetchone()[0] or 0
  if current!=d.expected_revision:raise HTTPException(409,'다른 탭에서 판단이 바뀌었습니다. 현재 내용 새로고침 후 다시 저장하세요.')
  cur=c.execute('INSERT INTO decision_events(request_id,body_hash,rule_id,report_version,decision,reason,revision,created_at,rule_snapshot) VALUES(?,?,?,?,?,?,?,?,?)',(str(d.request_id),digest,d.rule_id,d.report_version,d.decision,d.reason.strip(),current+1,datetime.datetime.now(datetime.timezone.utc).isoformat(),json.dumps(snapshots[d.rule_id],ensure_ascii=False)))
  event=dict(c.execute('SELECT * FROM decision_events WHERE event_id=?',(cur.lastrowid,)).fetchone())
 return event
@app.get('/api/history/{rule_id}')
def history(rule_id:str):
 with db() as c:return {'events':[dict(r) for r in c.execute('SELECT * FROM decision_events WHERE rule_id=? ORDER BY revision DESC',(rule_id,))]}
@app.get('/api/export')
def export():
 report=catalog();rules={r['id']:{'expert':e['name'],'field':e['field'],**r} for e in report['experts'] for r in e['rules']}
 with db() as c:
  data=latest(c);total=c.execute('SELECT count(*) FROM decision_events').fetchone()[0]
 return {'report_version':report['version'],'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'event_count':total,'decisions':[{**d,'rule':json.loads(d.get('rule_snapshot') or '{}') or rules.get(d['rule_id'])} for d in data],'notice':'User choices are evidence for a later scoped plugin change. Saving a decision does not modify installed plugins.'}
app.mount('/',StaticFiles(directory=HERE/'static',html=True),name='static')
