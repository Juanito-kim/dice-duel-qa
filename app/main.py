"""API: 화면·Generator 요청을 받아 Processor로 판정하고 DB에 저장한다.

API와 Processor는 한 서비스 안에서 모듈만 나눴다 (processor.py).
"""
import logging
import os
import random
import socket
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from pydantic import BaseModel

import processor

TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"
INSTANCE = socket.gethostname()  # 여러 인스턴스를 띄웠을 때 log·응답에서 구분용
KST = timezone(timedelta(hours=9))
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


# ---------- log ----------
# 형식: 2026-10-26 14:00:00 ERROR [인스턴스] 메시지  → monitoring/ 스크립트가 이 형식을 필터링한다.
class KstFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        return datetime.fromtimestamp(record.created, KST).strftime("%Y-%m-%d %H:%M:%S")


formatter = KstFormatter(f"%(asctime)s %(levelname)s [{INSTANCE}] %(message)s")
log = logging.getLogger("dice")
log.setLevel(logging.INFO)
log.propagate = False
handler = logging.StreamHandler()
handler.setFormatter(formatter)
log.addHandler(handler)
# LOG_DIR이 있으면 인스턴스별 파일에도 쓴다 → monitoring/log_monitor.py가 모아서 ERROR를 걸러낸다
if os.getenv("LOG_DIR"):
    os.makedirs(os.environ["LOG_DIR"], exist_ok=True)
    file_handler = logging.FileHandler(os.path.join(os.environ["LOG_DIR"], f"app-{INSTANCE}.log"), encoding="utf-8")
    file_handler.setFormatter(formatter)
    log.addHandler(file_handler)

pool = ConnectionPool(
    os.environ["DATABASE_URL"],
    kwargs={"row_factory": dict_row, "options": "-c TimeZone=Asia/Seoul"},
    min_size=1,
    max_size=10,
    open=True,
)

app = FastAPI(title="Dice Duel API", version="1.0")


@app.middleware("http")
async def add_instance_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Instance"] = INSTANCE
    return response


# ---------- 요청 형식 ----------
class MatchCreate(BaseModel):
    nickname: str
    dice_count: int
    seed: int | None = None
    source: str = "web"
    created_at: datetime | None = None  # 테스트 모드 전용: 초기 데이터의 시작 시각을 과거로 지정


class ThrowRequest(BaseModel):
    round_no: int


class NextRoll(BaseModel):
    match_id: int
    player: list[int]
    cpu: list[int]


# ---------- 공통 ----------
def load_match(conn, match_id: int) -> dict | None:
    match = conn.execute("SELECT * FROM matches WHERE id = %s", (match_id,)).fetchone()
    if match is None:
        return None
    match["rounds"] = conn.execute(
        "SELECT round_no, player_dice, cpu_dice, player_sum, cpu_sum, result, forced"
        " FROM rounds WHERE match_id = %s ORDER BY round_no",
        (match_id,),
    ).fetchall()
    return match


def reject(status: int, level: int, message: str, detail: str):
    log.log(level, message)
    raise HTTPException(status_code=status, detail=detail)


# ---------- 화면 ----------
# no-store: 앱을 다시 빌드한 뒤 브라우저가 예전 화면을 보여주지 않게 한다
NO_CACHE = {"Cache-Control": "no-store"}


@app.get("/", include_in_schema=False)
def game_page():
    return FileResponse(os.path.join(STATIC_DIR, "game.html"), headers=NO_CACHE)


@app.get("/stats", include_in_schema=False)
def stats_page():
    return FileResponse(os.path.join(STATIC_DIR, "stats.html"), headers=NO_CACHE)


@app.get("/health")
def health():
    with pool.connection() as conn:
        conn.execute("SELECT 1")
    return {"status": "ok", "instance": INSTANCE, "test_mode": TEST_MODE}


# ---------- 매치 ----------
@app.post("/api/matches")
def create_match(body: MatchCreate):
    if body.dice_count not in processor.DICE_COUNTS:
        reject(400, logging.ERROR,
               f"match rejected: invalid dice_count={body.dice_count} nickname={body.nickname!r}",
               "주사위 개수는 2개 또는 3개만 고를 수 있습니다.")
    if not processor.is_valid_nickname(body.nickname):
        reject(400, logging.ERROR,
               f"match rejected: invalid nickname={body.nickname!r}",
               "닉네임은 2~10자의 한글·영문·숫자만 사용할 수 있습니다.")

    seed = body.seed if body.seed is not None else random.randint(1, 2**31 - 1)
    created_at = body.created_at if (TEST_MODE and body.created_at) else datetime.now(KST)

    with pool.connection() as conn:
        match_id = conn.execute(
            "INSERT INTO matches (nickname, dice_count, seed, source, created_at)"
            " VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (body.nickname, body.dice_count, seed, body.source, created_at),
        ).fetchone()["id"]
        log.info(f"match created id={match_id} nickname={body.nickname} dice={body.dice_count} seed={seed}")
        return load_match(conn, match_id)


