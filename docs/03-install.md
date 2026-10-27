# 03. 환경 구성·설치 — Dice Duel v1.0

> Part 1 · TC-002 · 03 환경 구성·설치
> 수행: 2026-10-27 · 수행자: 김성환 · 결과: **설치 성공** (빌드·기동 19초)
> 원본 실행 기록: [evidence/03-install-run.txt](evidence/03-install-run.txt)

## 1. 테스트 환경

| 항목 | 값 |
|---|---|
| OS | Windows 11 Home |
| Docker | Docker Desktop (Engine 29.9.2, Compose v5.6.1), WSL 2 |
| 브라우저 | Chrome (수동 확인), 화면 폭 1024px 이상 |
| 자동화 도구 | JDK 25 (Temurin, 컴파일 대상 Java 17), Maven 3.10.0, VS Code |
| 대상 | Dice Duel v1.0 (`main` 브랜치) |

## 2. 구성

```
브라우저 ─▶ lb (nginx, :8080) ─▶ app (FastAPI: API + Processor, 1~N개) ─▶ db (PostgreSQL 16, :5432)
                                      ▲
                       generator ─────┘ (처음 한 번 봇 매치 200개 생성 후 종료)
```

| 컨테이너 | 이미지 | 역할 | 포트 |
|---|---|---|---|
| db | postgres:16 | 매치·라운드 저장. 처음 만들 때 `app/db/init.sql`로 테이블 생성 | 5432 (DB 직접 조회용) |
| app | 직접 빌드 (python:3.12-slim) | API + 판정 로직 + 화면 2장 | 8000 (내부) |
| lb | nginx:1.27-alpine | app 인스턴스 앞의 로드밸런서 | **8080** |
| generator | app과 같은 이미지 | 초기 데이터 생성 (DB가 비어 있을 때만) | — |

## 3. 설치 절차

사전 조건: Docker Desktop 실행 중, Git 설치.

```bash
git clone https://github.com/Juanito-kim/dice-duel-qa.git
```
```bash
cd dice-duel-qa
```
```bash
docker compose up -d --build
```

처음부터 다시 설치하려면 데이터까지 지운 뒤 올린다.

```bash
docker compose down -v
```

## 4. 설치 후 상태 확인

| # | 확인 항목 | 방법 | 기대 결과 | 실제 결과 | 판정 |
|---|---|---|---|---|---|
| 1 | 컨테이너 상태 | `docker compose ps -a` | db·app healthy, lb Up, generator Exited (0) | 기대와 같음 | PASS |
| 2 | 앱 상태 | `GET /health` | `status: ok`, `test_mode: true` | `{"status":"ok","instance":"a2c6aea7a6a4","test_mode":true}` | PASS |
| 3 | 초기 데이터 생성 | generator log | 매치 200개 시도, 오류 없이 종료 | 요청 1,074건 (200: 1,065 / 400: 2 / 409: 7). 400·409는 일부러 넣은 이상값 | PASS |
| 4 | 초기 데이터 내용 | DB 조회 | 봇 10명, 최근 7일에 분포, 진행 중 매치 포함 | 198건, 10명, 10/20~10/27, 진행 중 3건 | PASS |
| 5 | 화면·API 문서 | `/`, `/stats`, `/docs` | 모두 200 | 모두 200 | PASS |
| 6 | 재시작 후 데이터 유지 | `docker compose restart` | 데이터 그대로, generator는 생성 건너뜀 | "이미 데이터가 있어 생성을 건너뜁니다", 198건 유지 | PASS |

`docker compose ps -a` 실제 출력:

```
SERVICE     IMAGE                    STATUS                      PORTS
app         dice-duel-qa-app         Up 32 seconds (healthy)     8000/tcp
db          postgres:16              Up 36 seconds (healthy)     0.0.0.0:5432->5432/tcp
generator   dice-duel-qa-generator   Exited (0) 23 seconds ago
lb          nginx:1.27-alpine        Up 28 seconds               0.0.0.0:8080->80/tcp
```

초기 데이터는 seed가 고정(`--seed 42`)이라 몇 번을 다시 설치해도 **같은 매치 구성**이 만들어진다 (요청 결과 1,074건 / 200: 1,065 / 400: 2 / 409: 7이 10/26과 동일). 매치 시작 시각만 설치한 날을 기준으로 최근 7일에 놓인다.

## 5. 접속 주소

| 화면 | 주소 |
|---|---|
| 게임 | http://localhost:8080 |
| 통계 | http://localhost:8080/stats |
| API 문서 (자동 생성) | http://localhost:8080/docs |
| DB 직접 조회 | `docker compose exec db psql -U dice -d dice` |

## 6. 자주 겪는 문제

| 증상 | 원인 | 해결 |
|---|---|---|
| `failed to connect to the docker API` | Docker Desktop이 실행되지 않음 | Docker Desktop 실행 후 엔진이 running이 될 때까지 대기 |
| Docker Desktop 설치 중 "Virtual Machine Platform" 오류 | Windows 가상화 기능이 꺼져 있음 | 설치 프로그램을 "All-users installation"으로 다시 실행 (관리자 권한) |
| 화면을 고쳤는데 예전 화면이 보임 | 브라우저 캐시 | v1.0은 화면 HTML에 `Cache-Control: no-store`를 넣어 해결 |
| 인스턴스를 늘렸는데 요청이 한 곳으로만 감 | nginx가 시작할 때의 인스턴스 목록만 앎 | `docker compose up -d --scale app=3` 후 `docker compose restart lb` |
