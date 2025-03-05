import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 프로젝트 정보
PROJECT_NAME = "SmartPick Backend"
VERSION = "0.1.0"

# API 키
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY", "")

# 데이터베이스 경로
REVIEW_DB_PATH = os.getenv("REVIEW_DB_PATH", "app/agents/tablet_reviews_db")
SPEC_DB_PATH = os.getenv("SPEC_DB_PATH", "app/agents/spec_documents/product_details.csv")

# 서버 설정
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000")) 