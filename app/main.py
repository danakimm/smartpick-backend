from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import chat, product, report
from .config import settings

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
app.include_router(product.router, prefix="/api/products", tags=["products"])
app.include_router(report.router, prefix="/api/reports", tags=["reports"])