@app.get("/api/matches/{match_id}")
def get_match(match_id: int):
    with pool.connection() as conn:
        match = load_match(conn, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="매치를 찾을 수 없습니다.")
    return match


@app.post("/api/matches/{match_id}/throw")
def throw(match_id: int, body: ThrowRequest):
    with pool.connection() as conn, conn.transaction():
        # FOR UPDATE: 같은 매치에 동시에 온 요청을 한 줄로 세운다 (R-09)
        match = conn.execute("SELECT * FROM matches WHERE id = %s FOR UPDATE", (match_id,)).fetchone()
        if match is None:
            reject(404, logging.ERROR, f"throw rejected: match not found id={match_id}",
                   "매치를 찾을 수 없습니다.")
        if match["status"] == "FINISHED":
            reject(409, logging.ERROR,
                   f"throw rejected: match already finished id={match_id} round_no={body.round_no}",
                   "이미 끝난 매치입니다.")
        expected = match["rounds_played"] + 1
        if body.round_no != expected:
            reject(409, logging.WARNING,
                   f"throw rejected: duplicate round id={match_id} round_no={body.round_no} expected={expected}",
                   "이미 처리된 라운드입니다.")

        forced = conn.execute(
            "DELETE FROM forced_rolls WHERE match_id = %s RETURNING player_dice, cpu_dice", (match_id,)
        ).fetchone()
        if forced:
            player, cpu = forced["player_dice"], forced["cpu_dice"]
        else:
            player, cpu = processor.roll(match["seed"], expected, match["dice_count"])

        round_result = processor.judge_round(player, cpu)
        player_wins = match["player_wins"] + (round_result == "PLAYER")
        cpu_wins = match["cpu_wins"] + (round_result == "CPU")
        draws = match["draws"] + (round_result == "DRAW")
        match_result = processor.judge_match(player_wins, cpu_wins, expected)

        conn.execute(
            "INSERT INTO rounds (match_id, round_no, player_dice, cpu_dice, player_sum, cpu_sum, result, forced)"
            " VALUES (%s, %s, %s::int[], %s::int[], %s, %s, %s, %s)",
            (match_id, expected, player, cpu, sum(player), sum(cpu), round_result, forced is not None),
        )
        conn.execute(
            "UPDATE matches SET rounds_played = %s, player_wins = %s, cpu_wins = %s, draws = %s,"
            " result = %s, status = %s, finished_at = %s WHERE id = %s",
            (expected, player_wins, cpu_wins, draws, match_result,
             "FINISHED" if match_result else "IN_PROGRESS",
             datetime.now(KST) if match_result else None, match_id),
        )
        log.info(f"round processed id={match_id} round={expected} player={player} cpu={cpu} result={round_result}")
        if match_result:
            log.info(f"match finished id={match_id} result={match_result} score={player_wins}:{cpu_wins}")

    with pool.connection() as conn:
        return load_match(conn, match_id)


@app.get("/api/matches")
def list_matches(response: Response, nickname: str = "", date_from: str = "", date_to: str = "",
                 sort: str = "created_at", order: str = "desc", limit: int = 100, offset: int = 0):
    """S-01: 닉네임 부분 일치·기간(YYYY-MM-DD, KST) 필터, 정렬.
    U-02: limit·offset으로 나눠 가져오고, 필터에 맞는 전체 건수는 X-Total-Count 헤더로 알려준다."""
    sort_columns = {"created_at", "nickname", "result", "rounds_played"}
    if sort not in sort_columns:
        sort = "created_at"
    direction = "ASC" if order.lower() == "asc" else "DESC"

    where, params = [], []
    if nickname:
        where.append("nickname ILIKE %s")
        params.append(f"%{nickname}%")
    if date_from:
        where.append("created_at >= %s::date")
        params.append(date_from)
    if date_to:
        where.append("created_at < %s::date + 1")
        params.append(date_to)
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    with pool.connection() as conn:
        total = conn.execute(f"SELECT count(*) AS n FROM matches {where_sql}", params).fetchone()["n"]
        response.headers["X-Total-Count"] = str(total)
        return conn.execute(
            f"SELECT id, nickname, dice_count, status, rounds_played, player_wins, cpu_wins, draws,"
            f" result, source, created_at FROM matches {where_sql}"
            f" ORDER BY {sort} {direction}, id {direction} LIMIT %s OFFSET %s",
            (*params, min(limit, 1000), max(offset, 0)),
        ).fetchall()


