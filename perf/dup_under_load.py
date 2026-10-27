"""TC-E02 / RG-08: 부하 중에 같은 라운드 던지기 요청 2건을 동시에 보내도 1건만 처리되는가.

인스턴스가 여러 개면 두 요청이 서로 다른 인스턴스로 갈 수 있다 → DB 잠금(SELECT … FOR UPDATE)이 지켜 주는지 본다.
app 컨테이너 안에서 실행: docker compose exec -T app python - < perf/dup_under_load.py
"""
import json
import os
import threading
import urllib.error
import urllib.request

import psycopg

BASE = "http://lb"
PAIRS = 100


def call(path, body):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, r.headers.get("X-Instance")
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("X-Instance")


ok, cross_instance, ids = 0, 0, []
for _ in range(PAIRS):
    req = urllib.request.Request(BASE + "/api/matches", method="POST", headers={"Content-Type": "application/json"},
                                 data=json.dumps({"nickname": "DupCheck", "dice_count": 2}).encode())
    mid = json.loads(urllib.request.urlopen(req).read())["id"]
    ids.append(mid)
    results = []
    threads = [threading.Thread(target=lambda: results.append(call(f"/api/matches/{mid}/throw", {"round_no": 1})))
               for _ in range(2)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    ok += sorted(code for code, _ in results) == [200, 409]
    cross_instance += len({inst for _, inst in results}) > 1

db = psycopg.connect(os.environ["DATABASE_URL"])
dup = db.execute("select count(*) from (select match_id, round_no from rounds where match_id = any(%s)"
                 " group by 1, 2 having count(*) > 1) t", (ids,)).fetchone()[0]
rounds = db.execute("select count(*) from rounds where match_id = any(%s)", (ids,)).fetchone()[0]
print(json.dumps({"pairs": PAIRS, "exactly_one_ok": ok, "pairs_split_across_instances": cross_instance,
                  "db_rounds": rounds, "db_duplicate_rounds": dup}, ensure_ascii=False))
