# SmartPick Backend

태블릿 제품 추천 AI 챗봇 서비스의 백엔드 서버입니다.

## 💡 프로젝트 소개

SmartPick은 사용자의 요구사항을 분석하여 최적의 태블릿을 추천해주는 AI 기반 챗봇 서비스입니다. 다중 에이전트 시스템을 활용하여 제품 스펙, 사용자 리뷰, 전문가 의견을 종합적으로 분석하고, 개인화된 추천을 제공합니다.

## 🌟 주요 특징

### 1. 멀티 에이전트 아키텍처
- **Question Agent**: 자연어 처리를 통한 사용자 요구사항 정확한 파악 및 의도 분석
- **Spec Agent**: 제품 스펙 데이터 기반 객관적 분석 및 필터링
- **Review Agent**: 실제 사용자 리뷰 감성 분석 및 핵심 포인트 추출
- **YouTube Agent**: 제품 리뷰 영상 분석 및 전문가 의견 추출
- **Middleware Agent**: 다중 에이전트의 분석 결과를 통합하여 최적의 추천 도출
- **Report Agent**: 최종 추천 결과를 사용자 친화적인 형태로 가공
- **Feedback Agent**: 사용자 피드백을 처리하고 추천 결과 개선

### 2. 실시간 대화형 인터페이스
- WebSocket 기반 양방향 실시간 통신
- 사용자의 추가 질문과 피드백을 반영한 동적 추천
- 자연스러운 대화 흐름 유지

### 3. 고도화된 데이터 분석
- 리뷰 데이터 감성 분석 및 핵심 의견 추출
- 제품 스펙 데이터 정규화 및 비교 분석

## 🛠 기술 스택

### 핵심 기술
- **Python 3.10**: 안정적이고 현대적인 백엔드 개발
- **FastAPI & WebSocket**: 고성능 비동기 웹 서버 구현
- **LangChain**: AI 기반 대화형 에이전트 구현
- **OpenAI GPT-4**: 자연어 처리 및 대화 생성
- **FAISS & ChromaDB**: 고성능 벡터 데이터베이스 활용

### AI/ML
- langchain-openai, langchain-anthropic, langchain-upstage
- langchain-core, langchain-community
- langchain-text-splitters

### 데이터 처리
- ChromaDB: 벡터 데이터베이스
- SQLAlchemy: 관계형 데이터베이스 ORM
- NumPy & Pandas: 데이터 분석 및 처리
- KoNLPy: 한국어 자연어 처리


## 🔗 API 엔드포인트

### WebSocket: `/api/chat/ws/{client_id}`
실시간 대화형 제품 추천 서비스
- 자연어 기반 사용자 요구사항 분석
- 실시간 제품 추천 및 상세 정보 제공
- 사용자 피드백 기반 추천 결과 개선
