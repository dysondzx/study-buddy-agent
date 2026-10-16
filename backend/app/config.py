"""全局基础设施：配置、日志、LLM 工厂。"""
import logging
import os
import sys

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


class Settings:
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")

    SQLITE_PATH = os.getenv("SQLITE_PATH", "/data/agent_data.db")
    CHROMA_PATH = os.getenv("CHROMA_PATH", "/data/chroma_notes")
    KG_PATH = os.getenv("KG_PATH", "/data/knowledge_graph.pkl")

    NOTES_DIR = os.getenv("NOTES_DIR", "./notes")


settings = Settings()


def _setup_logging():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        '{"time": "%(asctime)s", "level": "%(levelname)s", '
        '"logger": "%(name)s", "message": "%(message)s"}'
    ))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    return root


logger = _setup_logging()


def get_llm(temperature: float = 0.0) -> ChatOpenAI:
    logger.info(f"初始化 LLM: {settings.DEEPSEEK_MODEL}")
    return ChatOpenAI(
        model=settings.DEEPSEEK_MODEL,
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
        temperature=temperature,
    )
