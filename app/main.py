from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .routers import chat

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

