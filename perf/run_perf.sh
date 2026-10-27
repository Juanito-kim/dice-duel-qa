#!/usr/bin/env bash
# TC-004 성능 측정: app 인스턴스 1·2·3개에서 같은 부하(봇 매치 동시 실행)를 주고 결과를 모은다.
#   부하: Generator 매치 1,000개, 동시 20개 (약 5,500 요청). 동시 중복 던지기 확인이 부하 중에 끝나도록 충분히 길게
#   측정: 처리량·응답 시간(Generator 요약), CPU·메모리(docker stats 2초 간격), 동시 중복 던지기(부하 중)
# 사용: bash perf/run_perf.sh      결과: perf/raw/ (원본), perf/results.json (요약)
set -u
cd "$(dirname "$0")/.."
mkdir -p perf/raw
MATCHES=${MATCHES:-1000}
CONCURRENCY=${CONCURRENCY:-20}

for N in 1 2 3; do
  echo "=== 인스턴스 ${N}개 ==="
  docker compose up -d --scale app=$N app >/dev/null 2>&1
  for i in $(seq 1 60); do
    [ "$(docker compose ps app --format '{{.Health}}' | grep -c healthy)" -ge "$N" ] && break; sleep 2
  done
  docker compose restart lb >/dev/null 2>&1; sleep 3
  # 주의: generator는 --no-deps로 실행 (의존 서비스를 다시 맞추면서 app이 1개로 돌아가는 것을 막음)

  # docker stats 기록 (부하가 끝날 때까지)
  : > perf/raw/stats-$N.csv
  ( while [ ! -f perf/raw/.done-$N ]; do
      docker stats --no-stream --format '{{.Name}},{{.CPUPerc}},{{.MemUsage}}' | grep -E 'app|db|lb' \
        | sed "s/^/$(date +%H:%M:%S),/" >> perf/raw/stats-$N.csv
    done ) &
  SAMPLER=$!

  # 부하 + 그 사이 동시 중복 던지기 확인
  MSYS_NO_PATHCONV=1 docker compose run --rm --no-deps -v "$(pwd)/perf/raw:/results" generator \
    python generator.py --base-url http://lb --matches "$MATCHES" --concurrency "$CONCURRENCY" --seed $((1000 + N)) \
    --out /results/load-$N.json > perf/raw/load-$N.log 2>&1 &
  LOAD=$!
  sleep 3
  docker compose exec -T app python - < perf/dup_under_load.py > perf/raw/dup-$N.json 2>&1
  wait $LOAD
  touch perf/raw/.done-$N; wait $SAMPLER; rm -f perf/raw/.done-$N
  cat perf/raw/load-$N.json | tr -d '\n' | head -c 400; echo
  cat perf/raw/dup-$N.json
done

docker compose up -d --scale app=1 app >/dev/null 2>&1; docker compose restart lb >/dev/null 2>&1
echo "완료: perf/raw/"
