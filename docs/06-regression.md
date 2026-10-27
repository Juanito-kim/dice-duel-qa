# 06. 회귀 시나리오 — Dice Duel v1.0

> Part 1 · TC-002 · 06 회귀 시나리오 반영
> 작성: 2026-10-27 · 근거: [05-test-results.md](05-test-results.md)의 FAIL·BLOCKED와 핵심 기능

결함은 **고쳐졌는지**만이 아니라 **다시 생기지 않는지**를 계속 확인해야 한다.
기능 검증에서 나온 결함과 핵심 기능을 회귀 시나리오로 등록하고, 가능한 것은 Gherkin으로 자동화해 매 빌드마다 돌린다.

## 언제 무엇을 돌리나

| 시점 | 범위 | 실행 |
|---|---|---|
| 매 빌드 (CI) | Sanity → `@smoke` 태그 시나리오 | GitHub Actions · Jenkins |
| 결함 수정 빌드 | 해당 결함의 RG + 같은 기능의 RG | CI + 수정 확인 수동 |
| 릴리스 전 | 전체 RG + 기능 TC 45건 | CI + 수동 |

## 회귀 시나리오 목록

| RG | 출처 | 내용 | 원래 TC | 우선순위 | 자동화 | Feature 파일 · 태그 |
|---|---|---|---|---|---|---|
| RG-01 | [BUG-001](05-defects/BUG-001.md) | 라운드 판정 결정 테이블 **8칸 전체** (한 칸을 고치며 다른 칸이 깨지지 않게) | B01~B08 | 높음 | UI (Selenium) | [`02_round_judgement.feature`](../automation/src/test/resources/features/02_round_judgement.feature) `@R-01 @R-02 @BUG-001` |
| RG-02 | [BUG-002](05-defects/BUG-002.md) | 닉네임 경계값 1·2·9·10·11자 | A01~A05 | 높음 | UI (Selenium) | [`01_match_start.feature`](../automation/src/test/resources/features/01_match_start.feature) `@R-06 @BUG-002` |
| RG-03 | [BUG-003](05-defects/BUG-003.md) | 승률 = 승리 ÷ 끝난 매치, 순위 순서 (진행 중 매치가 있는 닉네임 포함) | F12, F13, F15 | 높음 | UI + API 비교 | [`04_stats.feature`](../automation/src/test/resources/features/04_stats.feature) `@S-04 @BUG-003` |
| RG-04 | [BUG-004](05-defects/BUG-004.md) | 매치 중 주사위 개수 선택 불가, 새 매치에서는 다시 선택 가능 | A10 | 보통 | UI (Selenium) | [`01_match_start.feature`](../automation/src/test/resources/features/01_match_start.feature) `@R-05 @BUG-004` |
| RG-05 | 핵심 기능 | 3승 즉시 종료, 던지기 비활성화, 종료 문구 | C01 | 높음 | UI (Selenium) | [`03_match_flow.feature`](../automation/src/test/resources/features/03_match_flow.feature) `@R-03 @R-08 @smoke` |
| RG-06 | 핵심 기능 | 처음 온 사용자의 한 판 (규칙 안내 → 시작 → 던지기 → 결과) | US-01, A11 | 높음 | UI (Selenium) | [`03_match_flow.feature`](../automation/src/test/resources/features/03_match_flow.feature) `@U-01 @smoke` |
| RG-07 | 핵심 기능 | 끝난 매치 던지기 거부, 잘못된 닉네임 → ERROR log 검출 | C05, C06, A08 | 보통 | log 모니터링 | `monitoring/` (TC-003 Server) |
| RG-08 | 핵심 기능 | 같은 라운드 동시 요청 1건만 처리 (부하 중) | E01, E02 | 보통 | 성능 스크립트 | `perf/` (TC-004) |
| RG-09 | 핵심 기능 | 빌드 직후 Sanity 11항목 | SN-01~11 | 높음 | 스크립트 | [`scripts/sanity.sh`](../scripts/sanity.sh) |
| RG-10 | [SPEC-001](05-defects/SPEC-001.md) · [SPEC-002](05-defects/SPEC-002.md) | PO 결정 후 규칙(R-10, S-01 보완)에 맞춰 TC 작성 | G01, F04 | 결정 후 | — | (PO 결정 대기) |

## 자동화 결과 (2026-10-27)

RG-01~RG-06을 Cucumber feature 4개, 시나리오 19개로 자동화했다. 결과는 아래 "기대 상태"와 정확히 일치했다.

| 실행 | 결과 | 판정 |
|---|---|---|
| 로컬 (Chrome headless) | PASS 15 · FAIL 4 (모두 `@BUG-xxx`) | 새 실패 0 → 통과 |
| GitHub Actions | Sanity 10/10 → PASS 15 · FAIL 4 (모두 `@BUG-xxx`) · [실행 기록](https://github.com/Juanito-kim/dice-duel-qa/actions/workflows/qa.yml) · [Cucumber 리포트](https://juanito-kim.github.io/dice-duel-qa/) | 새 실패 0 → **Success** |
| Jenkins (Docker, 원격 Chrome) | Sanity 7 PASS · 3 SKIP(docker 없음) → Smoke 2/2 → PASS 15 · FAIL 4 · [Jenkinsfile](../jenkins/Jenkinsfile) · [콘솔 기록](evidence/tc003-jenkins-build3.txt) | 새 실패 0 → **UNSTABLE** (JUnit이 알려진 결함 4건을 실패로 표시. "결함은 남아 있지만 새로 깨진 것은 없음") |

판정 규칙: 실패한 시나리오가 모두 알려진 결함(`@BUG-xxx`)이면 통과, 아니면 빌드 실패 ([known_failures.py](../scripts/known_failures.py)).
v1.0은 결함을 고치지 않고 릴리스 판단 자료로 쓰므로, CI의 역할은 **새로 깨진 것만 막는 것**이다. RG-07은 [log 모니터링](../monitoring/README.md), RG-08은 [성능 측정](../perf/report.md), RG-09는 [sanity.sh](../scripts/sanity.sh)로 수행했다.

## 결함 수정 전의 기대 상태

v1.0은 결함을 고치지 않고 릴리스 판단 자료로 쓰므로, 지금 돌리면 아래 시나리오는 **FAIL이 정상**이다. 자동화 리포트에서 FAIL이 이 결함들과 정확히 일치하는지 확인한다.

| 시나리오 | 지금 결과 | 이유 |
|---|---|---|
| RG-01 "둘 다 더블 → 무승부" | FAIL | BUG-001 |
| RG-02 "10자 닉네임 허용" | FAIL | BUG-002 |
| RG-03 "진행 중 매치가 있는 닉네임 승률" | FAIL | BUG-003 |
| RG-04 "매치 중 주사위 개수 선택 불가" | FAIL | BUG-004 |
| 나머지 | PASS | |

## 태그 규칙 (Gherkin)

- 규칙 ID: `@R-02`, `@S-04`, `@U-01` — 명세에서 해당 시나리오를 찾을 수 있게
- 결함 ID: `@BUG-001` — 결함 수정 빌드에서 `--tags @BUG-001`로 해당 회귀만 실행
- `@smoke`: 매 빌드 CI에서 Sanity 다음에 실행하는 최소 세트
