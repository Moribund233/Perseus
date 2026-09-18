import { Popover, Tooltip } from 'antd';
import { AimOutlined, StopOutlined, UsergroupAddOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { CollabParticipant, CollabStatus, FollowState } from '../../api/collabSocket';

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
  followState: FollowState;
  onToggle: () => void;
  onFollow: (clientID: string | null) => void;
  onSpotlight: (on: boolean) => void;
}

/**
 * 协作状态栏（对齐 web 编辑器协作 chip）：开关 + 连接状态点 + 参与者头像 + 未同步指示
 * + 跟随模式（Follow me）：参与者跟随列表、跟随中指示、"跟我来"开关。
 * 纯展示/交互组件；会话生命周期由 EditorTabs 管理。
 */
export default function CollabMonaco({ enabled, status, participants, pending, followState, onToggle, onFollow, onSpotlight }: Props) {
  const { t } = useTranslation();
  const dot = STATUS_COLOR[status];
  const connected = enabled && status === 'connected';
  const myFollowing = followState.following;

  const followMenu = (
    <div style={{ width: 220, maxHeight: 260, overflowY: 'auto', display: 'grid', gap: 4 }}>
      <div style={{ fontSize: 11, opacity: 0.7, padding: '2px 4px' }}>{t('desktop.collab.followMenu')}</div>
      {participants.length === 0 && (
        <div style={{ fontSize: 11, opacity: 0.6, padding: '4px' }}>{t('desktop.collab.noParticipants')}</div>
      )}
      {participants.map((p) => (
        <div key={p.clientID} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '3px 4px' }}>
          <span
            style={{
              width: 16, height: 16, borderRadius: '50%', background: p.color, color: '#fff', fontSize: 8,
              lineHeight: '16px', textAlign: 'center', flex: 'none',
            }}
          >
            {p.username.slice(0, 1).toUpperCase()}
          </span>
          <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 12 }}>
            {p.username || String(p.clientID).slice(0, 6)}
          </span>
          {p.isSelf ? (
            <span style={{ fontSize: 11, opacity: 0.7 }}>
              {followState.followerCount > 0 ? t('desktop.collab.followerCount', { count: followState.followerCount }) : ''}
            </span>
          ) : (
            <button
              onClick={() => onFollow(myFollowing === p.clientID ? null : p.clientID)}
              style={{
                display: 'flex', alignItems: 'center', gap: 4, background: 'transparent', border: 'none',
                color: myFollowing === p.clientID ? '#f85149' : '#58a6ff', fontSize: 11, cursor: 'pointer', padding: '2px 4px',
              }}
            >
              {myFollowing === p.clientID ? <StopOutlined style={{ fontSize: 10 }} /> : <AimOutlined style={{ fontSize: 10 }} />}
              {myFollowing === p.clientID ? t('desktop.collab.followStop') : t('desktop.collab.follow')}
            </button>
          )}
        </div>
      ))}
    </div>
  );

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
          <Tooltip key={p.clientID} title={`${p.username}${p.clientID === myFollowing ? ` · ${t('desktop.collab.following', { name: followState.followingName ?? '' })}` : ''}`}>
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
      {connected && followState.following && (
        <Tooltip title={t('desktop.collab.following', { name: followState.followingName ?? '…' })}>
          <button
            onClick={() => onFollow(null)}
            title={t('desktop.collab.followStop')}
            style={{
              display: 'flex', alignItems: 'center', gap: 4, background: 'transparent', border: 'none',
              color: '#58a6ff', fontSize: 11, cursor: 'pointer', padding: '2px 4px',
            }}
          >
            <AimOutlined style={{ fontSize: 11 }} />
            <span style={{ maxWidth: 90, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {followState.followingName ?? '…'}
            </span>
            <StopOutlined style={{ fontSize: 9 }} />
          </button>
        </Tooltip>
      )}
      {connected && (
        <Tooltip title={followState.spotlightOn ? t('desktop.collab.spotlightStop') : t('desktop.collab.spotlightStart')}>
          <button
            onClick={() => onSpotlight(!followState.spotlightOn)}
            style={{
              display: 'flex', alignItems: 'center', background: 'transparent', border: 'none',
              color: followState.spotlightOn ? green : '#8b949e', fontSize: 12, cursor: 'pointer', padding: '2px 4px',
            }}
          >
            <AimOutlined />
          </button>
        </Tooltip>
      )}
      {connected && (
        <Popover content={followMenu} trigger="click" overlayInnerStyle={{ background: '#161b22', border: '1px solid #30363d' }}>
          <button
            title={t('desktop.collab.followMenu')}
            style={{
              display: 'flex', alignItems: 'center', background: 'transparent', border: 'none',
              color: '#8b949e', fontSize: 12, cursor: 'pointer', padding: '2px 4px',
            }}
          >
            <UsergroupAddOutlined />
          </button>
        </Popover>
      )}
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