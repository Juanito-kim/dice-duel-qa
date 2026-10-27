"""기능 검증 보조 스크립트: API·DB 수준 TC를 실행하고 실제 값을 기록한다.

화면(UI) TC는 브라우저에서 따로 수행하고, 이 스크립트는 명세 규칙을 API와 DB로 확인한다.
app 컨테이너 안에서 실행한다 (DB 직접 조회를 위해):
  docker compose exec -T app python - < scripts/functional_check.py
출력 한 줄 = TC 하나: "TC-ID | PASS/FAIL/BLOCKED | 실제 값"
"""
import itertools
import json
import os
import threading
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

import psycopg

BASE = os.getenv("BASE_URL", "http://lb")
KST = timezone(timedelta(hours=9))
db = psycopg.connect(os.environ["DATABASE_URL"], autocommit=True)


def call(method, path, body=None):
    req = urllib.request.Request(BASE + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            return res.status, json.loads(res.read()), dict(res.headers)
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null"), dict(e.headers)


def q(sql, *args):
    return db.execute(sql, args).fetchall()


def report(tc, ok, actual):
    print(f"{tc} | {'PASS' if ok else 'FAIL'} | {actual}")


def new_match(dice=2, nick="TCcheck", seed=None):
    body = {"nickname": nick, "dice_count": dice}
    if seed is not None:
        body["seed"] = seed
    return call("POST", "/api/matches", body)[1]["id"]


def play(mid, rolls):
    """rolls: [(플레이어 눈, 컴퓨터 눈), ...] 순서대로 지정하고 던진다. 마지막 응답을 돌려준다."""
    m = None
    for i, (p, c) in enumerate(rolls, start=1):
        call("POST", "/api/test/next-roll", {"match_id": mid, "player": p, "cpu": c})
        m = call("POST", f"/api/matches/{mid}/throw", {"round_no": i})[1]
    return m


LABEL = {"PLAYER": "플레이어 승리", "CPU": "컴퓨터 승리", "DRAW": "무승부"}

# ---------- A. 매치 시작 (API 수준) ----------
for tc, nick, expect in [("TC-A04", "가나다라마바사아자차", 200), ("TC-A07", " 유노", 400)]:
    st, body, _ = call("POST", "/api/matches", {"nickname": nick, "dice_count": 2})
    report(tc, st == expect, f"닉네임 {nick!r}({len(nick)}자) → {st} {body.get('detail', '') if isinstance(body, dict) else ''}")
before = q("select count(*) from matches")[0][0]
st, body, _ = call("POST", "/api/matches", {"nickname": "TCcheck", "dice_count": 4})
after = q("select count(*) from matches")[0][0]
report("TC-A09", st == 400 and before == after, f"dice_count=4 → {st}, 매치 수 {before}→{after}")

# ---------- B. 라운드 판정 (결정 테이블) ----------
cases = [("TC-B01", 2, [6, 5], [1, 2], "PLAYER"), ("TC-B02", 2, [1, 2], [6, 5], "CPU"),
         ("TC-B03", 2, [3, 3], [2, 4], "PLAYER"), ("TC-B04", 2, [2, 4], [3, 3], "CPU"),
         ("TC-B05", 2, [3, 3], [3, 3], "DRAW"), ("TC-B06", 2, [1, 4], [2, 3], "DRAW"),
         ("TC-B07", 3, [4, 4, 1], [3, 3, 3], "CPU"), ("TC-B08", 3, [4, 4, 1], [2, 2, 5], "DRAW")]
for tc, dice, p, c, expect in cases:
    m = play(new_match(dice), [(p, c)])
    got = m["rounds"][0]["result"]
    report(tc, got == expect,
           f"#{m['id']} {p} vs {c} → {LABEL[got]} (기대 {LABEL[expect]}), 스코어 {m['player_wins']}:{m['cpu_wins']}")

# ---------- C. 매치 진행·종료 ----------
WIN, LOSE, DRAW = ([6, 6], [1, 2]), ([1, 2], [6, 6]), ([1, 4], [2, 3])
m = play(new_match(), [WIN] * 3)
c01_id = m["id"]
report("TC-C01", m["status"] == "FINISHED" and m["result"] == "PLAYER" and m["rounds_played"] == 3,
       f"#{m['id']} 3승 후 status={m['status']} result={m['result']} rounds={m['rounds_played']} (버튼은 UI에서 확인)")
m = play(new_match(), [DRAW, DRAW, WIN, WIN, WIN])
report("TC-C02", m["rounds_played"] == 5 and (m["player_wins"], m["cpu_wins"], m["draws"]) == (3, 0, 2),
       f"#{m['id']} rounds={m['rounds_played']} 스코어 {m['player_wins']}:{m['cpu_wins']} 무승부 {m['draws']}")
m = play(new_match(), [WIN, LOSE, WIN, LOSE] + [DRAW] * 6)
report("TC-C03", m["rounds_played"] == 10 and m["result"] == "DRAW",
       f"#{m['id']} rounds={m['rounds_played']} 2:2 무6 → result={m['result']}")
m = play(new_match(), [WIN, WIN, LOSE] + [DRAW] * 7)
report("TC-C04", m["rounds_played"] == 10 and m["result"] == "PLAYER",
       f"#{m['id']} rounds={m['rounds_played']} 2:1 무7 → result={m['result']}")
st, _, _ = call("POST", f"/api/matches/{c01_id}/throw", {"round_no": 4})
rounds = q("select count(*) from rounds where match_id=%s", c01_id)[0][0]
report("TC-C05", st == 409 and rounds == 3, f"끝난 매치 #{c01_id}에 던지기 → {st}, DB 라운드 수 {rounds}")

# ---------- D. seed ----------
a, b = new_match(seed=777777), new_match(seed=777777)
for mid in (a, b):
    for i in range(1, 6):  # 3승으로 먼저 끝나면 이후 요청은 409로 거부된다
        call("POST", f"/api/matches/{mid}/throw", {"round_no": i})
da = [(r["player_dice"], r["cpu_dice"]) for r in call("GET", f"/api/matches/{a}")[1]["rounds"]]
db_ = [(r["player_dice"], r["cpu_dice"]) for r in call("GET", f"/api/matches/{b}")[1]["rounds"]]
report("TC-D01", da == db_ and len(da) > 0, f"seed 777777 매치 #{a}·#{b}, 라운드 {len(da)}개 비교, 같음={da == db_}, 1라운드 {da[0] if da else '-'}")

# ---------- E. 중복 던지기 ----------
mid = new_match()
call("POST", f"/api/matches/{mid}/throw", {"round_no": 1})
st, _, _ = call("POST", f"/api/matches/{mid}/throw", {"round_no": 1})
rp = q("select rounds_played from matches where id=%s", mid)[0][0]
report("TC-E01", st == 409 and rp == 1, f"#{mid} round_no=1 재요청 → {st}, rounds_played={rp}")

ok_runs, results = 0, []
for _ in range(100):
    mid = new_match()
    codes = []
    th = [threading.Thread(target=lambda: codes.append(call("POST", f"/api/matches/{mid}/throw", {"round_no": 1})[0]))
          for _ in range(2)]
    [t.start() for t in th]
    [t.join() for t in th]
    ok_runs += sorted(codes) == [200, 409]
dup = q("select count(*) from (select match_id, round_no from rounds group by 1, 2 having count(*) > 1) t")[0][0]
report("TC-E02", ok_runs == 100 and dup == 0, f"동시 요청 2건 × 100회: 1건만 200인 회차 {ok_runs}/100, DB 중복 라운드 {dup}건")

# ---------- F. 통계 (API·DB 수준) ----------
# F03 기간 경계: 테스트 모드로 시작 시각을 지정한 매치 2개
yesterday = (datetime.now(KST) - timedelta(days=1)).date()
edge_a = datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59, tzinfo=KST)
edge_b = edge_a + timedelta(seconds=1)
for nick, t in [("EdgeLast", edge_a), ("EdgeFirst", edge_b)]:
    call("POST", "/api/matches", {"nickname": nick, "dice_count": 2, "created_at": t.isoformat()})
