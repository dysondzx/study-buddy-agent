from langchain.agents import create_agent
from app.config import get_llm, logger
from app.tools.knowledge_base import knowledge_search
from app.data.knowledge_graph import knowledge_graph_query

_knowledge = None


def get_knowledge_agent():
    """知识管家 Agent：检索笔记与知识关联，回答"我学过什么"。

    工具集：知识库（Vector RAG 检索笔记）+ 知识图谱（知识点关联）
    """
    global _knowledge
    if _knowledge is None:
        _knowledge = create_agent(
            model=get_llm(temperature=0.1),
            tools=[knowledge_search, knowledge_graph_query],
            system_prompt="""你是「知识管家」Agent，负责管理用户的学习笔记与知识体系。

能力：
1. 通过 knowledge_search 检索用户的笔记、资料、错题，回答"我学过什么"、"某主题记了什么"。
2. 通过 knowledge_graph_query 补充知识点之间的依赖与关联，说明"学 A 之前要懂 B"。

回答要求：
- 明确区分"来自笔记的事实"和"图谱推断的关系"。
- 如果检索不到，如实说明"知识库中未找到"，不要编造。
- 涉及错题时给出关键要点。""",
        ).with_config({"recursion_limit": 12})
        logger.info("Knowledge Agent 构建完成")
    return _knowledge


async def run_knowledge(user_input: str) -> str:
    result = await get_knowledge_agent().ainvoke(
        {"messages": [{"role": "user", "content": user_input}]},
        config={"recursion_limit": 12},
    )
    for msg in reversed(result["messages"]):
        if getattr(msg, "content", None) and not getattr(msg, "tool_calls", None):
            return msg.content
    return "（知识管家未能生成回复）"