# ---------- 통계 ----------
@app.get("/api/stats/sum-distribution")
def sum_distribution(dice_count: int = 2):
    """S-02: 플레이어·컴퓨터의 모든 라운드 합계 분포와 이론 분포. 눈을 지정한 라운드(forced)는 제외."""
    with pool.connection() as conn:
        rows = conn.execute(
            "SELECT s, count(*) AS cnt FROM ("
            "  SELECT r.player_sum AS s FROM rounds r JOIN matches m ON m.id = r.match_id"
            "   WHERE m.dice_count = %s AND NOT r.forced"
            "  UNION ALL"
            "  SELECT r.cpu_sum FROM rounds r JOIN matches m ON m.id = r.match_id"
            "   WHERE m.dice_count = %s AND NOT r.forced"
            ") t GROUP BY s",
            (dice_count, dice_count),
        ).fetchall()
    counts = {row["s"]: row["cnt"] for row in rows}
    total = sum(counts.values())
    theory = processor.theoretical_distribution(dice_count)
    return {
        "dice_count": dice_count,
        "total": total,
        "rows": [
            {"sum": s, "count": counts.get(s, 0),
             "actual_ratio": round(counts.get(s, 0) / total, 4) if total else 0,
             "theory_ratio": round(p, 4)}
            for s, p in theory.items()
        ],
    }


@app.get("/api/stats/players")
def player_stats():
    """S-04: 플레이어별 승률 = 승리 매치 ÷ 끝난 매치."""
    with pool.connection() as conn:
        rows = conn.execute(
            "SELECT nickname,"
            " count(*) AS total_matches,"
            " count(*) FILTER (WHERE status = 'FINISHED') AS finished_matches,"
            " count(*) FILTER (WHERE result = 'PLAYER') AS wins"
            " FROM matches GROUP BY nickname ORDER BY nickname"
        ).fetchall()
    for row in rows:
        # PLANTED BUG-003: 분모에 진행 중인 매치까지 넣는다. S-04에 따르면 finished_matches로 나눠야 한다.
        row["win_rate"] = round(row["wins"] / row["total_matches"], 4) if row["total_matches"] else 0
    # 승률 순위: 승률 높은 순, 같으면 끝난 매치 많은 순, 그다음 닉네임 순
    rows.sort(key=lambda r: (-r["win_rate"], -r["finished_matches"], r["nickname"]))
    return rows


# ---------- 테스트 모드 전용 ----------
@app.post("/api/test/next-roll")
def set_next_roll(body: NextRoll):
    """R-07: 다음 라운드의 눈을 지정한다. TEST_MODE=true일 때만 동작."""
    if not TEST_MODE:
        reject(403, logging.WARNING, f"next-roll rejected: test mode off id={body.match_id}",
               "테스트 모드에서만 사용할 수 있습니다.")
    with pool.connection() as conn:
        match = conn.execute("SELECT * FROM matches WHERE id = %s", (body.match_id,)).fetchone()
        if match is None or match["status"] == "FINISHED":
            raise HTTPException(status_code=400, detail="진행 중인 매치가 아닙니다.")
        dice_ok = all(1 <= d <= 6 for d in body.player + body.cpu)
        if len(body.player) != match["dice_count"] or len(body.cpu) != match["dice_count"] or not dice_ok:
            raise HTTPException(status_code=400, detail="주사위 개수 또는 눈 값이 올바르지 않습니다.")
        conn.execute(
            "INSERT INTO forced_rolls (match_id, player_dice, cpu_dice) VALUES (%s, %s::int[], %s::int[])"
            " ON CONFLICT (match_id) DO UPDATE SET player_dice = EXCLUDED.player_dice, cpu_dice = EXCLUDED.cpu_dice",
            (body.match_id, body.player, body.cpu),
        )
    log.info(f"test next-roll set id={body.match_id} player={body.player} cpu={body.cpu}")
    return {"match_id": body.match_id, "player": body.player, "cpu": body.cpu}
