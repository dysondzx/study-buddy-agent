"""RAGAS 评估：数据集、裁判模型工厂。"""
import os

from openai import AsyncOpenAI
from pydantic import BaseModel
from ragas.embeddings import embedding_factory
from ragas.llms import llm_factory


class EvalSample(BaseModel):
    user_input: str
    reference: str = ""
    response: str = ""


DEFAULT_DATASET: list[EvalSample] = [
    EvalSample(
        user_input="帮我制定一个 2 周学完 FastAPI 的计划",
        reference="应按周拆解：第一周 Python 异步基础 + FastAPI 入门路由/依赖注入，"
                 "第二周 中间件/数据库集成/部署；需先掌握 Python 基础。",
    ),
    EvalSample(
        user_input="我在 RAG 评估那里记了什么？",
        reference="RAGAS 指标：Faithfulness 衡量答案是否被上下文支持，"
                 "AnswerRelevancy 衡量是否解决问题，ContextRecall 衡量召回率。",
    ),
    EvalSample(
        user_input="这个月我学了多少小时？",
        reference="按 study_log 表统计本月 duration_minutes 总和，换算成小时。",
    ),
    EvalSample(
        user_input="学 RAG 之前需要先懂什么？",
        reference="线性代数 → Embedding → 向量检索 → RAG；混合检索 → Rerank → RAG。",
    ),
    EvalSample(
        user_input="我下周怎么安排复习？",
        reference="应结合知识薄弱点（知识检索）+ 学习节奏（数据统计）综合排期。",
    ),
]


def _get_api_key() -> str:
    key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not key:
        print("  [WARN] DEEPSEEK_API_KEY 未设置，裁判 LLM 将无法调用")
    return key


def _get_base_url() -> str:
    return os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")


def get_judge_llm():
    client = AsyncOpenAI(api_key=_get_api_key(), base_url=_get_base_url())
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    return llm_factory(model, client=client)


def get_judge_embeddings():
    return embedding_factory(
        "huggingface",
        model=os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5"),
    )
