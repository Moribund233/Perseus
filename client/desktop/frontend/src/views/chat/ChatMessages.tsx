import { useEffect, useMemo, useRef, useState } from 'react';
import { Avatar, Popover, Tooltip } from 'antd';
import { DeleteOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import Markdown from '../../components/Markdown';
import type { ChatMessage } from '../../api/chat';
import { useChatStore } from '../../stores/chat';
import { useIdentityStore } from '../../stores/identity';
import { getAvatarColor, getInitials } from '../../utils/avatar';

const borderColor = '#21262d';
const hoverBg = '#1c2333';
const textPrimary = '#e6edf3';
const textSecondary = '#8b949e';
const textTertiary = '#6e7681';
const bluePrimary = '#1f6feb';
const bgPrimary = '#0d1117';

const emojiPalette = [
  '👍', '👎', '👏', '🙏', '🔥', '🎉', '🚀', '✅',
  '❌', '⚠️', '💡', '👀', '😀', '😂', '😊', '🤔',
  '😎', '🥳', '😢', '😡', '❤️', '💪', '🐛', '📌',
];

const TYPING_TTL_MS = 4000;

function formatTime(dateStr: string | null): string {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function EmojiGrid({ onPick }: { onPick: (emoji: string) => void }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(8, 1fr)', gap: 2, width: 264, background: '#161b22', border: `1px solid ${borderColor}` }}>
      {emojiPalette.map((emoji) => (
        <button
          key={emoji}
          onClick={() => onPick(emoji)}
          style={{ background: 'transparent', border: 'none', fontSize: 16, cursor: 'pointer', padding: 4, borderRadius: 6, lineHeight: 1 }}
          onMouseEnter={(e) => { e.currentTarget.style.background = hoverBg; }}
          onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
        >
          {emoji}
        </button>
      ))}
    </div>
  );
}

export default function ChatMessages({ roomId, compact = false }: { roomId: string; compact?: boolean }) {
  const { t } = useTranslation();
  const me = useIdentityStore((s) => s.me);
  const messages = useChatStore((s) => s.messages[roomId] ?? []);
  const typingMap = useChatStore((s) => s.typingByRoom[roomId] ?? {});
  const toggleReaction = useChatStore((s) => s.toggleReaction);
  const pickReaction = useChatStore((s) => s.pickReaction);
  const deleteMessage = useChatStore((s) => s.deleteMessage);

  // typing 指示自动过期：定时器触发重渲染，过滤超时条目。
  const [, setTick] = useState(0);
  useEffect(() => {
    const timer = setInterval(() => setTick((v) => v + 1), 2000);
    return () => clearInterval(timer);
  }, []);

  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length]);

  const typingUsers = useMemo(
    () => Object.values(typingMap).filter((u) => Date.now() - u.ts < TYPING_TTL_MS),
    [typingMap],
  );

  // 消息按日期分组插入分隔条（今天 / 具体日期）。
  const rows = useMemo(() => {
    const out: Array<{ type: 'date'; key: string; label: string } | { type: 'msg'; key: string; msg: ChatMessage }> = [];
    let lastDate = '';
    const today = new Date().toDateString();
    for (const msg of messages) {
      const d = msg.created_at ? new Date(msg.created_at) : null;
      const dateKey = d ? d.toDateString() : '';
      if (dateKey && dateKey !== lastDate) {
        lastDate = dateKey;
        out.push({ type: 'date', key: `d-${dateKey}`, label: dateKey === today ? t('desktop.chat.today') : d!.toLocaleDateString() });
      }
      out.push({ type: 'msg', key: msg.id, msg });
    }
    return out;
  }, [messages, t]);

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: compact ? '10px 12px' : '16px 20px' }}>
      {messages.length === 0 && (
        <div style={{ textAlign: 'center', color: textTertiary, fontSize: 13, marginTop: 32 }}>
          {t('desktop.chat.noMessages')}
        </div>
      )}
      {rows.map((row) =>
        row.type === 'date' ? (
          <div key={row.key} style={{ textAlign: 'center', margin: '14px 0', position: 'relative' }}>
            <div style={{ position: 'absolute', left: 0, right: 0, top: '50%', height: 1, background: borderColor }} />
            <span style={{ background: bgPrimary, padding: '0 12px', fontSize: 11, color: textTertiary, position: 'relative', fontWeight: 500 }}>
              {row.label}
            </span>
          </div>
        ) : (
          <ChatMessageRow
            key={row.msg.id}
            msg={row.msg}
            meId={me?.id ?? null}
            compact={compact}
            onToggleReaction={toggleReaction}
            onPickReaction={pickReaction}
            onDelete={deleteMessage}
            t={t}
          />
        ),
      )}
      {typingUsers.length > 0 && (
        <div style={{ padding: '6px 4px', fontSize: 12, color: textTertiary }}>
          {typingUsers.map((u) => u.username).join(', ')} {t('desktop.chat.typing')}
        </div>
      )}
      <div ref={endRef} />
    </div>
  );
}

