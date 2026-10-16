export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
}

export interface SSEData {
  type: "meta" | "message" | "done" | "error";
  content?: string;
  /** 仅 type === "meta" 时下发，首轮会话由服务端创建后回传真实 id */
  conversation_id?: string;
}

export interface ConversationSummary {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface StoredMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface ConversationDetail extends ConversationSummary {
  messages: StoredMessage[];
}
