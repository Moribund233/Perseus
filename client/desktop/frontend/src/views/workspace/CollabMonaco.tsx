import { Tooltip } from 'antd';
import { useTranslation } from 'react-i18next';
import type { CollabParticipant, CollabStatus } from '../../api/collabSocket';

const green = '#3fb950';
const yellow = '#d29922';

const STATUS_COLOR: Record<CollabStatus, string> = {
  connected: green,
  connecting: yellow,
  disconnected: '#6e7681',
};

interface Props {
  enabled: boolean;
  status: CollabStatus;
  participants: CollabParticipant[];
  pending: boolean;
  onToggle: () => void;
}

/**
 * 协作状态栏（对齐 web 编辑器协作 chip）：开关 + 连接状态点 + 参与者头像 + 未同步指示。
 * 纯展示组件；会话生命周期由 EditorTabs 管理。
 */
export default function CollabMonaco({ enabled, status, participants, pending, onToggle }: Props) {
  const { t } = useTranslation();
  const dot = STATUS_COLOR[status];

  return (
    <span style={{ display: 'flex', alignItems: 'center', gap: 6, marginLeft: 12 }}>
      {enabled && pending && (
        <Tooltip title={t('desktop.collab.pending')}>
          <span style={{ width: 7, height: 7, borderRadius: '50%', background: yellow, boxShadow: `0 0 6px ${yellow}` }} />
        </Tooltip>
      )}
      {participants
        .filter((p) => p.username)
        .slice(0, 6)
        .map((p) => (
          <Tooltip key={p.clientID} title={p.username}>
            <span
              style={{
                width: 18, height: 18, borderRadius: '50%', display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                background: p.color, color: '#fff', fontSize: 9, fontWeight: 600, border: '1px solid #0d1117',
              }}
            >
              {p.username.slice(0, 2).toUpperCase()}
            </span>
          </Tooltip>
        ))}
      <button
        onClick={onToggle}
        title={t('desktop.collab.toggle')}
        style={{
          display: 'flex', alignItems: 'center', gap: 5, background: 'transparent', border: 'none',
          color: enabled ? '#e6edf3' : '#8b949e', fontSize: 11, cursor: 'pointer', padding: '2px 4px',
        }}
      >
        <span style={{ width: 7, height: 7, borderRadius: '50%', background: dot, boxShadow: status === 'connected' ? `0 0 6px ${dot}` : 'none' }} />
        {t('desktop.collab.label')}
      </button>
    </span>
  );
}
