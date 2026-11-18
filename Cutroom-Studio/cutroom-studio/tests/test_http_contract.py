from fastapi.testclient import TestClient
import pytest
from cutroom import api, config, store

@pytest.fixture
def client(tmp_path,monkeypatch):
    if store.POSTGRES: pytest.skip('These disposable tests explicitly exercise SQLite')
    monkeypatch.setattr(store,'DATA',tmp_path)
    monkeypatch.setattr(store,'MEDIA',tmp_path/'media')
    monkeypatch.setattr(config,'GUEST_ENABLED',True)
    with TestClient(api.app,base_url='http://testserver') as c: yield c


def test_session_upgrade_keeps_sample_project(client):
    g=client.post('/api/auth/guest'); assert g.status_code==201 and g.json()['guest']; assert 'HttpOnly' in g.headers['set-cookie']
    p=client.post('/api/samples/lunar/open');assert p.status_code==201
    id=p.json()['id']
    r=client.post('/api/auth/register',json={'name':'Example','email':'creator@example.test','password':'strong-pass-88110'});assert r.status_code==201
    assert r.json()['id']==g.json()['id'] and r.json()['plan']=='Creator'
    assert client.get('/api/projects/'+id).json()['clip_count']>=2
    assert client.post('/api/auth/logout').status_code==204
    assert client.get('/api/projects/'+id).status_code==401
    assert client.post('/api/auth/login',json={'email':'creator@example.test','password':'strong-pass-88110'}).status_code==200
    assert client.get('/api/projects/'+id).status_code==200


def test_cross_origin_writes_blocked(client):
    client.post('/api/auth/guest')
    response=client.post('/api/samples/lunar/open',headers={'Origin':'https://unrelated.example'})
    assert response.status_code==403
    assert client.get('/api/projects').json()==[]
    assert client.post('/api/samples/lunar/open',headers={'Origin':'http://testserver'}).status_code==201


def test_file_size_and_invalid_export_ids(client):
    client.post('/api/auth/guest')
    res=client.post('/api/projects',json={'bytes':3*1024**3,'filename':'big.mp4'})
    assert res.status_code==413
    res=client.get('/api/jobs/not-a-job-id/download')
    assert res.status_code==422
    assert client.get('/readyz').status_code==503
