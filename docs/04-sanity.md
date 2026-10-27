# 04. Sanity Test — Dice Duel v1.0

> Part 1 · TC-002 · 04 Sanity test
> 수행: 2026-10-27 13:42 · 수행자: 김성환 · 빌드: `main` (클린 설치 직후) · 결과: **PASS 11 / FAIL 0 → 기능 검증 진행**

## 목적과 기준

Sanity는 빌드·배포 직후 **"핵심 기능이 살아 있어 상세 테스트를 시작해도 되는가"**만 판단한다.
깊이 확인하지 않고 넓고 빠르게 본다 (약 10초). 하나라도 FAIL이면 상세 기능 테스트를 시작하지 않고 빌드를 되돌린다.

- 자동 점검: [`scripts/sanity.sh`](../scripts/sanity.sh) — CI(Jenkins·GitHub Actions)에서도 같은 스크립트를 쓴다
- 원본 실행 기록: [evidence/04-sanity-run.txt](evidence/04-sanity-run.txt)

## 체크리스트와 결과

| ID | 영역 | 확인 항목 | 기대 결과 | 실제 결과 | 판정 |
|---|---|---|---|---|---|
| SN-01 | 환경 | db·app 컨테이너 상태 | 둘 다 healthy | app=healthy, db=healthy | PASS |
| SN-02 | 환경 | `/health` | `status: ok` | `{"status":"ok", "test_mode":true}` | PASS |
| SN-03 | 게임 화면 | 규칙·닉네임·시작·던지기 요소 | 4개 모두 있음 | 4/4 | PASS |
| SN-04 | 매치 | 유효한 닉네임으로 매치 시작 | 매치 번호 발급 | #199 | PASS |
| SN-05 | 매치 | 던지기 1회 | 라운드 1 기록 | rounds_played=1 | PASS |
| SN-06 | 데이터 | 매치 조회 API 값 = DB 값 | 같음 | API 1:0:1 = DB 1:0:1 (라운드:플레이어승:컴퓨터승) | PASS |
| SN-07 | 통계 화면 | 화면 응답, 매치 목록 | 200, 1건 이상 | 200, 199건 | PASS |
| SN-08 | 통계 | 합계 분포 행 수 | 2개 11행, 3개 16행 | 11행, 16행 | PASS |
| SN-09 | 통계 | 닉네임별 전적 | 봇 10명 이상 | 11명 (봇 10 + SanityChk) | PASS |
| SN-10 | log | 처리 log 출력 | 방금 라운드의 `round processed` | 찍힘 | PASS |
| SN-11 | 게임 화면 (브라우저) | 화면에서 매치 시작 → 던지기 | 굴림 애니메이션 후 결과 표시 | 시작됨, 굴리는 중 `data-rolling=true` → 끝난 뒤 `false`, 라운드 1, "컴퓨터 승리", 주사위 눈 표시 | PASS |

SN-11은 스크립트가 HTML만 확인하는 한계를 보완하려고 실제 브라우저에서 한 번 조작했다.

## 판정

**PASS 11 / FAIL 0** → 빌드를 받아들이고 [기능 검증](05-test-results.md)을 시작한다.

## 참고: Sanity가 남기는 데이터

Sanity는 확인용 매치(`SanityChk`, `SanityUI`)를 만들고 1라운드만 진행한 채 둔다. 그래서 통계에 "진행 중" 매치가 2건 늘어난다.
이는 사용자가 도중에 떠난 매치와 같은 상태이며, 명세에 처리 규칙이 없는 상황이다 → [SPEC-001](05-defects/SPEC-001.md)의 사례로도 쓸 수 있다.
