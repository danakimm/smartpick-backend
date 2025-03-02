#!/bin/bash

# 도커 컨테이너 중지 및 제거
echo "도커 컨테이너 중지 및 제거 중..."
docker stop smartpick-dev 2>/dev/null || true
docker rm smartpick-dev 2>/dev/null || true

echo "도커 컨테이너가 중지되었습니다." 