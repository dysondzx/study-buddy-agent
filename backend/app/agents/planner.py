from langchain.agents import create_agent
from app.config import get_llm, logger
from app.data.knowledge_graph import knowledge_graph_query
from app.tools.study_db import query_study_data

_planner = None


def get_planner():
    """规划师 Agent：拆解目标、排日程、分配学习任务。

    工具集：知识图谱（查知识点依赖）+ 学习数据（参考历史学习节奏）
    """
    global _planner
    if _planner is None:
        _planner = create_agent(
            model=get_llm(temperature=0.2),
            tools=[knowledge_graph_query, query_study_data],
            system_prompt="""你是「规划师」Agent，负责把模糊的学习目标拆解成可执行的学习计划。

能力：
1. 目标拆解：将"一个月学会 RAG"拆成按周/按天的任务列表。
2. 依赖识别：通过 knowledge_graph_query 判断知识点先后关系，避免倒序学习。
3. 节奏参考：通过 query_study_data 了解用户历史学习节奏，量力排期。

输出要求：
- 用清晰的列表结构呈现计划（第 X 天 / 第 X 周）。
- 标注每个任务的前置依赖。
- 结尾给一句鼓励。

只做规划，不检索笔记细节。""",
        ).with_config({"recursion_limit": 12})
        logger.info("Planner Agent 构建完成")
    return _planner


async def run_planner(user_input: str) -> str:
    result = await get_planner().ainvoke(
        {"messages": [{"role": "user", "content": user_input}]},
        config={"recursion_limit": 12},
    )
    for msg in reversed(result["messages"]):
        if getattr(msg, "content", None) and not getattr(msg, "tool_calls", None):
            return msg.content
    return "（规划师未能生成回复）"
