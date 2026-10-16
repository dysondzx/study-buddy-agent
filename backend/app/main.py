from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.chat import router as chat_router
from app.api.conversations import router as conversations_router
from app.api.evaluation import router as eval_router
from app.data.init_db import init_sqlite_db
from app.config import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时做幂等初始化（建表）
    init_sqlite_db()
    logger.info("学伴智能体助手 后端启动完成")
    yield


app = FastAPI(title="学伴智能体助手", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(conversations_router)
app.include_router(eval_router)


@app.get("/health")
def health():
    return {"status": "ok"}
