import { useCallback, useEffect, useState } from 'react';
import { App as AntApp, Empty, Input, Modal, Tag } from 'antd';
import {
  DeleteOutlined,
  MessageOutlined,
  RightOutlined,
  SendOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { Workspace } from '../../api/workspaces';
import { discussionsApi, type DiscussionComment } from '../../api/discussions';
import { useIdentityStore } from '../../stores/identity';
import { useWorkspaceRepo } from '../../hooks/useWorkspaceRepo';

const textPrimary = '#e6edf3';
const textSecondary = '#8b949e';
const textTertiary = '#6e7681';
const blueLight = '#58a6ff';
const borderColor = '#21262d';

function formatTime(dateStr: string | null): string {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

export default function DiscussionsPanel({ workspace, filePath, cursorLine, onGoLine }: {
  workspace: Workspace;
  filePath: string | null;
  cursorLine?: number | null;
  onGoLine?: (path: string, line: number) => void;
}) {
  const { t } = useTranslation();
  const { message, modal } = AntApp.useApp();
  const me = useIdentityStore((s) => s.me);
  const { serverId, repoId, defaultBranch } = useWorkspaceRepo(workspace);

  const [comments, setComments] = useState<DiscussionComment[]>([]);
  const [loading, setLoading] = useState(false);
  const [newText, setNewText] = useState('');
  const [replyText, setReplyText] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  const branch = workspace.branch || defaultBranch || 'main';

  const reload = useCallback(async () => {
    if (!serverId || !repoId || !filePath) {
      setComments([]);
      return;
    }
    setLoading(true);
    try {
      const items = await discussionsApi.list(serverId, repoId, {
        file_path: filePath,
        include_resolved: true,
      });
      setComments(items ?? []);
    } catch (e) {
      message.error(`${t('desktop.discussions.loadFailed')}: ${(e as Error).message}`);
    } finally {
      setLoading(false);
    }
  }, [serverId, repoId, filePath, message, t]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const roots = comments.filter((c) => !c.parent_id);
  const repliesByRoot = useCallback((rootId: string) => comments.filter((c) => c.parent_id === rootId), [comments]);

  const submitCreate = async () => {
    const text = newText.trim();
    if (!text || !serverId || !repoId || !filePath) return;
    setBusy(true);
    try {
      await discussionsApi.create(serverId, repoId, {
        content: text,
        file_path: filePath,
        line_number: cursorLine && cursorLine > 0 ? cursorLine : null,
        branch,
      });
      setNewText('');
      await reload();
      message.success(t('desktop.discussions.created'));
    } catch (e) {
      message.error(`${t('desktop.discussions.failed')}: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  };

  const submitReply = async (rootId: string) => {
    const text = (replyText[rootId] ?? '').trim();
    if (!text || !serverId || !repoId || !filePath) return;
    setBusy(true);
    try {
      await discussionsApi.create(serverId, repoId, {
        content: text,
        file_path: filePath,
        line_number: null,
        branch,
        parent_id: rootId,
      });
      setReplyText((prev) => ({ ...prev, [rootId]: '' }));
      await reload();
    } catch (e) {
      message.error(`${t('desktop.discussions.failed')}: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  };

  const toggleResolve = async (c: DiscussionComment) => {
    if (!serverId || !repoId) return;
    try {
      await discussionsApi.resolve(serverId, repoId, c.id, !c.resolved);
      await reload();
    } catch (e) {
      message.error(`${t('desktop.discussions.failed')}: ${(e as Error).message}`);
    }
  };

  const removeComment = async (c: DiscussionComment) => {
    if (!serverId || !repoId) return;
    modal.confirm({
      title: t('desktop.discussions.deleteTitle'),
      okText: t('desktop.discussions.delete'),
      cancelText: t('desktop.discussions.cancel'),
      onOk: async () => {
        await discussionsApi.remove(serverId, repoId, c.id);
        await reload();
      },
      onCancel: () => undefined,
    });
  };

  const location = (c: DiscussionComment) => (
    <span
      style={{ color: blueLight, fontSize: 11, cursor: onGoLine && c.line_number ? 'pointer' : 'default' }}
      onClick={() => { if (onGoLine && c.line_number) onGoLine(c.file_path, c.line_number); }}
    >
      {c.file_path}{c.line_number ? `:${c.line_number}` : ''}
    </span>
  );

  const authorText = (c: DiscussionComment) => (
    <span style={{ color: textTertiary, fontSize: 11 }}>
      {c.author_username} · {formatTime(c.created_at)} · {location(c)}
    </span>
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: '#161b22' }}>
      <div style={{ padding: '10px 12px', borderBottom: `1px solid ${borderColor}`, display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
        <MessageOutlined style={{ color: blueLight }} />
        <b style={{ fontSize: 13, color: textPrimary }}>{t('desktop.discussions.title')}</b>
        {filePath && <span style={{ fontSize: 11, color: textTertiary, marginLeft: 'auto' }} title={filePath}>{filePath.split(/[\\/]/).pop()}</span>}
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: 12 }}>
        {!repoId && (
          <div style={{ padding: '14px 4px', fontSize: 12, color: textTertiary, textAlign: 'center' }}>
            {t('desktop.discussions.noRepo')}
          </div>
        )}
        {repoId && !filePath && (
          <div style={{ padding: '14px 4px', fontSize: 12, color: textTertiary, textAlign: 'center' }}>
            {t('desktop.discussions.selectFile')}
          </div>
        )}
        {repoId && filePath && loading && comments.length === 0 && (
          <div style={{ padding: '14px 4px', fontSize: 12, color: textTertiary, textAlign: 'center' }}>…</div>
        )}
        {repoId && filePath && !loading && comments.length === 0 && (
          <Empty description={t('desktop.discussions.empty')} style={{ marginTop: 24 }} />
        )}

        {roots.map((root) => {
          const replies = repliesByRoot(root.id);
          return (
            <div key={root.id} style={{
              border: `1px solid ${borderColor}`, borderRadius: 8, marginBottom: 10, background: 'var(--bg, #0d1117)', overflow: 'hidden',
            }}>
              <div style={{ padding: '8px 10px', display: 'flex', alignItems: 'center', gap: 8 }}>
                {root.resolved && <Tag style={{ fontSize: 10, margin: 0 }}>{t('desktop.discussions.resolved')}</Tag>}
                {root.line_number != null && (
                  <button
                    className="icon-btn sm"
                    title={t('desktop.discussions.goLine')}
                    onClick={() => onGoLine?.(root.file_path, root.line_number!)}
                  >
                    <RightOutlined style={{ fontSize: 10 }} />
                  </button>
                )}
                <span style={{ flex: 1, fontSize: 12, color: textSecondary, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                  {root.content}
                </span>
                <button
                  className="icon-btn sm"
                  title={root.resolved ? t('desktop.discussions.reopen') : t('desktop.discussions.resolve')}
                  onClick={() => void toggleResolve(root)}
                >
                  {root.resolved ? '↻' : '✓'}
                </button>
                {me && root.author_id === me.id && (
                  <button
                    className="icon-btn sm"
                    title={t('desktop.discussions.delete')}
                    onClick={() => void removeComment(root)}
                  >
                    <DeleteOutlined style={{ fontSize: 11 }} />
                  </button>
                )}
              </div>
              <div style={{ padding: '0 10px 6px' }}>{authorText(root)}</div>

              {replies.length > 0 && (
                <div style={{ borderTop: `1px solid ${borderColor}`, padding: '6px 0' }}>
                  {replies.map((r) => (
                    <div key={r.id} style={{ padding: '4px 10px' }}>
                      <div style={{ fontSize: 12, color: textSecondary, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{r.content}</div>
                      <div style={{ marginTop: 2, display: 'flex', alignItems: 'center', gap: 8 }}>
                        {authorText(r)}
                        {me && r.author_id === me.id && (
                          <button className="icon-btn sm" title={t('desktop.discussions.delete')} onClick={() => void removeComment(r)}>
                            <DeleteOutlined style={{ fontSize: 10 }} />
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <div style={{ borderTop: `1px solid ${borderColor}`, padding: 8, display: 'flex', gap: 6 }}>
                <Input.TextArea
                  autoSize={{ minRows: 1, maxRows: 3 }}
                  style={{ fontSize: 12 }}
                  placeholder={t('desktop.discussions.replyPlaceholder')}
                  value={replyText[root.id] ?? ''}
                  onChange={(e) => setReplyText((prev) => ({ ...prev, [root.id]: e.target.value }))}
                />
                <button
                  className="btn primary sm"
                  style={{ alignSelf: 'flex-end' }}
                  disabled={!(replyText[root.id] ?? '').trim() || busy}
                  onClick={() => void submitReply(root.id)}
                >
                  <SendOutlined />
                </button>
              </div>
            </div>
          );
        })}

        {repoId && filePath && (
          <div style={{ padding: 8, border: `1px solid ${borderColor}`, borderRadius: 8, display: 'flex', gap: 6, background: 'var(--bg, #0d1117)' }}>
            <Input.TextArea
              autoSize={{ minRows: 2, maxRows: 5 }}
              style={{ fontSize: 12 }}
              placeholder={cursorLine ? `${t('desktop.discussions.createPlaceholder')} (L${cursorLine})` : t('desktop.discussions.createPlaceholder')}
              value={newText}
              onChange={(e) => setNewText(e.target.value)}
            />
            <button
              className="btn primary sm"
              style={{ alignSelf: 'flex-end' }}
              disabled={!newText.trim() || busy}
              onClick={() => void submitCreate()}
            >
              {t('desktop.discussions.post')}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}