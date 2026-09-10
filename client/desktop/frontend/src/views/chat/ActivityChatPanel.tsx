import { useEffect, useMemo, useState } from 'react';
import { Select } from 'antd';
import { useTranslation } from 'react-i18next';
import { useChatStore } from '../../stores/chat';
import type { Workspace } from '../../api/workspaces';
import ChatMessages from './ChatMessages';
import ChatComposer from './ChatComposer';

const borderColor = '#21262d';
const textTertiary = '#6e7681';
const green = '#3fb950';

// IDE 活动栏聊天精简面板：与门户 ChatView 共用同一 store/socket（socket 常驻）。
export default function ActivityChatPanel({ workspace }: { workspace: Workspace }) {
  const { t } = useTranslation();
  const rooms = useChatStore((s) => s.rooms);
  const activeRoomId = useChatStore((s) => s.activeRoomId);
  const status = useChatStore((s) => s.status);
  const setActiveRoom = useChatStore((s) => s.setActiveRoom);
  const start = useChatStore((s) => s.start);

  useEffect(() => {
    start();
  }, [start]);

  useEffect(() => {
    void useChatStore.getState().fetchChatRooms();
  }, [workspace.server_id]);

  // 优先匹配工作区来源仓库的房间（clone 工作区 remote_url = <base>/<owner>/<repo>.git）。
  const preferredRoomId = useMemo(() => {
    if (rooms.length === 0) return null;
    const repoName = workspace.remote_url ? (workspace.remote_url.split('/').pop() ?? '').replace(/\.git$/, '') : '';
    if (repoName) {
      const hit = rooms.find((r) => r.name === repoName);
      if (hit) return hit.id;
    }
    return null;
  }, [rooms, workspace.remote_url]);

  useEffect(() => {
    if (preferredRoomId && preferredRoomId !== activeRoomId) {
      setActiveRoom(preferredRoomId);
      void useChatStore.getState().fetchMessages(preferredRoomId);
      void useChatStore.getState().fetchMembers(preferredRoomId);
    }
  }, [preferredRoomId, activeRoomId, setActiveRoom]);

  const roomOptions = rooms.map((r) => ({ value: r.id, label: `# ${r.name}` }));

  const onSelectRoom = (roomId: string) => {
    setActiveRoom(roomId);
    void useChatStore.getState().fetchMessages(roomId);
    void useChatStore.getState().fetchMembers(roomId);
  };

  const activeRoom = rooms.find((r) => r.id === activeRoomId) ?? null;

  return (
    <div className="sb-pane on" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="sb-head" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span>{t('desktop.menu.chat')}</span>
        <span
          title={t(`desktop.chat.status.${status}`)}
          style={{ width: 7, height: 7, borderRadius: '50%', background: status === 'connected' ? green : '#6e7681', flexShrink: 0 }}
        />
      </div>

      <div style={{ padding: '8px 10px', borderBottom: `1px solid ${borderColor}` }}>
        <Select
          size="small"
          style={{ width: '100%' }}
          placeholder={t('desktop.chat.selectChannel')}
          value={activeRoomId ?? undefined}
          options={roomOptions}
          onChange={onSelectRoom}
          notFoundContent={<span style={{ color: textTertiary, fontSize: 12 }}>{t('desktop.chat.noChannels')}</span>}
        />
      </div>

      {activeRoom ? (
        <>
          <ChatMessages roomId={activeRoom.id} compact />
          <ChatComposer roomId={activeRoom.id} roomName={activeRoom.name} compact />
        </>
      ) : (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: textTertiary, fontSize: 12, padding: 16, textAlign: 'center' }}>
          {rooms.length === 0 ? t('desktop.chat.noChannelsHint') : t('desktop.chat.selectChannel')}
        </div>
      )}
    </div>
  );
}