_, rows, _ = call("GET", f"/api/matches?nickname=Edge&date_to={yesterday}&limit=100")
names = sorted({r["nickname"] for r in rows})
report("TC-F03", names == ["EdgeLast"], f"종료일={yesterday} → {names} (23:59:59 포함, 다음 날 00:00:00 제외)")

# F04 기간 역전: 기대 결과 없음 → 실제 동작만 기록
st, rows, hdr = call("GET", f"/api/matches?date_from={datetime.now(KST).date()}&date_to={yesterday}")
print(f"TC-F04 | BLOCKED | 명세 없음. 실제: {st}, {len(rows)}건, 안내 없음 → SPEC-002")

_, rows, _ = call("GET", "/api/matches?limit=5&sort=created_at&order=asc")
diff = []
for r in rows:
    d = q("select rounds_played, player_wins, cpu_wins, status from matches where id=%s", r["id"])[0]
    if d != (r["rounds_played"], r["player_wins"], r["cpu_wins"], r["status"]):
        diff.append(r["id"])
report("TC-F07", not diff, f"매치 {[r['id'] for r in rows]} API와 DB 비교, 다른 건 {diff}")

for dice in (2, 3):
    _, dist, _ = call("GET", f"/api/stats/sum-distribution?dice_count={dice}")
    dbc = dict(q("select s, count(*) from (select r.player_sum s from rounds r join matches m on m.id=r.match_id"
                 " where m.dice_count=%s and not r.forced union all select r.cpu_sum from rounds r join matches m"
                 " on m.id=r.match_id where m.dice_count=%s and not r.forced) t group by s", dice, dice))
    api_c = {r["sum"]: r["count"] for r in dist["rows"] if r["count"]}
    n = q("select count(*) from rounds r join matches m on m.id=r.match_id where m.dice_count=%s and not r.forced", dice)[0][0]
    if dice == 2:
        report("TC-F08", api_c == dbc and dist["total"] == n * 2,
               f"2개: 합계별 횟수 API=DB {api_c == dbc}, 표본 {dist['total']} = 라운드 {n} × 2")
    theory = {}
    for faces in itertools.product(range(1, 7), repeat=dice):
        theory[sum(faces)] = theory.get(sum(faces), 0) + 1
    bad = [r["sum"] for r in dist["rows"] if abs(r["theory_ratio"] - theory[r["sum"]] / 6 ** dice) > 0.00005]
    sample = {2: 7, 3: 10}[dice]
    tr = next(r["theory_ratio"] for r in dist["rows"] if r["sum"] == sample)
    if dice == 3:
        report("TC-F10", [r["sum"] for r in dist["rows"]] == list(range(3, 19)), f"3개 합계 {dist['rows'][0]['sum']}~{dist['rows'][-1]['sum']}, {len(dist['rows'])}행")
    print(f"TC-F09({dice}개) | {'PASS' if not bad else 'FAIL'} | 이론 비율 불일치 {bad}, 예: 합 {sample} = {tr * 100:.2f}%")

