#!/bin/bash

echo "Starting Cardnews deployment..."

# 1. 기존 컨테이너 중지 및 제거
echo "Stopping existing container..."
docker stop cardnews-app 2>/dev/null || true
docker rm cardnews-app 2>/dev/null || true

# 2. 최신 이미지 pull
echo "Pulling latest image..."
docker pull achil7/cardnews:latest

# 3. docker-compose로 실행
echo "Starting container..."
docker compose up -d

# 4. 상태 확인
sleep 3
if docker ps | grep -q cardnews-app; then
  echo "Container is running!"
  docker logs cardnews-app --tail 10
else
  echo "Container failed to start!"
  docker logs cardnews-app
  exit 1
fi

echo "Deployment complete!"
echo "Logs: docker logs -f cardnews-app"
