"""Generator: 봇 플레이어의 매치를 API로 만든다. 화면과 같은 API → Processor 경로를 탄다.

용도
  초기 데이터 : python generator.py --matches 200 --seed 42 --spread-days 7 --only-if-empty
  부하 테스트 : python generator.py --matches 1000 --concurrency 20 --out /results/run.json
  이상값 주입 : --inject-errors 0.1  (매치의 10%에 잘못된 닉네임·끝난 매치 던지기·중복 던지기·중도 이탈)

같은 --seed면 어떤 매치를 만들지(닉네임, 주사위 개수, 매치 seed, 이상값 종류)가 항상 같다.
표준 라이브러리만 쓴다.
"""
import argparse
import json
import random
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
# 봇 플레이어 10명: 로마 신화의 신 (모두 R-06 범위 안. 유노는 최소 길이 2자)
BOT_NAMES = ["유피테르", "유노", "미네르바", "아폴로", "디아나",
             "메르쿠리우스", "넵투누스", "플루토", "베누스", "바쿠스"]
ERROR_KINDS = ["invalid_nickname", "throw_after_finish", "duplicate_throw", "abandon"]


class Stats:
    """요청별 상태 코드·응답 시간·처리 인스턴스를 모은다 (TC-004 결과용)."""

    def __init__(self):
        self.lock = threading.Lock()
        self.latencies = []
        self.status_counts = {}
        self.instance_counts = {}

    def add(self, status, seconds, instance):
        with self.lock:
            self.latencies.append(seconds)
            self.status_counts[status] = self.status_counts.get(status, 0) + 1
            self.instance_counts[instance] = self.instance_counts.get(instance, 0) + 1


def call(base_url, method, path, body, stats):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base_url + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            status, payload, instance = res.status, json.loads(res.read()), res.headers.get("X-Instance", "-")
    except urllib.error.HTTPError as e:
        status, payload, instance = e.code, None, e.headers.get("X-Instance", "-")
    except Exception:
        status, payload, instance = "conn_error", None, "-"
    stats.add(status, time.perf_counter() - start, instance)
    return status, payload


def play_match(base_url, index, total, master_seed, error_ratio, spread_days, started_at, stats):
    rng = random.Random(f"{master_seed}-{index}")
    nickname = rng.choice(BOT_NAMES)
    body = {"nickname": nickname, "dice_count": rng.choice([2, 3]),
            "seed": rng.randint(1, 2**31 - 1), "source": "generator"}
    if spread_days:
        # 최근 N일을 매치 수만큼 칸으로 나눠 앞에서부터 차례로 배정한다 (칸 안에서만 무작위).
        # 매치 번호(저장 순서)와 시작 시각 순서가 같아져 실제 서비스 데이터처럼 보인다.
        slot = (index + rng.random()) / total
        body["created_at"] = (started_at - timedelta(days=spread_days * (1 - slot))).isoformat()
    error_kind = rng.choice(ERROR_KINDS) if rng.random() < error_ratio else None

    if error_kind == "invalid_nickname":
        body["nickname"] = rng.choice(["a", "유노!", "열한글자닉네임입니다요", " 유노"])
        call(base_url, "POST", "/api/matches", body, stats)
        return

    status, match = call(base_url, "POST", "/api/matches", body, stats)
    if status != 200:
        return
    abandon_at = rng.randint(1, 3) if error_kind == "abandon" else None

    while match["status"] != "FINISHED":
        round_no = match["rounds_played"] + 1
        if abandon_at == round_no:
            return  # 중도 이탈: 진행 중인 매치로 남는다
        status, result = call(base_url, "POST", f"/api/matches/{match['id']}/throw", {"round_no": round_no}, stats)
        if status != 200:
            return
        if error_kind == "duplicate_throw" and round_no == 1:
            call(base_url, "POST", f"/api/matches/{match['id']}/throw", {"round_no": round_no}, stats)
        match = result

    if error_kind == "throw_after_finish":
        call(base_url, "POST", f"/api/matches/{match['id']}/throw", {"round_no": match["rounds_played"] + 1}, stats)


def wait_until_ready(base_url, timeout=120):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(base_url + "/health", timeout=5) as res:
                if res.status == 200:
                    return
        except Exception:
            pass
        time.sleep(2)
    raise SystemExit(f"앱이 {timeout}초 안에 준비되지 않았습니다: {base_url}")


def has_data(base_url):
    with urllib.request.urlopen(base_url + "/api/matches?limit=1", timeout=10) as res:
        return len(json.loads(res.read())) > 0


def main():
    p = argparse.ArgumentParser(description="Dice Duel 봇 매치 생성기")
    p.add_argument("--base-url", default="http://localhost:8080")
    p.add_argument("--matches", type=int, default=100, help="만들 매치 수")
    p.add_argument("--seed", type=int, default=42, help="같은 값이면 같은 매치 구성")
    p.add_argument("--concurrency", type=int, default=1, help="동시에 진행할 매치 수 (부하용)")
    p.add_argument("--rate", type=float, default=0, help="초당 시작할 매치 수, 0이면 제한 없음")
    p.add_argument("--inject-errors", type=float, default=0, help="이상값을 넣을 매치 비율 0~1")
    p.add_argument("--spread-days", type=float, default=0, help="매치 시작 시각을 최근 N일에 흩뿌림 (테스트 모드)")
    p.add_argument("--only-if-empty", action="store_true", help="DB에 매치가 있으면 아무것도 하지 않음")
    p.add_argument("--out", help="결과 요약을 저장할 JSON 경로")
    args = p.parse_args()

    wait_until_ready(args.base_url)
    if args.only_if_empty and has_data(args.base_url):
        print("이미 데이터가 있어 생성을 건너뜁니다.")
        return

    stats = Stats()
    started = time.perf_counter()
    started_at = datetime.now(KST)
    # --concurrency 1이면 매치를 순서대로 저장하므로 번호와 시작 시각의 순서가 같다
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        for i in range(args.matches):
            if args.rate > 0:
                time.sleep(max(0.0, started + i / args.rate - time.perf_counter()))
            pool.submit(play_match, args.base_url, i, args.matches, args.seed,
                        args.inject_errors, args.spread_days, started_at, stats)
    elapsed = time.perf_counter() - started

    lat = sorted(stats.latencies) or [0]
    summary = {
        "matches": args.matches,
        "concurrency": args.concurrency,
        "requests": len(stats.latencies),
        "elapsed_sec": round(elapsed, 2),
        "throughput_rps": round(len(stats.latencies) / elapsed, 1) if elapsed else 0,
        "latency_ms": {
            "avg": round(sum(lat) / len(lat) * 1000, 1),
            "p95": round(lat[int(len(lat) * 0.95) - 1] * 1000, 1) if len(lat) > 1 else round(lat[0] * 1000, 1),
            "max": round(lat[-1] * 1000, 1),
        },
        "status_counts": {str(k): v for k, v in sorted(stats.status_counts.items(), key=lambda x: str(x[0]))},
        "instance_counts": stats.instance_counts,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
