import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Workspace } from '../api/workspaces';
import ExplorerPanel from '../views/workspace/ExplorerPanel';
import EditorTabs from '../views/workspace/EditorTabs';
import GitPanel from '../views/workspace/GitPanel';
import { useGatewayStore } from '../stores/gateway';

export default function IdeShell({ workspace }: { workspace: Workspace }) {
  const { t } = useTranslation();
  const baseURL = useGatewayStore((s) => s.config?.baseURL);
  const [view, setView] = useState<'explorer' | 'git'>('explorer');
  const [openPath, setOpenPath] = useState<string | null>(null);

  return (
    <div className="ide">
      <nav className="activity-bar">
        <button className={view === 'explorer' ? 'active' : ''} onClick={() => setView('explorer')}>📁</button>
        <button className={view === 'git' ? 'active' : ''} onClick={() => setView('git')}>⑂</button>
      </nav>
      <aside className="sidebar">
        {view === 'explorer' && <ExplorerPanel workspaceId={workspace.id} onOpen={setOpenPath} />}
        {view === 'git' && <GitPanel workspaceId={workspace.id} />}
      </aside>
      <main className="editor-area">
        <EditorTabs workspaceId={workspace.id} openPath={openPath} />
      </main>
      <footer className="status-bar">
        <span>{t('desktop.ide.gateway', { url: baseURL ?? '…' })}</span>
      </footer>
    </div>
  );
}
