"""Cucumber 결과 판정: 실패한 시나리오가 모두 '알려진 결함(@BUG-xxx 태그)'이면 통과, 아니면 빌드 실패.

v1.0은 결함을 고치지 않고 릴리스 판단 자료로 쓰므로, 회귀 시나리오 중 일부는 FAIL이 정상이다 (docs/06-regression.md).
CI가 할 일은 "새로 깨진 것"만 막는 것이다.
사용: python3 scripts/known_failures.py automation/target/cucumber-report/cucumber.json
출력: Markdown 요약 (GitHub Actions Job Summary에 그대로 붙인다). 종료 코드 0 = 통과, 1 = 새 실패 있음
"""
import json
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "automation/target/cucumber-report/cucumber.json"
try:
    features = json.load(open(path, encoding="utf-8"))
except (OSError, ValueError) as e:
    print(f"### ❌ Cucumber 결과 파일을 읽을 수 없음: {path} ({e})")
    sys.exit(1)

rows, passed, known, new = [], 0, 0, 0
for feature in features:
    for sc in feature.get("elements", []):
        if sc.get("type") != "scenario":
            continue
        tags = [t["name"] for t in sc.get("tags", [])]
        failed = any(s.get("result", {}).get("status") in ("failed", "undefined", "pending") for s in sc.get("steps", []))
        bugs = [t for t in tags if t.startswith("@BUG-")]
        if not failed:
            passed += 1
            continue
        if bugs:
            known += 1
            status = "알려진 결함"
        else:
            new += 1
            status = "**새 실패**"
        rows.append(f"| {status} | {' '.join(bugs) or '-'} | {sc['name']} |")

total = passed + known + new
print(f"### Cucumber 회귀 결과: 전체 {total} · PASS {passed} · 알려진 결함 FAIL {known} · 새 실패 {new}")
print()
if rows:
    print("| 판정 | 결함 | 시나리오 |")
    print("|---|---|---|")
    print("\n".join(rows))
    print()
if total == 0:
    print("❌ 실행된 시나리오가 없음")
    sys.exit(1)
print("✅ 알려진 결함 외 실패 없음" if new == 0 else "❌ 알려진 결함이 아닌 실패가 있음 → 빌드 실패")
sys.exit(1 if new else 0)
