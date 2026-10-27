# Log 모니터링 — TC-003 · Server (05 수집, 06 ERROR 필터링)

> 수행: 2026-10-27 · 스크립트: [log_monitor.py](log_monitor.py) · 원본 실행 기록: [../docs/reports/05-log-monitoring/2026-10-27_monitor-run.txt](../docs/reports/05-log-monitoring/2026-10-27_monitor-run.txt)

## 구조

```
app 인스턴스 1..N ──(log 파일)──▶ logs/app-<인스턴스>.log
                                        │  주기 수집 (지난번 읽은 위치부터)
                                        ▼
                        monitor ──▶ monitoring/collected/YYYY-MM-DD.log   (하나로 모은 log)
                           │
                           └──▶ ERROR·WARNING 유형별 집계 → 경보(ALERT) → latest-report.txt
```

- **수집 (05)**: 인스턴스가 여러 개여도 각자의 log 파일을 읽어 하루 단위 파일 하나로 모은다. 읽은 위치를 기억해 **새로 생긴 줄만** 가져온다.
- **필터링 (06)**: ERROR·WARNING을 명세 규칙 ID별 유형으로 나눈다. 패턴에 없는 ERROR는 **미분류**로 따로 표시한다 (새로운 종류의 장애).
- **경보**: 한 주기의 ERROR가 기준(기본 10건)을 넘거나 미분류 ERROR가 나오면 `ALERT`.

| 유형 | 규칙 | log 패턴 |
|---|---|---|
| 잘못된 닉네임 | R-06 | `match rejected: invalid nickname` |
| 잘못된 주사위 개수 | R-05 | `match rejected: invalid dice_count` |
| 끝난 매치에 던지기 | R-08 | `throw rejected: match already finished` |
| 없는 매치에 던지기 | R-08 | `throw rejected: match not found` |
| 중복 라운드 요청 (WARNING) | R-09 | `throw rejected: duplicate round` |
| 테스트 모드 아님 (WARNING) | R-07 | `next-roll rejected: test mode off` |

## 실행

```bash
docker compose run --rm monitor --once
```
```bash
docker compose run --rm monitor --interval 30 --threshold 10
```

## 검증: 일부러 넣은 오류를 빠짐없이 걸러내는가

Generator로 오류를 섞은 트래픽을 보낸 뒤(`--inject-errors 0.4`, 매치 60개) 모니터를 한 번 돌렸다.
Generator가 받은 응답 코드와 모니터가 검출한 건수를 비교했다.

| Generator가 받은 응답 | 건수 | 모니터 검출 | 건수 | 일치 |
|---|---|---|---|---|
| 400 (잘못된 닉네임) | 8 | ERROR · 잘못된 닉네임 (R-06) | 8 | ✅ |
| 409 (끝난 매치 · 중복 라운드) | 9 | ERROR · 끝난 매치에 던지기 (R-08) 4 + WARNING · 중복 라운드 (R-09) 5 | 9 | ✅ |

실제 출력:

```
[2026-10-27 14:20:03] 수집 316줄 · 인스턴스 1개 · INFO 299 · WARNING 5 · ERROR 12
     8  ERROR · 잘못된 닉네임 (R-06)
        예) 2026-10-27 14:20:00 ERROR [376de14a284f] match rejected: invalid nickname=' 유노'
        예) 2026-10-27 14:20:00 ERROR [376de14a284f] match rejected: invalid nickname='유노!'
     5  WARNING · 중복 라운드 요청 (R-09)
        예) 2026-10-27 14:20:01 WARNING [376de14a284f] throw rejected: duplicate round id=237 round_no=1 expected=2
     4  ERROR · 끝난 매치에 던지기 (R-08)
        예) 2026-10-27 14:20:00 ERROR [376de14a284f] throw rejected: match already finished id=221 round_no=5
ALERT  ERROR 12건이 기준 10건을 넘음
```

주기 실행(`--interval 5`)에서는 다음 주기부터 "수집 0줄"이 나와, 이미 읽은 줄을 다시 세지 않는 것을 확인했다.

## 회귀 시나리오 연결
- [RG-07](../docs/06-regression.md): 끝난 매치 던지기 거부, 잘못된 닉네임 → ERROR log 검출 (TC-A08, C05, C06)
