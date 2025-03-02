#!/bin/bash

# 서버 디렉토리로 이동
cd /home/ubuntu/smartpick-backend

# 최신 코드 가져오기
echo "최신 코드 가져오는 중..."
git pull

# 도커 이미지 빌드 및 실행
echo "도커 컨테이너 실행 중..."
./script/run_dev.sh

echo "배포가 완료되었습니다." 