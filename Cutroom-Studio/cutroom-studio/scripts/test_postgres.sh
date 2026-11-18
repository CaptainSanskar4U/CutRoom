#!/usr/bin/env bash
# A disposable non-public cluster that verifies PostgreSQL queue and ownership paths.
set -euo pipefail
cd "$(dirname "$0")/.."
PGBIN="${PGBIN:-/usr/lib/postgresql/17/bin}"
work="$(mktemp -d /tmp/cutroom-pg-XXXXXX)"
trap '"$PGBIN/pg_ctl" -D "$work/db" -m immediate stop >/dev/null 2>&1 || :; rm -rf "$work"' EXIT
"$PGBIN/initdb" -D "$work/db" --no-locale --encoding=UTF8 --auth=trust >/dev/null
"$PGBIN/pg_ctl" -D "$work/db" -l "$work/postgres.log" -o "-F -h '' -k $work" -w start >/dev/null
export DATABASE_URL="postgresql:///postgres?host=$work" CUTROOM_DATA="$work/media"
.venv/bin/python - <<'PY'
from fastapi.testclient import TestClient
from cutroom import api, store, worker
assert store.POSTGRES
with TestClient(api.app) as client:
    user=client.post('/api/auth/register',json={'email':'pg-test@example.test','name':'PG Test','password':'strong-test-0815'})
    assert user.status_code==201, user.text
    p=client.post('/api/samples/lunar/open');assert p.status_code==201,p.text
    data=client.get('/api/projects/'+p.json()['id']).json(); assert len(data['clips'])>=2 and data['info']['face_frames']>0
    exp=client.post('/api/clips/'+data['clips'][0]['id']+'/render',json={'resolution':480});assert exp.status_code==202,exp.text
    j=store.claim('pg-test-worker'); assert j['kind']=='render' and j['id']==exp.json()['id']; assert store.claim('other-worker') is None
    worker.run_job(j)
    status=client.get('/api/jobs/'+j['id']).json();assert status['status']=='done',status
    res=client.get('/api/jobs/'+j['id']+'/download',headers={'Range':'bytes=0-511'}); assert res.status_code==206 and len(res.content)==512
    assert client.get('/api/usage').json()['exports']==1
    assert client.post('/api/auth/logout').status_code==204
    assert client.get('/api/jobs/'+j['id']+'/download').status_code==401
print('PostgreSQL integration passed: schema, auth, sample, exclusive claim, real FFmpeg, authenticated HTTP Range, usage.')
PY
