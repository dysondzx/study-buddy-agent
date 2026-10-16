import sqlite3
from app.config import settings, logger

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS study_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        subject TEXT NOT NULL,
        duration_minutes INTEGER NOT NULL,
        notes TEXT DEFAULT ''
    )""",
    """CREATE TABLE IF NOT EXISTS habit_checkin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        habit TEXT NOT NULL,
        done INTEGER NOT NULL DEFAULT 0
    )""",
    """CREATE TABLE IF NOT EXISTS learning_goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        target_date TEXT,
        status TEXT DEFAULT '进行中'
    )""",
    """CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL DEFAULT '新对话',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""",
    """CREATE INDEX IF NOT EXISTS idx_messages_conversation
        ON messages(conversation_id, id)""",
]

SAMPLE_DATA = [
    "INSERT OR IGNORE INTO study_log VALUES (1,'2026-10-01','RAG 基础',90,'向量检索与 Embedding')",
    "INSERT OR IGNORE INTO study_log VALUES (2,'2026-10-02','LangGraph',120,'状态机与条件边')",
    "INSERT OR IGNORE INTO study_log VALUES (3,'2026-10-03','RAG 评估',60,'RAGAS 指标')",
    "INSERT OR IGNORE INTO habit_checkin VALUES (1,'2026-10-01','早起',1)",
    "INSERT OR IGNORE INTO habit_checkin VALUES (2,'2026-10-02','早起',1)",
    "INSERT OR IGNORE INTO habit_checkin VALUES (3,'2026-10-03','运动',0)",
    "INSERT OR IGNORE INTO learning_goals VALUES (1,'掌握 RAG 全流程','2026-10-31','进行中')",
]


def init_sqlite_db():
    conn = sqlite3.connect(settings.SQLITE_PATH)
    cur = conn.cursor()
    for ddl in SCHEMA:
        cur.execute(ddl)
    for stmt in SAMPLE_DATA:
        cur.execute(stmt)
    conn.commit()
    conn.close()
    logger.info(f"SQLite 初始化完成：{settings.SQLITE_PATH}")
    logger.info(
        "表：study_log / habit_checkin / learning_goals（含示例数据）"
        " / conversations / messages"
    )


if __name__ == "__main__":
    init_sqlite_db()
