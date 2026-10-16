"""会话历史的 HTTP 接口：列表、详情、删除。

创建会话不单独暴露接口——前端首次发消息时由 /api/chat 就地建立，
避免出现「点了新对话但没说话」的空会话。
"""
from fastapi import APIRouter, HTTPException

from app.data import conversations as store

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("")
async def list_conversations():
    return {"conversations": store.list_conversations()}


@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str):
    conv = store.get_conversation(conversation_id)
    if conv is None:
        raise HTTPException(404, "会话不存在")
    conv["messages"] = store.list_messages(conversation_id)
    return conv


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str):
    if not store.delete_conversation(conversation_id):
        raise HTTPException(404, "会话不存在")
    return {"ok": True}
