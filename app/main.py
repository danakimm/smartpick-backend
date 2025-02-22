from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from .routers import chat, product, report
from .agents.question_agent import QuestionAgent
from .agents.review_agent import ProductRecommender
from .agents.graph import define_workflow

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])

# 질문 에이전트 엔드포인트 추가
@app.post("/api/question")
async def handle_question(request: Request):
    state = await request.json()
    agent = QuestionAgent()
    response = await agent.run(state)
    return response

# 리뷰 분석 에이전트 엔드포인트 추가
@app.post("/api/review")
async def handle_review(request: Request):
    state = await request.json()
    recommender = ProductRecommender()
    response = recommender.generate_recommendations(state)
    return response

@app.post("/api/workflow")
async def handle_workflow(request: Request):
    state = await request.json()
    workflow = define_workflow()
    response = await workflow.run(state)
    return response

