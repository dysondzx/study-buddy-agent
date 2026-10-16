import type {
  ConversationDetail,
  ConversationSummary,
  SSEData,
} from "../types/chat";

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(url, init);
  if (!resp.ok) {
    throw new Error(`HTTP ${resp.status}`);
  }
  return (await resp.json()) as T;
}

/** 会话列表，按最近更新倒序 */
export async function listConversations(): Promise<ConversationSummary[]> {
  const data = await request<{ conversations: ConversationSummary[] }>(
    "/api/conversations",
  );
  return data.conversations;
}

/** 单个会话的详情（含全部历史消息） */
export function getConversation(id: string): Promise<ConversationDetail> {
  return request<ConversationDetail>(`/api/conversations/${encodeURIComponent(id)}`);
}

export async function deleteConversation(id: string): Promise<void> {
  await request<{ ok: boolean }>(`/api/conversations/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}

/**
 * SSE 流式客户端：用 fetch + ReadableStream 解析 SSE 协议。
 * 不用原生 EventSource（只支持 GET，无法 POST JSON body）。
 *
 * conversationId 为 null 时由服务端新建会话，并通过首个 meta 事件回传 id。
 */
export async function* streamChat(
  message: string,
  conversationId: string | null,
): AsyncGenerator<SSEData> {
  const resp = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, conversation_id: conversationId }),
  });
  if (!resp.ok || !resp.body) {
    throw new Error(`HTTP ${resp.status}`);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    // SSE 以 \n\n 分隔事件；最后一段可能不完整，留到下次
    const events = buffer.split("\n\n");
    buffer = events.pop() || "";
    for (const evt of events) {
      const line = evt.split("\n").find((l) => l.startsWith("data:"));
      if (!line) continue;
      const data = line.slice(5).trim();
      if (!data) continue;
      try {
        yield JSON.parse(data) as SSEData;
      } catch {
        // 忽略解析失败的行
      }
    }
  }
}
