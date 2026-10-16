import { useCallback, useEffect, useState } from "react";
import type { ChatMessage, ConversationSummary } from "./types/chat";
import Sidebar from "./components/Sidebar";
import ChatWindow from "./components/ChatWindow";
import InputBar from "./components/InputBar";
import {
  deleteConversation,
  getConversation,
  listConversations,
  streamChat,
} from "./api/client";

export default function App() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  /** null 表示尚未落库的新会话（首次发送后由服务端创建并回传 id） */
  const [currentId, setCurrentId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);

  const refreshConversations = useCallback(async () => {
    try {
      setConversations(await listConversations());
    } catch (err) {
      console.error("加载会话列表失败", err);
    }
  }, []);

  useEffect(() => {
    void refreshConversations();
  }, [refreshConversations]);

  const handleNew = () => {
    setCurrentId(null);
    setMessages([]);
  };

  const handleSelect = async (id: string) => {
    if (id === currentId) return;
    try {
      const detail = await getConversation(id);
      setCurrentId(detail.id);
      setMessages(
        detail.messages.map((m) => ({ role: m.role, content: m.content })),
      );
    } catch (err) {
      console.error("加载会话失败", err);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteConversation(id);
      if (id === currentId) {
        setCurrentId(null);
        setMessages([]);
      }
      await refreshConversations();
    } catch (err) {
      console.error("删除会话失败", err);
    }
  };

  const handleSend = async (text: string) => {
    const userMsg: ChatMessage = { role: "user", content: text };
    const assistantMsg: ChatMessage = {
      role: "assistant",
      content: "",
      streaming: true,
    };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setLoading(true);

    let acc = "";
    try {
      for await (const event of streamChat(text, currentId)) {
        if (event.type === "meta" && event.conversation_id) {
          // 首轮：服务端已建好会话，前端归位到该 id
          setCurrentId(event.conversation_id);
        } else if (event.type === "message" && event.content) {
          acc += event.content;
          setMessages((prev) => {
            const next = [...prev];
            next[next.length - 1] = {
              role: "assistant",
              content: acc,
              streaming: true,
            };
            return next;
          });
        } else if (event.type === "error" && !acc) {
          // 已有部分内容时保留，只有完全没吐字才用错误提示占位
          acc = event.content
            ? `（服务端发生错误：${event.content}）`
            : "（服务端发生错误）";
        }
      }
    } catch (err) {
      acc =
        acc || `（请求出错：${err instanceof Error ? err.message : "未知错误"}）`;
    }

    setMessages((prev) => {
      const next = [...prev];
      next[next.length - 1] = {
        role: "assistant",
        content: acc || "（无回复）",
        streaming: false,
      };
      return next;
    });
    setLoading(false);
    // 标题与排序由后端基于落库结果生成，这里拉一次最新列表
    void refreshConversations();
  };

  return (
    <div className="app">
      <Sidebar
        conversations={conversations}
        currentId={currentId}
        disabled={loading}
        onSelect={handleSelect}
        onNew={handleNew}
        onDelete={handleDelete}
      />
      <div className="main">
        <header className="app-header">🎓 学伴智能体助手</header>
        <ChatWindow messages={messages} />
        <InputBar onSend={handleSend} disabled={loading} />
      </div>
    </div>
  );
}
