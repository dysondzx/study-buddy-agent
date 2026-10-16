import type { ChatMessage } from "../types/chat";
import MessageItem from "./MessageItem";

interface Props {
  messages: ChatMessage[];
}

export default function MessageList({ messages }: Props) {
  return (
    <>
      {messages.map((msg, i) => (
        <MessageItem key={i} message={msg} />
      ))}
    </>
  );
}
