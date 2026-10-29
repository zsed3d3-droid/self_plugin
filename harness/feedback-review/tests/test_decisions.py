import importlib.util,json,sqlite3,uuid
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
HERE=Path(__file__).resolve().parents[1]
@pytest.fixture
def service(tmp_path,monkeypatch):
 monkeypatch.setenv('REVIEW_DATA',str(tmp_path))
 spec=importlib.util.spec_from_file_location('review_test',HERE/'app.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 return module,TestClient(module.app),tmp_path

def body(**changes):
 return dict(request_id=str(uuid.uuid4()),rule_id='garry-1',decision='adopt',reason='신규 서비스 요구사항 누락을 줄이기 위해 사용한다.',expected_revision=0,report_version='2026-10-28.review-1',**changes)
def test_append_only_decision_history_and_restart(service):
 module,client,folder=service
 first=body();r=client.put('/api/decisions',json=first);assert r.status_code==200
 assert client.put('/api/decisions',json=first).json()['event_id']==r.json()['event_id']
 second=body();second.update(decision='reject',reason='작은 수정에서는 대화 단계가 과하다.',expected_revision=1)
 assert client.put('/api/decisions',json=second).json()['revision']==2
 assert client.get('/api/decisions').json()['decisions'][0]['decision']=='reject'
 assert len(client.get('/api/history/garry-1').json()['events'])==2
 # A fresh process connection sees both events, and the latest user reason.
 connection=sqlite3.connect(folder/'review.sqlite');assert connection.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
 assert connection.execute('SELECT count(*) FROM decision_events').fetchone()[0]==2
 assert connection.execute('SELECT reason FROM decision_events ORDER BY revision DESC LIMIT 1').fetchone()[0]==second['reason']
 another=TestClient(module.app)
 exported=another.get('/api/export').json();assert exported['event_count']==2
 assert exported['decisions'][0]['rule']['expert']=='Garry Tan'
 assert exported['decisions'][0]['reason']==second['reason']
def test_conflicting_tabs_do_not_overwrite(service):
 _,client,_=service
 with ThreadPoolExecutor(max_workers=2) as pool:
  codes=list(pool.map(lambda _:client.put('/api/decisions',json=body()).status_code,range(2)))
 assert sorted(codes)==[200,409]
 assert len(client.get('/api/history/garry-1').json()['events'])==1

def test_invalid_decisions_never_enter_journal(service):
 _,client,_=service
 for changes in [{'reason':''},{'rule_id':'missing'},{'decision':'delete'},{'report_version':'stale'}]:
  data=body();data.update(changes);assert client.put('/api/decisions',json=data).status_code in (404,409,422)
 assert client.get('/api/decisions').json()['decisions']==[]
def test_same_request_id_cannot_change_meaning(service):
 _,client,_=service;data=body();assert client.put('/api/decisions',json=data).status_code==200
 data['reason']='변경된 이유';assert client.put('/api/decisions',json=data).status_code==409

def test_cross_origin_and_rebinding_are_rejected(service):
 _,client,_=service
 assert client.put('/api/decisions',json=body(),headers={'Origin':'https://other.example'}).status_code==403
 assert client.get('/api/decisions',headers={'Host':'other.example'}).status_code==400

def test_catalog_rules_unique_and_actual_sources_present(service):
 _,client,_=service;catalog=client.get('/api/catalog').json();ids=[r['id'] for e in catalog['experts'] for r in e['rules']]
 assert len(ids)==len(set(ids))==30
 for e in catalog['experts']:
  assert e['good'] and e['bad'] and e['sources'] and e['action']['url'].startswith('https://github.com/')
