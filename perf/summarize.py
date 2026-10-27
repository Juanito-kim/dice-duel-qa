"""perf/raw의 원본 결과를 요약(docs/reports/06-performance/2026-10-27_results.json)하고 Chart(docs/images/tc004-chart.png)를 그린다.

실행 (Pillow와 한글 글꼴이 필요해 컨테이너에서):
  docker run --rm -v "<저장소>:/repo" -v "C:\\Windows\\Fonts:/fonts:ro" -w /repo python:3.12-slim \
    sh -c "pip install -q pillow && python perf/summarize.py"
"""
import csv
import json
from statistics import mean

from PIL import Image, ImageDraw, ImageFont

RAW, N = "perf/raw/", [1, 2, 3]
results = []
for n in N:
    load = json.load(open(f"{RAW}load-{n}.json"))
    dup = json.loads(open(f"{RAW}dup-{n}.json").read().strip().splitlines()[-1])
    cpu, mem = {}, {}
    for row in csv.reader(open(f"{RAW}stats-{n}.csv")):
        _, name, c, m = row[0], row[1], float(row[2].rstrip("%")), row[3].split(" / ")[0]
        short = name.replace("dice-duel-qa-", "")
        cpu.setdefault(short, []).append(c)
        mem[short] = m
    app_cpu_peak = sum(max(v) for k, v in cpu.items() if k.startswith("app"))
    results.append({
        "instances": n, "requests": load["requests"], "elapsed_sec": load["elapsed_sec"],
        "throughput_rps": load["throughput_rps"], **{f"latency_{k}_ms": v for k, v in load["latency_ms"].items()},
        "errors": sum(v for k, v in load["status_counts"].items() if k != "200"),
        "per_instance": sorted(load["instance_counts"].values()),
        "app_cpu_peak_sum_pct": round(app_cpu_peak, 1),
        "db_cpu_peak_pct": round(max(cpu.get("db-1", [0])), 1),
        "app_mem": {k: v for k, v in mem.items() if k.startswith("app")},
        "dup_pairs": dup["pairs"], "dup_exactly_one_ok": dup["exactly_one_ok"],
        "dup_split_across_instances": dup["pairs_split_across_instances"], "dup_db_duplicates": dup["db_duplicate_rounds"],
    })
json.dump(results, open("docs/reports/06-performance/2026-10-27_results.json", "w"), ensure_ascii=False, indent=2)
for r in results:
    print(r)

# ---------- Chart: 두 지표는 단위가 달라 축을 공유하지 않고 나란히 그린다 ----------
SURFACE, INK, INK2, GRID, BAR = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df", "#2a78d6"
F = lambda size, bold=False: ImageFont.truetype("/fonts/malgunbd.ttf" if bold else "/fonts/malgun.ttf", size)
W, H = 1200, 560
img = Image.new("RGB", (W, H), SURFACE)
d = ImageDraw.Draw(img)
d.text((40, 24), "인스턴스 수별 성능 (봇 매치 1,000개 · 동시 20개, 약 5,500 요청)", font=F(26, True), fill=INK)
d.text((40, 62), "같은 부하에서 app 인스턴스를 1·2·3개로 늘렸을 때 · 오류 0건 · 부하 중 같은 라운드 동시 요청 100쌍 모두 1건만 처리", font=F(17), fill=INK2)


def panel(x0, title, unit, values, step):
    top, bottom, left, right = 140, 480, x0 + 60, x0 + 520
    d.text((x0 + 10, 104), title, font=F(20, True), fill=INK)
    vmax = step * (int(max(values) / step) + 1)
    for t in range(0, int(vmax) + 1, step):
        y = bottom - (bottom - top) * t / vmax
        d.line([(left, y), (right, y)], fill=GRID, width=1)
        d.text((left - 10, y), f"{t}", font=F(14), fill=INK2, anchor="rm")
    d.line([(left, bottom), (right, bottom)], fill=INK2, width=1)
    slot = (right - left) / len(values)
    for i, v in enumerate(values):
        cx = left + slot * (i + 0.5)
        bw = slot * 0.42
        y = bottom - (bottom - top) * v / vmax
        d.rounded_rectangle([cx - bw / 2, y, cx + bw / 2, bottom], radius=4, fill=BAR)
        d.rectangle([cx - bw / 2, bottom - 4, cx + bw / 2, bottom], fill=BAR)  # 아래쪽은 각지게 (기준선에 붙임)
        d.text((cx, y - 8), f"{v:g} {unit}", font=F(16, True), fill=INK, anchor="mb")
        d.text((cx, bottom + 12), f"인스턴스 {N[i]}개", font=F(15), fill=INK2, anchor="mt")


panel(20, "처리량 (요청/초) — 높을수록 좋음", "", [r["throughput_rps"] for r in results], 100)
panel(620, "p95 응답 시간 (ms) — 낮을수록 좋음", "", [r["latency_p95_ms"] for r in results], 25)
img.save("docs/images/tc004-chart.png", optimize=True)
print("chart saved")
