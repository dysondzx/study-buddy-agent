import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agents.orchestrator import build_graph
from app.config import logger
from app.data import conversations as store

router = APIRouter()
_graph = None

NO_REPLY = "（无回复）"


def _get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    """为空表示新会话，服务端会就地创建并通过 meta 事件回传真实 id。"""


@router.post("/api/chat")
async def chat(req: ChatRequest):
    """SSE 流式返回多 Agent 编排结果。

    事件类型：
      - meta:     携带 conversation_id（首轮新建时前端据此归位）
      - message:  正文增量
      - error:    编排异常
      - done:     结束标记
    """
    graph = _get_graph()

    async def event_stream():
        # 会话归位：先把用户消息落库，再开始编排，避免流中断时丢失提问
        conversation_id = store.ensure_conversation(req.conversation_id, req.message)
        store.add_message(conversation_id, "user", req.message)
        yield _sse({"type": "meta", "conversation_id": conversation_id})

        answer = ""
        try:
            async for chunk, metadata in graph.astream(
                {"user_input": req.message},
                stream_mode="messages",
            ):
                # 只转发最终回答节点（synthesizer）的 token
                if metadata.get("langgraph_node") != "synthesizer":
                    continue
                if isinstance(chunk.content, str) and chunk.content:
                    answer += chunk.content
                    yield _sse({"type": "message", "content": chunk.content})
        except Exception as e:
            logger.error(f"编排执行出错: {e}")
            if not answer:
                # 一个字都没吐出来时，把错误写进历史，避免留下空白的助手消息
                answer = f"（服务端发生错误：{e}）"
            yield _sse({"type": "error", "content": str(e)})
        finally:
            # 无论成功、报错还是客户端断开，都保存已产生的回答
            try:
                store.add_message(conversation_id, "assistant", answer or NO_REPLY)
            except Exception as e:
                logger.error(f"保存助手回复失败: {e}")
            yield _sse({"type": "done"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
