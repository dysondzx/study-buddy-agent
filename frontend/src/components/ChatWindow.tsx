import { useRef, useEffect } from "react";
import type { ChatMessage } from "../types/chat";
import MessageList from "./MessageList";

interface Props {
  messages: ChatMessage[];
}

export default function ChatWindow({ messages }: Props) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="chat-window">
      {messages.length === 0 && (
        <div className="empty-hint">
          👋 你好！我是你的个人学习生活助手，由 3 个 Agent 协作：
          <br />
          📋 <b>规划师</b> — 拆解目标、排日程
          <br />
          📚 <b>知识管家</b> — 检索笔记、关联知识点
          <br />
          📊 <b>追踪者</b> — 记录学习、打卡、统计
          <br />
          <br />
          试试问：
          <br />
          · 帮我制定一个 2 周学完 FastAPI 的计划
          <br />
          · 我在 RAG 评估那里记了什么？
          <br />
          · 这个月我学了多少小时？
          <br />
          · 学 RAG 之前需要先懂什么？
          <br />
          · 我下周怎么安排复习？
        </div>
      )}
      <MessageList messages={messages} />
      <div ref={endRef} />
    </div>
  );
}
