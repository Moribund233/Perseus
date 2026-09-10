import { useCallback, useRef, useState } from 'react';
import { Button, Input, Popover, Tooltip } from 'antd';
import {
  BoldOutlined,
  CodeOutlined,
  ItalicOutlined,
  LinkOutlined,
  PaperClipOutlined,
  SendOutlined,
  SmileOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { chatApi } from '../../api/chat';
import { useChatStore } from '../../stores/chat';
import { useServersStore } from '../../stores/servers';

const borderColor = '#21262d';
const textPrimary = '#e6edf3';
const textTertiary = '#6e7681';
const bluePrimary = '#1f6feb';
const bgTertiary = '#1c2128';

const emojiPalette = [
  '😀', '😂', '🤣', '😊', '😍', '🤔', '😎', '🥳',
  '😢', '😡', '👍', '👎', '👏', '🙌', '🤝', '💪',
  '🔥', '⭐', '🎉', '🚀', '✅', '❌', '⚠️', '💡',
  '🐛', '📌', '👀', '❤️', '🙏', '😅', '🫡', '🤖',
];

const TYPING_INTERVAL_MS = 2000;

export default function ChatComposer({ roomId, roomName, compact = false }: { roomId: string; roomName: string; compact?: boolean }) {
  const { t } = useTranslation();
  const serverId = useServersStore((s) => s.currentServerId);
  const status = useChatStore((s) => s.status);
  const sendMessage = useChatStore((s) => s.sendMessage);
  const sendTyping = useChatStore((s) => s.sendTyping);

  const [input, setInput] = useState('');
  const [uploading, setUploading] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const lastTypingRef = useRef(0);

  const connected = status === 'connected';

  const getTextAreaEl = (): HTMLTextAreaElement | null =>
    boxRef.current?.querySelector('textarea') ?? null;

  const insertAtCursor = useCallback((text: string, wrap?: string) => {
    const el = getTextAreaEl();
    const start = el?.selectionStart ?? input.length;
    const end = el?.selectionEnd ?? input.length;
    const selected = input.slice(start, end);
    const inserted = wrap != null ? `${wrap}${selected || text}${wrap}` : text;
    const next = input.slice(0, start) + inserted + input.slice(end);
    setInput(next);
    requestAnimationFrame(() => {
      if (!el) return;
      el.focus();
      const caret = start + inserted.length;
      el.setSelectionRange(caret, caret);
    });
  }, [input]);

  const insertLink = useCallback(() => {
    const el = getTextAreaEl();
    const start = el?.selectionStart ?? input.length;
    const end = el?.selectionEnd ?? input.length;
    const selected = input.slice(start, end);
    const isUrl = /^https?:\/\//.test(selected);
    const inserted = isUrl ? `[文本](${selected})` : `[${selected || '文本'}](https://)`;
    const next = input.slice(0, start) + inserted + input.slice(end);
    setInput(next);
    requestAnimationFrame(() => {
      if (!el) return;
      el.focus();
      el.setSelectionRange(start + inserted.length, start + inserted.length);
    });
  }, [input]);

  const handleSend = useCallback(() => {
    const content = input.trim();
    if (!content || !connected) return;
    sendMessage(roomId, content);
    sendTyping(roomId, false);
    setInput('');
  }, [input, connected, roomId, sendMessage, sendTyping]);

  const handleChange = (value: string) => {
    setInput(value);
    const now = Date.now();
    if (value && now - lastTypingRef.current > TYPING_INTERVAL_MS) {
      lastTypingRef.current = now;
      sendTyping(roomId, true);
    }
  };

  const handleFileSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file || !serverId) return;
    if (!connected) return;
    setUploading(true);
    try {
      const att = await chatApi.uploadAttachment(serverId, roomId, file);
      const content = att.content_type.startsWith('image/')
        ? `![${att.name}](${att.url})`
        : `[${att.name}](${att.url})`;
      sendMessage(roomId, content);
    } finally {
      setUploading(false);
    }
  };

  const iconBtn = (title: string, node: React.ReactNode, onClick: () => void) => (
    <Tooltip title={title}>
      <Button type="text" size="small" icon={node} onClick={onClick} />
    </Tooltip>
  );

  return (
    <div style={{ padding: compact ? '8px 12px 12px' : '12px 20px', borderTop: `1px solid ${borderColor}`, flexShrink: 0 }}>
      <div style={{ background: bgTertiary, border: '1px solid #30363d', borderRadius: 12, overflow: 'hidden' }}>
        <div ref={boxRef}>
          <Input.TextArea
            value={input}
            onChange={(e) => handleChange(e.target.value)}
            onPressEnter={(e) => {
              if (!e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder={t('desktop.chat.placeholder', { channel: roomName })}
            autoSize={{ minRows: 1, maxRows: compact ? 3 : 4 }}
            disabled={!connected}
            style={{ background: 'transparent', border: 'none', color: textPrimary, resize: 'none', padding: compact ? '8px 12px' : '12px 14px' }}
          />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', padding: '4px 8px', gap: 2, borderTop: '1px solid #30363d' }}>
          <input ref={fileInputRef} type="file" style={{ display: 'none' }} onChange={handleFileSelected} />
          <Tooltip title={t('desktop.chat.attach')}>
            <Button type="text" size="small" loading={uploading} icon={<PaperClipOutlined style={{ fontSize: 14, color: textTertiary }} />} onClick={() => fileInputRef.current?.click()} />
          </Tooltip>
          <Popover trigger="click" content={
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(8, 1fr)', gap: 2, width: 264 }}>
              {emojiPalette.map((emoji) => (
                <button
                  key={emoji}
                  onClick={() => { insertAtCursor(emoji); }}
                  style={{ background: 'transparent', border: 'none', fontSize: 18, cursor: 'pointer', padding: 4, borderRadius: 6, lineHeight: 1 }}
                  onMouseEnter={(e) => { e.currentTarget.style.background = '#1c2333'; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
                >
                  {emoji}
                </button>
              ))}
            </div>
          }>
            <Button type="text" size="small" icon={<SmileOutlined style={{ fontSize: 14, color: textTertiary }} />} />
          </Popover>
          {iconBtn(t('desktop.chat.bold'), <BoldOutlined style={{ fontSize: 14, color: textTertiary }} />, () => insertAtCursor(t('desktop.chat.boldText'), '**'))}
          {iconBtn(t('desktop.chat.italic'), <ItalicOutlined style={{ fontSize: 14, color: textTertiary }} />, () => insertAtCursor(t('desktop.chat.italicText'), '*'))}
          {iconBtn(t('desktop.chat.code'), <CodeOutlined style={{ fontSize: 14, color: textTertiary }} />, () => insertAtCursor('code', '`'))}
          {iconBtn(t('desktop.chat.link'), <LinkOutlined style={{ fontSize: 14, color: textTertiary }} />, insertLink)}
          {!compact && <span style={{ fontSize: 11, color: textTertiary, marginLeft: 6 }}>{t('desktop.chat.sendHint')}</span>}
          <Tooltip title={connected ? 'Enter' : t('desktop.chat.disconnected')}>
            <Button
              type="primary"
              size="small"
              icon={<SendOutlined style={{ fontSize: 14 }} />}
              onClick={handleSend}
              disabled={!connected || !input.trim()}
              style={{ marginLeft: 'auto', background: bluePrimary, borderColor: bluePrimary }}
            />
          </Tooltip>
        </div>
      </div>
    </div>
  );
}
