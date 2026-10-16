from langchain.agents import create_agent
from app.config import get_llm, logger
from app.tools.study_db import record_study, record_habit, query_study_data

_tracker = None


def get_tracker():
    """追踪者 Agent：记录学习行为、打卡，统计趋势与反馈。

    工具集：record_study / record_habit（写入）+ query_study_data（统计）
    """
    global _tracker
    if _tracker is None:
        _tracker = create_agent(
            model=get_llm(temperature=0),
            tools=[record_study, record_habit, query_study_data],
            system_prompt="""你是「追踪者」Agent，负责记录用户的学习行为与习惯，并提供统计反馈。

能力：
1. 记录：通过 record_study 记录学习科目与时长；通过 record_habit 记录习惯打卡。
2. 统计：通过 query_study_data 回答"这个月学了多少小时"、"连续打卡几天"、"哪个科目投入最多"。

回答要求：
- 记录类请求先执行工具再给确认。
- 统计类请求给出具体数字 + 一句趋势点评（如"本周学习时长较上周上升 20%"）。
- 鼓励用户坚持。""",
        ).with_config({"recursion_limit": 12})
        logger.info("Tracker Agent 构建完成")
    return _tracker


async def run_tracker(user_input: str) -> str:
    result = await get_tracker().ainvoke(
        {"messages": [{"role": "user", "content": user_input}]},
        config={"recursion_limit": 12},
    )
    for msg in reversed(result["messages"]):
        if getattr(msg, "content", None) and not getattr(msg, "tool_calls", None):
            return msg.content
    return "（追踪者未能生成回复）"
