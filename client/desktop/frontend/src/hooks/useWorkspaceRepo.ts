import { useEffect, useState } from 'react';
import type { Workspace } from '../api/workspaces';
import { repositoriesApi } from '../api/repositories';
import { useServersStore } from '../stores/servers';

export interface WorkspaceRepo {
  serverId: string | null;
  owner: string;
  repo: string;
  repoId: string | null;
  defaultBranch: string | null;
  loading: boolean;
}

// parseRemote 从 remote_url 解析 owner/repo 段（支持 https/ssh://git@xxx:owner/repo.git 形式）。
export function parseRemote(url: string | undefined): { owner: string; repo: string } | null {
  if (!url) return null;
  const m = url.replace(/\.git$/, '').match(/[/:]([^/:]+)\/([^/.]+)\s*$/);
  if (!m) return null;
  return { owner: m[1], repo: m[2] };
}

// useWorkspaceRepo 解析当前工作区对应的服务端仓库 id（无服务器或非远端克隆时静默降级）。
export function useWorkspaceRepo(workspace: Workspace): WorkspaceRepo {
  const serverId = useServersStore((s) => s.currentServerId) ?? workspace.server_id ?? null;
  const parts = parseRemote(workspace.remote_url);
  const owner = parts?.owner ?? '';
  const repo = parts?.repo ?? '';
  const [repoId, setRepoId] = useState<string | null>(null);
  const [defaultBranch, setDefaultBranch] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let alive = true;
    setRepoId(null);
    setDefaultBranch(null);
    if (!serverId || !owner || !repo) return;
    setLoading(true);
    repositoriesApi
      .getByPath(serverId, owner, repo)
      .then((r) => {
        if (alive) {
          setRepoId(r.id);
          setDefaultBranch(r.default_branch ?? null);
        }
      })
      .catch(() => {
        if (alive) setRepoId(null);
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [serverId, owner, repo]);

  return { serverId, owner, repo, repoId, defaultBranch, loading };
}