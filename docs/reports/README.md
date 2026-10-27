# 테스트 실행 리포트 모음

> 테스트를 **실제로 실행한 결과**(원본 출력, 리포트 파일)를 실행 종류별로 모은 곳이다.
> 무엇을 테스트했고 어떻게 판정했는지는 각 단계 문서(`docs/01`~`06`, `perf/report.md`, `monitoring/README.md`)에 있고, 이 폴더는 그 근거가 되는 실행 기록이다.
> 파일 이름 규칙: `YYYY-MM-DD_<실행 내용>` · 새로 실행하면 같은 폴더에 날짜만 다른 파일을 추가한다.

## 실행 이력

| 날짜 | 종류 | 실행 환경 | 결과 | 리포트 | 관련 문서 |
|---|---|---|---|---|---|
| 2026-10-27 | 설치 (클린) | 로컬 Docker Desktop | 19초, 확인 6항목 PASS | [01-install/2026-10-27_clean-install.txt](01-install/2026-10-27_clean-install.txt) | [03-install.md](../03-install.md) |
| 2026-10-27 | Sanity | 로컬 | **11/11 PASS** (스크립트 10 + 브라우저 1) | [02-sanity/2026-10-27_local.txt](02-sanity/2026-10-27_local.txt) | [04-sanity.md](../04-sanity.md) |
| 2026-10-27 | Sanity | Jenkins (docker 없음) | 7 PASS · 3 SKIP · 0 FAIL | [02-sanity/2026-10-27_jenkins.txt](02-sanity/2026-10-27_jenkins.txt) | [jenkins/Jenkinsfile](../../jenkins/Jenkinsfile) |
| 2026-10-27 | 기능 검증 (API·DB) | 로컬, app 컨테이너 안에서 실행 | 45건 중 API·DB 수준 TC 수행 | [03-functional/2026-10-27_api-db-run.txt](03-functional/2026-10-27_api-db-run.txt) | [05-test-results.md](../05-test-results.md) |
| 2026-10-27 | 기능 검증 (log) | 로컬 | ERROR·WARNING log TC 3건 PASS | [03-functional/2026-10-27_log-checks.txt](03-functional/2026-10-27_log-checks.txt) | TC-A08, C06, E01 |
| 2026-10-27 | 기능 검증 (테스트 모드 OFF) | 임시 app 인스턴스 | 403 거부 PASS | [03-functional/2026-10-27_test-mode-off.txt](03-functional/2026-10-27_test-mode-off.txt) | TC-D02 |
| 2026-10-27 | 기능 검증 (분포 허용 오차) | 로컬, 표본 6,000개 이상 | 2개·3개 모두 ±2%p 이내 PASS | [결과](03-functional/2026-10-27_f11-distribution-result.txt) · [분포 데이터](03-functional/2026-10-27_f11-distribution.json) | TC-F11 |
| 2026-10-27 | 결함 영향 조사 | 로컬 DB | BUG-001 조건 14회 모두 오판정 | [03-functional/2026-10-27_bug-001-occurrence.txt](03-functional/2026-10-27_bug-001-occurrence.txt) | [BUG-001](../05-defects/BUG-001.md) |
| 2026-10-27 | **회귀 (Cucumber)** | **GitHub Actions** (headless Chrome) | 19 시나리오: PASS 15 · 알려진 결함 FAIL 4 · 새 실패 0 → **Success** | [HTML 리포트](04-regression/2026-10-27_github-actions/cucumber-report.html) · [판정 요약](04-regression/2026-10-27_github-actions/gate-summary.md) · [cucumber.json](04-regression/2026-10-27_github-actions/cucumber.json) | [06-regression.md](../06-regression.md) |
| 2026-10-27 | **회귀 (Cucumber)** | **Jenkins** #3 (원격 Chrome) | PASS 15 · 알려진 결함 FAIL 4 · 새 실패 0 → **UNSTABLE** | [04-regression/2026-10-27_jenkins-build3-console.txt](04-regression/2026-10-27_jenkins-build3-console.txt) | [06-regression.md](../06-regression.md) |
| 2026-10-27 | log 모니터링 | 로컬 (오류 주입 트래픽) | 주입 17건 = 검출 17건, ALERT 1회 | [05-log-monitoring/2026-10-27_monitor-run.txt](05-log-monitoring/2026-10-27_monitor-run.txt) | [monitoring/README.md](../../monitoring/README.md) |
| 2026-10-27 | **성능** | 로컬, app 인스턴스 1·2·3 | 188 → 364 → 534 요청/초, 오류 0, 동시 중복 300쌍 모두 1건만 처리 | [06-performance/2026-10-27_results.json](06-performance/2026-10-27_results.json) | [perf/report.md](../../perf/report.md) |

## Cucumber HTML 리포트 보는 법

| 무엇 | 어디서 |
|---|---|
| **가장 최근 실행** | GitHub Pages — https://juanito-kim.github.io/dice-duel-qa/ (main에 push할 때마다 새로 올라감) |
| **10/27 실행 보관본** | [04-regression/2026-10-27_github-actions/cucumber-report.html](04-regression/2026-10-27_github-actions/cucumber-report.html) — GitHub에서는 HTML 원문으로 보이므로 **내려받아 브라우저로 연다** (Step별 스크린샷 포함, 약 4.6MB) |

Pages는 마지막 실행 하나만 보여주므로, 기록으로 남길 실행은 이 폴더에 날짜별로 보관한다.

## 폴더 구성

```
docs/reports/
├─ 01-install/          설치 실행 기록
├─ 02-sanity/           Sanity 실행 기록 (로컬, Jenkins)
├─ 03-functional/       기능 검증 실행 기록 (API·DB, log, 분포, 결함 영향 조사)
├─ 04-regression/       회귀 자동화: Cucumber 리포트(HTML·JSON)와 판정 요약, Jenkins 콘솔
├─ 05-log-monitoring/   log 모니터 실행 기록
└─ 06-performance/      성능 측정 결과 (요약 JSON)
```
