import { Select } from 'antd';
import { useTranslation } from 'react-i18next';
import { useChatStore } from '../../stores/chat';
import type { Workspace } from '../../api/workspaces';
import { useWorkspaceChatRoom } from '../../hooks/useWorkspaceChatRoom';
import ChatMessages from './ChatMessages';
import ChatComposer from './ChatComposer';

const borderColor = '#21262d';
const textTertiary = '#6e7681';
const green = '#3fb950';

// IDE 活动栏聊天精简面板：与门户 ChatView 共用同一 store/socket（socket 常驻）。
export default function ActivityChatPanel({ workspace }: { workspace: Workspace }) {
  const { t } = useTranslation();
  const { rooms, activeRoomId, activeRoom, status } = useWorkspaceChatRoom(workspace);
  const setActiveRoom = useChatStore((s) => s.setActiveRoom);

  const roomOptions = rooms.map((r) => ({ value: r.id, label: `# ${r.name}` }));

  const onSelectRoom = (roomId: string) => {
    setActiveRoom(roomId);
    void useChatStore.getState().fetchMessages(roomId);
    void useChatStore.getState().fetchMembers(roomId);
  };

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
