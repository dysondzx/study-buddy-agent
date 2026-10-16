from pathlib import Path
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.config import settings, logger


def load_notes(notes_dir: str = None) -> list:
    """加载 notes/ 目录下的 Markdown/TXT 笔记并切块。
    """
    if notes_dir is None:
        notes_dir = settings.NOTES_DIR

    p = Path(notes_dir)
    # 必须显式指定 UTF-8：否则在 Windows 上会退回 GBK，中文笔记直接解码失败
    loader = DirectoryLoader(
        str(p),
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
        show_progress=False,
    )
    docs = loader.load()
    logger.info(f"从 {notes_dir} 加载了 {len(docs)} 份笔记")
    if not docs:
        logger.warning(f"{notes_dir} 下没有找到 Markdown 笔记，索引将为空")

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    return splitter.split_documents(docs)


def build_chroma_index():
    embeddings = HuggingFaceEmbeddings(
        model_name=settings.EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    chunks = load_notes()
    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=settings.CHROMA_PATH,
    )
    logger.info(f"Chroma 索引构建完成：{settings.CHROMA_PATH}（{len(chunks)} 个块）")


if __name__ == "__main__":
    build_chroma_index()
