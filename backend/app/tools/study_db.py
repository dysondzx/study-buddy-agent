from langchain_core.tools import tool
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain.agents import create_agent
from app.config import settings, get_llm, logger

_sql_agent = None


def _get_sql_agent():
    global _sql_agent
    if _sql_agent is None:
        llm = get_llm(temperature=0)
        db = SQLDatabase.from_uri(
            f"sqlite:///{settings.SQLITE_PATH}",
            include_tables=["study_log", "habit_checkin", "learning_goals"],
        )
        toolkit = SQLDatabaseToolkit(db=db, llm=llm)
        # create_agent 不接受 max_iterations，用 with_config 设置迭代上限
        _sql_agent = create_agent(
            model=llm,
            tools=toolkit.get_tools(),
            system_prompt="""你是一个个人学习生活数据查询智能体。将用户的自然语言问题转换为正确的 SQLite 查询并返回结果。

规则：
1. 只允许 SELECT 查询，禁止 INSERT/UPDATE/DELETE/DROP。
2. 涉及时间的查询请使用 date 字段，格式为 YYYY-MM-DD。
3. 表结构：
   - study_log(id, date, subject, duration_minutes, notes)  学习记录
   - habit_checkin(id, date, habit, done)                  习惯打卡
   - learning_goals(id, title, target_date, status)        学习目标
4. 生成 SQL 后必须先验证再执行；出错时重写并重试。
""",
        ).with_config({"recursion_limit": 12})
        logger.info("Study DB Agent 初始化完成")
    return _sql_agent


@tool
def record_study(subject: str, duration_minutes: int, notes: str = "", date: str = "") -> str:
    """记录一次学习行为（写入 study_log）。

    subject: 学习科目；duration_minutes: 学习时长（分钟）；notes: 备注；date: 日期 YYYY-MM-DD，留空则取今天。
    """
    import sqlite3
    from datetime import date as date_cls
    if not date:
        date = date_cls.today().isoformat()
    conn = sqlite3.connect(settings.SQLITE_PATH)
    conn.execute(
        "INSERT INTO study_log(date, subject, duration_minutes, notes) VALUES (?, ?, ?, ?)",
        (date, subject, duration_minutes, notes),
    )
    conn.commit()
    conn.close()
    return f"已记录：{date} 学习 {subject} {duration_minutes} 分钟"


@tool
def record_habit(habit: str, done: bool, date: str = "") -> str:
    """记录一次习惯打卡（写入 habit_checkin）。

    habit: 习惯名称（如 早起/运动/阅读）；done: 是否完成（true/false）。
    """
    import sqlite3
    from datetime import date as date_cls
    if not date:
        date = date_cls.today().isoformat()
    conn = sqlite3.connect(settings.SQLITE_PATH)
    conn.execute(
        "INSERT INTO habit_checkin(date, habit, done) VALUES (?, ?, ?)",
        (date, habit, 1 if done else 0),
    )
    conn.commit()
    conn.close()
    return f"已记录：{date} 习惯「{habit}」{'已完成' if done else '未完成'}"


@tool
def query_study_data(question: str) -> str:
    """查询学习生活结构化数据，获取精确统计、趋势、汇总。

    当用户问"这个月学了多少小时"、"连续打卡几天"、"哪个科目学得最多"、"目标完成情况"时调用。
    """
    agent = _get_sql_agent()
    result = agent.invoke({"messages": [{"role": "user", "content": question}]})
    return result["messages"][-1].content
