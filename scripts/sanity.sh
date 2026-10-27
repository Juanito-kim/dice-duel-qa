#!/usr/bin/env bash
# Sanity test: 빌드·배포 직후 "핵심 기능이 살아 있는가"만 빠르게 확인한다 (약 10초).
# 하나라도 FAIL이면 상세 기능 테스트로 넘어가지 않는다.
# 사용: bash scripts/sanity.sh [BASE_URL]      (기본 http://localhost:8080)
# 필요: curl. docker compose가 있으면 컨테이너·DB·log 확인(SN-01·06·10)도 하고, 없으면 SKIP (예: Jenkins 컨테이너 안).
# 결과 요약은 마지막 줄에 나온다.

BASE="${1:-http://localhost:8080}"
PASS=0; FAIL=0; SKIP=0
HAS_DOCKER=0; docker compose ps >/dev/null 2>&1 && HAS_DOCKER=1
H='Content-Type: application/json'

check() {  # check "ID" "설명" 조건(0이면 PASS) "실제 값"
  if [ "$3" -eq 0 ]; then PASS=$((PASS+1)); printf 'PASS  %-6s %s  [%s]\n' "$1" "$2" "$4"
  else FAIL=$((FAIL+1)); printf 'FAIL  %-6s %s  [%s]\n' "$1" "$2" "$4"; fi
}
skip() { SKIP=$((SKIP+1)); printf 'SKIP  %-6s %s  [docker 없음]\n' "$1" "$2"; }
json() { sed -n "s/.*\"$1\":\([^,}]*\).*/\1/p" | head -1 | tr -d '"'; }   # 간단한 JSON 값 추출

echo "Sanity $(date '+%Y-%m-%d %H:%M:%S') target=$BASE"

# SN-01 컨테이너 상태
if [ "$HAS_DOCKER" = 1 ]; then
st=$(docker compose ps --format '{{.Service}}={{.Health}}' 2>/dev/null | tr '\n' ' ')
echo "$st" | grep -q 'app=healthy' && echo "$st" | grep -q 'db=healthy'; check SN-01 "db·app 컨테이너 healthy" $? "$st"
else skip SN-01 "db·app 컨테이너 healthy"; fi

# SN-02 앱 상태
h=$(curl -s "$BASE/health"); echo "$h" | grep -q '"status":"ok"'; check SN-02 "/health 응답 ok" $? "$h"

# SN-03 게임 화면과 핵심 요소
g=$(curl -s "$BASE/"); n=$(echo "$g" | grep -o -E 'data-testid="(nickname-input|start-button|throw-button|rules)"' | sort -u | wc -l)
[ "$n" -eq 4 ]; check SN-03 "게임 화면: 규칙·닉네임·시작·던지기 요소" $? "$n/4"

# SN-04 매치 시작
m=$(curl -s -H "$H" -d '{"nickname":"SanityChk","dice_count":2}' "$BASE/api/matches"); id=$(echo "$m" | json id)
[ -n "$id" ]; check SN-04 "매치 시작 (유효한 닉네임)" $? "match id=$id"

# SN-05 던지기 1회
t=$(curl -s -H "$H" -d '{"round_no":1}' "$BASE/api/matches/$id/throw"); r=$(echo "$t" | json rounds_played)
[ "$r" = "1" ]; check SN-05 "던지기 1회 → 라운드 1 기록" $? "rounds_played=$r"

# SN-06 API 값 = DB 값
if [ "$HAS_DOCKER" = 1 ]; then
db=$(docker compose exec -T db psql -U dice -d dice -tAc "select rounds_played||':'||player_wins||':'||cpu_wins from matches where id=$id" 2>/dev/null | tr -d '\r')
api=$(curl -s "$BASE/api/matches/$id"); api_v="$(echo "$api" | json rounds_played):$(echo "$api" | json player_wins):$(echo "$api" | json cpu_wins)"
[ "$db" = "$api_v" ]; check SN-06 "매치 조회 API = DB" $? "api=$api_v db=$db"
else skip SN-06 "매치 조회 API = DB"; fi

# SN-07 통계 화면과 매치 목록
s=$(curl -s -o /dev/null -w '%{http_code}' "$BASE/stats"); total=$(curl -s -D - -o /dev/null "$BASE/api/matches?limit=20" | tr -d '\r' | sed -n 's/^[Xx]-[Tt]otal-[Cc]ount: //p')
[ "$s" = "200" ] && [ "${total:-0}" -gt 0 ]; check SN-07 "통계 화면 200, 매치 목록 있음" $? "stats=$s total=$total"

# SN-08 합계 분포
d2=$(curl -s "$BASE/api/stats/sum-distribution?dice_count=2" | grep -o '"sum":' | wc -l)
d3=$(curl -s "$BASE/api/stats/sum-distribution?dice_count=3" | grep -o '"sum":' | wc -l)
[ "$d2" -eq 11 ] && [ "$d3" -eq 16 ]; check SN-08 "합계 분포 2개 11행·3개 16행" $? "2개=$d2 3개=$d3"

# SN-09 승률 순위
p=$(curl -s "$BASE/api/stats/players" | grep -o '"nickname":' | wc -l)
[ "$p" -ge 10 ]; check SN-09 "닉네임별 전적 응답 (봇 10명 이상)" $? "players=$p"

# SN-10 처리 log 출력
if [ "$HAS_DOCKER" = 1 ]; then
docker compose logs --since 2m app 2>/dev/null | grep -q "round processed id=$id"; check SN-10 "처리 log에 방금 라운드가 찍힘" $? "round processed id=$id"
else skip SN-10 "처리 log에 방금 라운드가 찍힘"; fi

echo "RESULT pass=$PASS fail=$FAIL skip=$SKIP"
[ "$FAIL" -eq 0 ]