function ChatMessageRow({
  msg, meId, compact, onToggleReaction, onPickReaction, onDelete, t,
}: {
  msg: ChatMessage;
  meId: string | null;
  compact: boolean;
  onToggleReaction: (roomId: string, msgId: string, emoji: string, add: boolean) => void;
  onPickReaction: (roomId: string, msgId: string, emoji: string) => Promise<void>;
  onDelete: (roomId: string, msgId: string) => Promise<void>;
  t: (k: string) => string;
}) {
  const author = msg.sender_username || '?';
  const initials = getInitials(author);
  const own = meId != null && msg.sender_id === meId;

  return (
    <div
      className="chat-msg"
      style={{
        display: 'flex',
        gap: 10,
        padding: '6px 0',
        borderRadius: 8,
      }}
      onMouseEnter={(e) => { e.currentTarget.style.background = hoverBg; }}
      onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
    >
      <Avatar size={compact ? 26 : 34} style={{ background: getAvatarColor(initials), fontSize: 12, fontWeight: 600, marginTop: 2, flexShrink: 0 }}>
        {initials}
      </Avatar>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
          <span style={{ fontSize: compact ? 13 : 14, fontWeight: 600, color: textPrimary }}>{author}</span>
          <span style={{ fontSize: 11, color: textTertiary }}>{formatTime(msg.created_at)}</span>
          {own && (
            <Tooltip title={t('desktop.chat.delete')}>
              <button
                onClick={() => { void onDelete(msg.room_id, msg.id); }}
                className="chat-delete-btn"
                style={{ background: 'none', border: 'none', color: textTertiary, cursor: 'pointer', padding: 0, lineHeight: 1, marginLeft: 'auto', opacity: 0, transition: 'opacity 0.15s' }}
                onMouseEnter={(e) => { e.currentTarget.style.color = '#f85149'; }}
                onMouseLeave={(e) => { e.currentTarget.style.color = textTertiary; }}
              >
                <DeleteOutlined style={{ fontSize: 12 }} />
              </button>
            </Tooltip>
          )}
        </div>
        <div style={{ fontSize: compact ? 13 : 14, lineHeight: 1.5, color: textSecondary, wordBreak: 'break-word' }}>
          <Markdown collapsibleCode>{msg.content}</Markdown>
        </div>
        <div className="chat-reactions" style={{ display: 'flex', gap: 4, marginTop: 4, flexWrap: 'wrap' }}>
          {(msg.reactions ?? []).map((r, idx) => (
            <span
              key={idx}
              onClick={() => onToggleReaction(msg.room_id, msg.id, r.emoji, !r.active)}
              style={{
                display: 'flex', alignItems: 'center', gap: 4, padding: '2px 8px', borderRadius: 12, fontSize: 12, cursor: 'pointer',
                background: r.active ? 'rgba(31,111,235,0.15)' : bgPrimary,
                border: `1px solid ${r.active ? bluePrimary : '#30363d'}`,
              }}
            >
              {r.emoji} <span style={{ fontSize: 11, color: textSecondary }}>{r.count}</span>
            </span>
          ))}
          <Popover trigger="click" content={<EmojiGrid onPick={(emoji) => { void onPickReaction(msg.room_id, msg.id, emoji); }} />}>
            <button
              style={{ background: 'transparent', border: '1px dashed #30363d', borderRadius: 12, color: textTertiary, fontSize: 12, padding: '0 8px', cursor: 'pointer', opacity: 0, transition: 'opacity 0.15s' }}
              className="chat-add-reaction"
            >
              +
            </button>
          </Popover>
        </div>
      </div>
    </div>
  );
}
