"""Log 모니터: app 인스턴스들의 log 파일을 주기적으로 모으고(수집), ERROR를 걸러내 유형별로 집계한다.

수집: LOG_DIR의 app-*.log를 지난번 읽은 위치부터 읽어 collected/YYYY-MM-DD.log 하나로 모은다.
필터: ERROR(와 WARNING)를 규칙 ID별 유형으로 분류한다. 정의되지 않은 ERROR는 "미분류"로 따로 알린다.
경보: 한 주기의 ERROR가 기준을 넘거나 미분류 ERROR가 나오면 ALERT를 출력한다.

사용 (app과 같은 이미지에서 실행):
  docker compose run --rm monitor                      # 30초마다 반복
  docker compose run --rm monitor --once               # 한 번만 수집·보고
  docker compose run --rm monitor --interval 10 --threshold 5
표준 라이브러리만 쓴다.
"""
import argparse
import glob
import json
import os
import re
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
LINE = re.compile(r"^(\S+ \S+) (INFO|WARNING|ERROR) \[(\S+)\] (.*)$")

# ERROR·WARNING 유형: (이름, 관련 규칙, 패턴)
RULES = [
    ("잘못된 닉네임", "R-06", re.compile(r"match rejected: invalid nickname")),
    ("잘못된 주사위 개수", "R-05", re.compile(r"match rejected: invalid dice_count")),
    ("끝난 매치에 던지기", "R-08", re.compile(r"throw rejected: match already finished")),
    ("없는 매치에 던지기", "R-08", re.compile(r"throw rejected: match not found")),
    ("중복 라운드 요청", "R-09", re.compile(r"throw rejected: duplicate round")),
    ("테스트 모드 아님", "R-07", re.compile(r"next-roll rejected: test mode off")),
]


def classify(message):
    for name, rule, pattern in RULES:
        if pattern.search(message):
            return f"{name} ({rule})"
    return "미분류"


def collect(log_dir, out_dir, state_path):
    """지난번 위치 이후의 새 줄을 읽어 collected 파일에 붙이고, 새 줄 목록을 돌려준다."""
    state = json.load(open(state_path)) if os.path.exists(state_path) else {}
    new_lines = []
    for path in sorted(glob.glob(os.path.join(log_dir, "app-*.log"))):
        offset = state.get(path, 0)
        if os.path.getsize(path) < offset:  # 파일이 새로 만들어졌으면 처음부터
            offset = 0
        with open(path, encoding="utf-8") as f:
            f.seek(offset)
            new_lines += [l.rstrip("\n") for l in f if l.strip()]
            state[path] = f.tell()
    os.makedirs(out_dir, exist_ok=True)
    if new_lines:
        day = datetime.now(KST).strftime("%Y-%m-%d")
        with open(os.path.join(out_dir, f"{day}.log"), "a", encoding="utf-8") as f:
            f.write("\n".join(sorted(new_lines)) + "\n")
    json.dump(state, open(state_path, "w"))
    return sorted(new_lines)


def report(lines, threshold, out_dir):
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
    levels, by_type, samples, instances = Counter(), Counter(), defaultdict(list), Counter()
    for line in lines:
        m = LINE.match(line)
        if not m:
            continue
        _, level, instance, message = m.groups()
        levels[level] += 1
        instances[instance] += 1
        if level in ("ERROR", "WARNING"):
            kind = f"{level} · {classify(message)}"
            by_type[kind] += 1
            if len(samples[kind]) < 2:
                samples[kind].append(line)

    out = [f"[{now}] 수집 {len(lines)}줄 · 인스턴스 {len(instances)}개 · "
           f"INFO {levels['INFO']} · WARNING {levels['WARNING']} · ERROR {levels['ERROR']}"]
    for kind, count in sorted(by_type.items(), key=lambda x: (-x[1], x[0])):
        out.append(f"  {count:>4}  {kind}")
        out += [f"        예) {s}" for s in samples[kind]]
    unknown = sum(c for k, c in by_type.items() if k.startswith("ERROR") and "미분류" in k)
    if levels["ERROR"] > threshold:
        out.append(f"ALERT  ERROR {levels['ERROR']}건이 기준 {threshold}건을 넘음")
    if unknown:
        out.append(f"ALERT  미분류 ERROR {unknown}건 (새로운 종류의 오류)")
    if levels["ERROR"] <= threshold and not unknown:
        out.append("OK     경보 없음")
    text = "\n".join(out)
    print(text, flush=True)
    with open(os.path.join(out_dir, "latest-report.txt"), "w", encoding="utf-8") as f:
        f.write(text + "\n")


def main():
    p = argparse.ArgumentParser(description="Dice Duel log 모니터")
    p.add_argument("--log-dir", default=os.getenv("LOG_DIR", "/var/log/dice"))
    p.add_argument("--out-dir", default="/monitoring/collected")
    p.add_argument("--interval", type=int, default=30, help="수집 주기(초)")
    p.add_argument("--threshold", type=int, default=10, help="한 주기 ERROR 경보 기준")
    p.add_argument("--once", action="store_true", help="한 번만 수집·보고")
    args = p.parse_args()
    state = os.path.join(args.out_dir, ".offsets.json")
    os.makedirs(args.out_dir, exist_ok=True)
    while True:
        report(collect(args.log_dir, args.out_dir, state), args.threshold, args.out_dir)
        if args.once:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
