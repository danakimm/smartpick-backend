#!/bin/bash

# 기본 서버 URL
SERVER_URL="http://localhost:8000"

# 명령줄 인수 처리
while [[ $# -gt 0 ]]; do
  case $1 in
    --url)
      SERVER_URL="$2"
      shift 2
      ;;
    --test)
      TEST_TYPE="$2"
      shift 2
      ;;
    *)
      echo "알 수 없는 옵션: $1"
      exit 1
      ;;
  esac
done

# 테스트 실행
echo "API 테스트 실행 중..."

if [ -n "$TEST_TYPE" ]; then
  python test/test_api.py --url "$SERVER_URL" --test "$TEST_TYPE"
else
  python test/test_api.py --url "$SERVER_URL"
fi 