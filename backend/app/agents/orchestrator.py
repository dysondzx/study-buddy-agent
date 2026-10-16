"""
编排中枢：意图路由 + LangGraph 状态机。
"""

from typing import TypedDict

from langgraph.graph import StateGraph, END

from app.config import get_llm
from app.agents.planner import run_planner
from app.agents.knowledge import run_knowledge
from app.agents.tracker import run_tracker


class AgentState(TypedDict):
    user_input: str
    intent: str
    plan: str
    knowledge: str
    track: str


async def router_node(state: AgentState) -> dict:
    """意图识别：判断该走哪个 Agent。

    关键词路由（确定性、可解释、不消耗 LLM 调用），兜底交给 hybrid。
    """
    text = state["user_input"]
    kw_plan = ["计划", "安排", "目标", "排期", "拆解", "周计划", "日程"]
    kw_knowledge = ["学过", "笔记", "知识", "记得", "错题", "知识点", "记了什么"]
    kw_track = ["打卡", "记录", "习惯", "统计", "学了多久", "多少小时", "连续"]
    score = {
        "plan": sum(k in text for k in kw_plan),
        "knowledge": sum(k in text for k in kw_knowledge),
        "track": sum(k in text for k in kw_track),
    }
    # 若多个维度命中或都不命中，走 hybrid（串联多个 Agent 综合分析）
    top = max(score.values())
    if top == 0 or list(score.values()).count(top) > 1:
        return {"intent": "hybrid"}
    intent = max(score, key=score.get)
    return {"intent": intent}


async def planner_node(state: AgentState) -> dict:
    out = await run_planner(state["user_input"])
    return {"plan": out}


async def knowledge_node(state: AgentState) -> dict:
    out = await run_knowledge(state["user_input"])
    return {"knowledge": out}


async def tracker_node(state: AgentState) -> dict:
    out = await run_tracker(state["user_input"])
    return {"track": out}


async def synthesizer_node(state: AgentState) -> dict:
    """汇总各 Agent 输出，生成最终回复。

    hybrid 模式下多个 Agent 都有产出，由合成器整合成一段连贯回答；
    结果不写入 state，而是作为 LLM token 流给调用方。
    """
    parts = []
    if state.get("plan"):
        parts.append(f"~ 规划：\n{state['plan']}")
    if state.get("knowledge"):
        parts.append(f"~ 知识：\n{state['knowledge']}")
    if state.get("track"):
        parts.append(f"~ 追踪：\n{state['track']}")

    # 统一交给 LLM 合成（单路也走这里，否则不会产生 token，前端就收不到内容）
    combined = "\n\n".join(parts)
    prompt = f"""用户问题：{state['user_input']}

        以下是各助手分别给出的内容，请综合成一段连贯、有条理的回答：
        {combined}

        要求：保留关键信息，去重，按"结论 → 依据 → 建议"组织。"""
    llm = get_llm(temperature=0.3)
    await llm.ainvoke([{"role": "user", "content": prompt}])
    return {}


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("router", router_node)
    g.add_node("planner", planner_node)
    g.add_node("knowledge", knowledge_node)
    g.add_node("tracker", tracker_node)
    g.add_node("synthesizer", synthesizer_node)

    g.set_entry_point("router")

    # 入口路由：单意图直接进对应 Agent，hybrid 统一从 planner 开始
    g.add_conditional_edges(
        "router",
        lambda state: state["intent"],
        {
            "plan": "planner",
            "knowledge": "knowledge",
            "track": "tracker",
            "hybrid": "planner",
        },
    )

    def after_planner(state):
        return "knowledge" if state["intent"] == "hybrid" else "synthesizer"

    def after_knowledge(state):
        return "tracker" if state["intent"] == "hybrid" else "synthesizer"

    g.add_conditional_edges(
        "planner",
        after_planner,
        {"knowledge": "knowledge", "synthesizer": "synthesizer"},
    )
    g.add_conditional_edges(
        "knowledge",
        after_knowledge,
        {"tracker": "tracker", "synthesizer": "synthesizer"},
    )

    g.add_edge("tracker", "synthesizer")
    g.add_edge("synthesizer", END)

    return g.compile()
