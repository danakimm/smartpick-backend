#!/bin/bash

# 이전 컨테이너 정리 (만약 존재한다면)
echo "이전 컨테이너 정리 중..."
docker stop smartpick-dev 2>/dev/null || true
docker rm smartpick-dev 2>/dev/null || true

# 도커 이미지 빌드
echo "도커 이미지 빌드 중..."
docker build -t smartpick-backend-dev -f script/Dockerfile.dev .

# 도커 컨테이너 실행 (로컬 디렉토리 마운트)
echo "도커 컨테이너 실행 중..."
docker run -d \
  --name smartpick-dev \
  --restart unless-stopped \
  --network host \
  -p 8000:8000 \
  -v "$(pwd)":/app \
  --env-file .env \
  smartpick-backend-dev

echo "개발 서버가 http://localhost:8000 에서 실행 중입니다."
echo "로그를 보려면: docker logs -f smartpick-dev" 