# Cardnews — Python + Playwright(Chromium) Docker Image
# Playwright 공식 이미지 기반 (Ubuntu jammy + Chromium 사전 설치)

FROM mcr.microsoft.com/playwright/python:v1.52.0-jammy

WORKDIR /app

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright Chromium 브라우저 설치
RUN playwright install chromium

# 소스 코드 복사
COPY config.py .
COPY accounts.yaml .
COPY main.py .
COPY gui_main.py .
COPY src/ ./src/

# GUI 포트
EXPOSE 8501

# 데이터/로그 디렉토리 생성
RUN mkdir -p data logs

# cron 설치 및 설정
RUN apt-get update && apt-get install -y cron && rm -rf /var/lib/apt/lists/*

# crontab 파일 복사
COPY deploy/crontab /etc/cron.d/cardnews-cron
RUN chmod 0644 /etc/cron.d/cardnews-cron && crontab /etc/cron.d/cardnews-cron

# 시작 스크립트
COPY deploy/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
