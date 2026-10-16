"""会话与消息的持久化层（SQLite）。

职责很窄：只管 conversations / messages 两张表的读写，不掺任何 Agent 逻辑。
表结构见 app/data/init_db.py。
"""
import sqlite3
import uuid
from datetime import datetime

from app.config import settings, logger

TITLE_LIMIT = 20
"""自动标题的截断长度。"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _make_title(text: str) -> str:
    """用首条用户消息生成标题：压平空白后截断。"""
    flat = " ".join(text.split())
    if not flat:
        return "新对话"
    return flat[:TITLE_LIMIT] + ("…" if len(flat) > TITLE_LIMIT else "")


def create_conversation(title: str) -> str:
    cid = str(uuid.uuid4())
    now = _now()
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO conversations(id, title, created_at, updated_at)"
            " VALUES (?, ?, ?, ?)",
            (cid, title, now, now),
        )
        conn.commit()
    finally:
        conn.close()
    logger.info(f"新建会话：{cid}（{title}）")
    return cid


def ensure_conversation(conversation_id: str | None, first_message: str) -> str:
    """确定本次请求归属的会话。

    前端首次发消息时不带 id，这里就地新建；
    若带上来的 id 已失效（比如数据库被清过），也退化为新建，避免请求直接失败。
    """
    if conversation_id:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT id FROM conversations WHERE id = ?", (conversation_id,)
            ).fetchone()
        finally:
            conn.close()
        if row:
            return conversation_id
        logger.warning(f"会话 {conversation_id} 不存在，改为新建")

    return create_conversation(_make_title(first_message))


def list_conversations(limit: int = 100) -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT id, title, created_at, updated_at FROM conversations"
            " ORDER BY updated_at DESC, rowid DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_conversation(conversation_id: str) -> dict | None:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT id, title, created_at, updated_at FROM conversations WHERE id = ?",
            (conversation_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_conversation(conversation_id: str) -> bool:
    conn = _connect()
    try:
        cur = conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        conn.commit()
        deleted = cur.rowcount > 0
    finally:
        conn.close()
    if deleted:
        logger.info(f"删除会话：{conversation_id}")
    return deleted


def add_message(conversation_id: str, role: str, content: str) -> None:
    """追加一条消息，并刷新所属会话的 updated_at（列表按它倒序）。"""
    now = _now()
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO messages(conversation_id, role, content, created_at)"
            " VALUES (?, ?, ?, ?)",
            (conversation_id, role, content, now),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conversation_id),
        )
        conn.commit()
    finally:
        conn.close()


def list_messages(conversation_id: str) -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT id, role, content, created_at FROM messages"
            " WHERE conversation_id = ? ORDER BY id ASC",
            (conversation_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
