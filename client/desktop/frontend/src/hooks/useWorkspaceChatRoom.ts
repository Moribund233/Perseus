import { useEffect, useMemo } from 'react';
import { useChatStore } from '../stores/chat';
import type { Workspace } from '../api/workspaces';

// 将工作区关联到其来源仓库的聊天房间：
// clone 工作区 remote_url = <base>/<owner>/<repo>.git，房间名 = 仓库名。
// 返回当前活跃房间与成员/在线信息（store 共享，门户聊天页与 IDE 面板同源）。
export function useWorkspaceChatRoom(workspace: Workspace) {
  const rooms = useChatStore((s) => s.rooms);
  const activeRoomId = useChatStore((s) => s.activeRoomId);
  const members = useChatStore((s) => s.members);
  const onlineUsers = useChatStore((s) => s.onlineUsers);
  const status = useChatStore((s) => s.status);
  const start = useChatStore((s) => s.start);
  const setActiveRoom = useChatStore((s) => s.setActiveRoom);

  useEffect(() => {
    start();
  }, [start]);

  useEffect(() => {
    void useChatStore.getState().fetchChatRooms();
  }, [workspace.server_id]);

  const preferredRoomId = useMemo(() => {
    if (rooms.length === 0) return null;
    const repoName = workspace.remote_url
      ? (workspace.remote_url.split('/').pop() ?? '').replace(/\.git$/, '')
      : '';
    if (repoName) {
      const hit = rooms.find((r) => r.name === repoName);
      if (hit) return hit.id;
    }
    return null;
  }, [rooms, workspace.remote_url]);

  useEffect(() => {
    if (!preferredRoomId || preferredRoomId === activeRoomId) return;
    setActiveRoom(preferredRoomId);
    void useChatStore.getState().fetchMessages(preferredRoomId);
    void useChatStore.getState().fetchMembers(preferredRoomId);
  }, [preferredRoomId, activeRoomId, setActiveRoom]);

  const roomMembers = activeRoomId ? members[activeRoomId] ?? [] : [];
  const onlineIds = useMemo(
    () => new Set((activeRoomId ? onlineUsers[activeRoomId] ?? [] : []).map((u) => u.user_id)),
    [onlineUsers, activeRoomId],
  );

  return {
    rooms,
    activeRoomId,
    activeRoom: rooms.find((r) => r.id === activeRoomId) ?? null,
    roomMembers,
    onlineIds,
    status,
  };
}
