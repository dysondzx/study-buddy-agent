from langchain_core.tools import tool
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from app.config import settings

_embeddings = None
_vector_store = None


def _get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embeddings


def _get_vector_store():
    global _vector_store
    if _vector_store is None:
        try:
            _vector_store = Chroma(
                persist_directory=settings.CHROMA_PATH,
                embedding_function=_get_embeddings(),
            )
        except Exception:
            return None
    return _vector_store


@tool
def knowledge_search(query: str) -> str:
    """检索个人学习笔记知识库，获取与查询相关的笔记片段、学习要点、错题记录。

    当用户问"学过什么"、"某知识点的笔记"、"错题怎么解"、"某主题我记了什么"时调用。
    """
    vs = _get_vector_store()
    if vs is None:
        return "（知识库尚未初始化，请先将笔记放入 notes/ 目录并运行 build_index）"
    try:
        docs = vs.similarity_search(query, k=3)
    except Exception as e:
        return f"（检索失败：{e}）"
    if not docs:
        return "（知识库中未检索到相关内容）"
    return "\n\n".join(d.page_content for d in docs)
