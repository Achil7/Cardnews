#!/bin/bash
set -e

# .env 환경변수를 cron 프로세스에서도 사용할 수 있도록 export
printenv | grep -v "no_proxy" >> /etc/environment

# DB 초기화 (첫 실행 시 테이블 생성)
cd /app && python -c "from src.db.repository import init_db; init_db()"

echo "=== Cardnews container started ==="
echo "Cron schedule: UTC 23:00 (KST 08:00), UTC 04:00 (KST 13:00)"

# cron 데몬 시작 (foreground)
cron -f
