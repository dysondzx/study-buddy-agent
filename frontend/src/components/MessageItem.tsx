import type { ChatMessage } from "../types/chat";

interface Props {
  message: ChatMessage;
}

export default function MessageItem({ message }: Props) {
  const isUser = message.role === "user";
  return (
    <div className={`msg ${isUser ? "msg-user" : "msg-assistant"}`}>
      <div className="msg-label">{isUser ? "我" : "助手"}</div>
      <div className="msg-content">
        {message.content}
        {message.streaming && <span className="cursor">▋</span>}
      </div>
    </div>
  );
}
