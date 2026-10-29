#!/usr/bin/env python3
"""Read the user's actual decisions without changing the database or guessing preferences."""
import argparse,json,sqlite3
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--db',type=Path,default=Path(__file__).resolve().parent/'.data/review.sqlite');p.add_argument('--history',action='store_true');a=p.parse_args()
if not a.db.is_file():raise SystemExit('No review database yet. Start the review service and save decisions.')
c=sqlite3.connect(a.db.resolve().as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row
query='SELECT * FROM decision_events ORDER BY event_id' if a.history else 'SELECT d.* FROM decision_events d JOIN (SELECT rule_id,MAX(revision) rev FROM decision_events GROUP BY rule_id) x ON x.rule_id=d.rule_id AND x.rev=d.revision ORDER BY d.rule_id'
print(json.dumps([dict(r) for r in c.execute(query)],ensure_ascii=False,indent=2))
