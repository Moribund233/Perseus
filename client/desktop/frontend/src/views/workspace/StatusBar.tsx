import { useTranslation } from 'react-i18next';
import {
  BranchesOutlined,
  BugOutlined,
  PushpinOutlined,
  DatabaseOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import type { Workspace, GitStatus } from '../../api/workspaces';
import { useGitStore } from '../../stores/git';
import { useProblemsStore } from '../../stores/problems';
import { useLspStore } from '../../stores/lsp';
import { useServersStore } from '../../stores/servers';
import { useEditorStatusStore } from '../../stores/editorStatus';

export type BottomTab = 'problems' | 'output' | 'terminal';

interface Props {
  workspace: Workspace;
  file: string | null;
  lang: string | null;
  cursor?: { line: number; column: number } | null;
  onOpenBottom?: (tab: BottomTab) => void;
}

// StatusBar：分支 / 问题数 / 语言服务 / 服务器 / 当前文件。数据全部来自真实 store。
export default function StatusBar({ workspace, file, lang, cursor, onOpenBottom }: Props) {
  const { t } = useTranslation();
  const status: GitStatus | null = useGitStore((s) => s.status);
  const problems = useProblemsStore((s) => s.diagnostics.length);
  const lsp = useLspStore();
  const servers = useServersStore((s) => s.servers);
  const currentServerId = useServersStore((s) => s.currentServerId);
  const { collabActive, collabSynced, lastSavedCommit, collabVersion } = useEditorStatusStore();

  const server = servers.find((s) => s.id === (currentServerId ?? workspace.server_id));
  const serverName = server?.name ?? (workspace.server_id ? String(workspace.server_id) : 'local');

  const lspText =
    lsp.status === 'idle'
      ? t('desktop.status.lspIdle', { defaultValue: '语言服务' })
      : lsp.status === 'connecting'
        ? t('desktop.status.lspConnecting', { defaultValue: '语言服务: 连接中' })
        : lsp.status === 'disconnected'
          ? t('desktop.status.lspOff', { defaultValue: '语言服务: 离线' })
          : t('desktop.status.lspOn', { lang: lsp.lang ?? '', defaultValue: '语言服务: {{lang}}' });

  const fileLabel = file ? file.split(/[\\/]/).pop() ?? file : t('desktop.status.noFile', { defaultValue: '无文件' });

  return (
    <footer className="statusbar">
      <span className="sb-item" title={t('desktop.status.branchTitle', { defaultValue: '当前分支' })}>
        <BranchesOutlined />
        {status?.branch ?? 'HEAD'}
        {!!status && status.ahead + status.behind > 0 && (
          <span style={{ fontFamily: 'var(--mono)', fontSize: 10.5, opacity: 0.85 }}>
            ↑{status.ahead} ↓{status.behind}
          </span>
        )}
      </span>
      <span
        className="sb-item clickable"
        title={t('desktop.status.problemsTitle', { defaultValue: '问题面板' })}
        onClick={() => onOpenBottom?.('problems')}
      >
        <BugOutlined />
        {t('desktop.status.problems', { count: problems, defaultValue: '问题: {{count}}' })}
      </span>
      <span className="sb-item" title={t('desktop.status.lspTitle', { defaultValue: '语言服务器状态' })}>
        <span className={`sb-dot ${lsp.status === 'connected' ? 'on' : 'off'}`} />
        {lspText}
      </span>
      {collabActive && (
        <span
          className="sb-item"
          title={t('desktop.status.collabTitle', { defaultValue: '协作会话状态' })}
        >
          <span className={`sb-dot ${collabSynced ? 'on' : 'off'}`} />
          {collabSynced
            ? t('desktop.status.collabSynced', { defaultValue: '会话已同步' })
            : t('desktop.status.collabSyncing', { defaultValue: '会话同步中' })}
          {collabVersion != null && <span style={{ fontFamily: 'var(--mono)', fontSize: 10.5 }}>{`v${collabVersion}`}</span>}
        </span>
      )}
      {lastSavedCommit && (
        <span
          className="sb-item"
          title={t('desktop.status.gitCommittedTitle', { defaultValue: '最近一次协作保存的 Git 提交' })}
          style={{ fontFamily: 'var(--mono)', fontSize: 10.5 }}
        >
          {t('desktop.status.gitCommitted', { sha: lastSavedCommit, defaultValue: 'Git 已提交 {{sha}}' })}
        </span>
      )}
      <span className="sb-item" title={t('desktop.status.serverTitle', { defaultValue: '关联服务器' })}>
        <DatabaseOutlined />
        {serverName}
      </span>
      <span className="sp" />
      <span className="sb-item" title={(file ?? '')}>
        <FileTextOutlined />
        {fileLabel}
        {lang ? ` — ${lang}` : ''}
      </span>
      {cursor && (
        <span className="sb-item" style={{ fontFamily: 'var(--mono)', fontSize: 11 }}>
          Ln {cursor.line}, Col {cursor.column}
        </span>
      )}
      <span className="sb-item clickable" title={t('desktop.status.repoTitle', { defaultValue: '仓库' })}>
        <PushpinOutlined />
        {workspace.name}
      </span>
    </footer>
  );
}