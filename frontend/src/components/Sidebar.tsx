import type { ConversationSummary } from "../types/chat";

interface Props {
  conversations: ConversationSummary[];
  currentId: string | null;
  /** 流式回答期间禁用交互，避免会话被中途切换导致消息写错位置 */
  disabled: boolean;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
}

/** 后端返回形如 2026-10-16T09:03:36，直接截取到分钟即可 */
function formatTime(iso: string): string {
  return iso.length >= 16 ? `${iso.slice(5, 10)} ${iso.slice(11, 16)}` : iso;
}

export default function Sidebar({
  conversations,
  currentId,
  disabled,
  onSelect,
  onNew,
  onDelete,
}: Props) {
  return (
    <aside className="sidebar">
      <button className="new-chat" onClick={onNew} disabled={disabled}>
        ＋ 新对话
      </button>

      <div className="conv-list">
        {conversations.length === 0 && (
          <div className="conv-empty">暂无历史记录</div>
        )}
        {conversations.map((conv) => (
          <div
            key={conv.id}
            className={`conv-item${conv.id === currentId ? " active" : ""}`}
            onClick={() => !disabled && onSelect(conv.id)}
            title={conv.title}
          >
            <div className="conv-main">
              <div className="conv-title">{conv.title}</div>
              <div className="conv-time">{formatTime(conv.updated_at)}</div>
            </div>
            <button
              className="conv-del"
              title="删除该会话"
              disabled={disabled}
              onClick={(e) => {
                e.stopPropagation();
                onDelete(conv.id);
              }}
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </aside>
  );
}