_, players, _ = call("GET", "/api/stats/players")
fin_only = [p for p in players if p["total_matches"] == p["finished_matches"] and p["finished_matches"] > 0]
bad12 = [p["nickname"] for p in fin_only if abs(p["win_rate"] - p["wins"] / p["finished_matches"]) > 0.00005]
report("TC-F12", not bad12, f"끝난 매치만 있는 {len(fin_only)}명, 불일치 {bad12}")

with_live = [p for p in players if p["total_matches"] > p["finished_matches"] and p["finished_matches"] > 0]
lines, bad13 = [], []
for p in with_live:
    correct = p["wins"] / p["finished_matches"]
    lines.append(f"{p['nickname']} 화면 {p['win_rate'] * 100:.2f}% vs DB {correct * 100:.2f}% ({p['wins']}/{p['finished_matches']})")
    if abs(p["win_rate"] - correct) > 0.00005:
        bad13.append(p["nickname"])
report("TC-F13", not bad13, "; ".join(lines))

correct_rank = sorted(players, key=lambda p: (-(p["wins"] / p["finished_matches"] if p["finished_matches"] else 0),
                                              -p["finished_matches"], p["nickname"]))
api_order = [p["nickname"] for p in players]
ok_order = [p["nickname"] for p in correct_rank]
moved = [f"{n} {api_order.index(n) + 1}위→{ok_order.index(n) + 1}위" for n in api_order if api_order.index(n) != ok_order.index(n)]
report("TC-F15", api_order == ok_order, f"순위가 다른 닉네임: {moved}")

# ---------- G. 사용자 흐름 ----------
old = q("select count(*) from matches where status='IN_PROGRESS' and created_at < now() - interval '1 day'")[0][0]
oldest = q("select id, nickname, rounds_played, created_at::text from matches where status='IN_PROGRESS' order by created_at limit 1")
print(f"TC-G01 | BLOCKED | 명세 없음. 하루 넘게 '진행 중'인 매치 {old}건, 가장 오래된 것 {oldest} → SPEC-001")
