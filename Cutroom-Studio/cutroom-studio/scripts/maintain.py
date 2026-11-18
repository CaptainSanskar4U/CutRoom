"""Operator-only age-based cleanup. Dry run by default; no registered accounts are removed."""
import argparse, json, shutil
from cutroom import store, media, config
from cutroom.store import db, NOW, lock_suffix

SQL="""SELECT u.id FROM users u WHERE u.email IS NULL AND u.created<?
AND NOT EXISTS(SELECT 1 FROM sessions s WHERE s.user_id=u.id AND s.expires>?)
AND NOT EXISTS(SELECT 1 FROM jobs j WHERE j.user_id=u.id AND j.status IN ('running','queued'))"""

def main():
    p=argparse.ArgumentParser();p.add_argument('--guest-days',type=int,default=14);p.add_argument('--apply',action='store_true');a=p.parse_args()
    if a.guest_days<7: p.error('Allow at least 7 days after guest workspace creation')
    store.init();now=NOW();projects=[];jobs=[];guests=[]
    with db(a.apply) as c:
        old=c.execute(SQL+(lock_suffix() if a.apply else ''),(now-a.guest_days*86400,now)).fetchall()
        expired=c.execute('SELECT COUNT(*) AS n FROM sessions WHERE expires<=?',(now,)).fetchone()['n']
        if a.apply: c.execute('DELETE FROM sessions WHERE expires<=?',(now,)); c.execute('DELETE FROM throttles WHERE since<?',(now-86400,))
        for row in old:
            user=row['id'];guests.append(user)
            projects.extend(r['id'] for r in c.execute('SELECT id FROM projects WHERE user_id=?',(user,)).fetchall())
            jobs.extend(r['id'] for r in c.execute("SELECT id FROM jobs WHERE user_id=? AND kind='render'",(user,)).fetchall())
            if a.apply: c.execute('DELETE FROM users WHERE id=? AND email IS NULL',(user,))
    if a.apply:
        for id in projects: shutil.rmtree(media.project_dir(id),ignore_errors=True)
        for id in jobs: shutil.rmtree(media.export_dir(id),ignore_errors=True)
        for id in guests: shutil.rmtree(config.MEDIA/'assets'/id,ignore_errors=True)
    print(json.dumps({'dry_run':not a.apply,'expired_sessions':expired,'expired_guest_workspaces':len(guests),'guest_projects':len(projects),'guest_exports':len(jobs)}))

if __name__=='__main__': main()
