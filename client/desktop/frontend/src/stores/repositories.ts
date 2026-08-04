import { create } from 'zustand';
import {
  repositoriesApi,
  type Repository,
  type RepoFile,
  type RepoBlob,
  type RepoBranch,
  type RepoCommit,
  type RepoMember,
  type PaginationResponse,
} from '../api/repositories';
import { useServersStore } from './servers';

// 当前连接的服务器 id；单服务器同时工作，取自 servers store。
function serverId(): string | null {
  return useServersStore.getState().currentServerId;
}

interface RepositoriesState {
  repositories: Repository[];
  currentRepo: Repository | null;
  files: RepoFile[];
  currentBlob: RepoBlob | null;
  readme: string | null;
  branches: RepoBranch[];
  commits: RepoCommit[];
  members: RepoMember[];
  isLoading: boolean;
  error: string | null;

  fetchRepositories: () => Promise<void>;
  fetchRepositoriesByUser: (userId: string) => Promise<void>;
  fetchRepository: (repoId: string) => Promise<void>;
  fetchRepositoryByPath: (owner: string, repo: string) => Promise<void>;
  createRepository: (data: { name: string; description?: string; is_public?: boolean }) => Promise<Repository>;
  deleteRepository: (repoId: string) => Promise<void>;
  archiveRepository: (repoId: string) => Promise<void>;
  unarchiveRepository: (repoId: string) => Promise<void>;
  fetchTree: (repoId: string, ref?: string, path?: string) => Promise<void>;
  fetchBlob: (repoId: string, path: string, ref?: string) => Promise<RepoBlob | null>;
  fetchReadme: (repoId: string, ref?: string) => Promise<void>;
  fetchBranches: (repoId: string) => Promise<void>;
  fetchCommits: (repoId: string, params?: { page?: number; per_page?: number; branch?: string }) => Promise<void>;
  starRepository: (repoId: string) => Promise<void>;
  unstarRepository: (repoId: string) => Promise<void>;
  clearCurrent: () => void;
}

export const useRepositoriesStore = create<RepositoriesState>((set, get) => ({
  repositories: [],
  currentRepo: null,
  files: [],
  currentBlob: null,
  readme: null,
  branches: [],
  commits: [],
  members: [],
  isLoading: false,
  error: null,

  fetchRepositories: async () => {
    const sid = serverId();
    if (!sid) return;
    set({ isLoading: true, error: null });
    try {
      const data = await repositoriesApi.list(sid);
      const repositories = Array.isArray(data) ? data : (data as PaginationResponse<Repository>).items;
      set({ repositories, isLoading: false });
    } catch (e) {
      set({ error: (e as Error).message, isLoading: false });
    }
  },

  fetchRepositoriesByUser: async (userId) => {
    const sid = serverId();
    if (!sid) return;
    set({ isLoading: true, error: null });
    try {
      const data = await repositoriesApi.listByUser(sid, userId);
      const repositories = Array.isArray(data) ? data : (data as PaginationResponse<Repository>).items;
      set({ repositories, isLoading: false });
    } catch (e) {
      set({ error: (e as Error).message, isLoading: false });
    }
  },

  fetchRepository: async (repoId) => {
    const sid = serverId();
    if (!sid) return;
    set({ isLoading: true, error: null });
    try {
      const currentRepo = await repositoriesApi.get(sid, repoId);
      set({ currentRepo, isLoading: false });
    } catch (e) {
      set({ error: (e as Error).message, isLoading: false });
    }
  },

  fetchRepositoryByPath: async (owner, repo) => {
    const sid = serverId();
    if (!sid) return;
    set({ isLoading: true, error: null });
    try {
      const currentRepo = await repositoriesApi.getByPath(sid, owner, repo);
      set({ currentRepo, isLoading: false });
    } catch (e) {
      set({ error: (e as Error).message, isLoading: false });
    }
  },

  createRepository: async (data) => {
    const sid = serverId();
    if (!sid) throw new Error('no server');
    const repo = await repositoriesApi.create(sid, data);
    set((state) => ({ repositories: [repo, ...state.repositories] }));
    return repo;
  },

  deleteRepository: async (repoId) => {
    const sid = serverId();
    if (!sid) return;
    await repositoriesApi.delete(sid, repoId);
    set((state) => ({
      repositories: state.repositories.filter((r) => r.id !== repoId),
      currentRepo: state.currentRepo?.id === repoId ? null : state.currentRepo,
    }));
  },

  archiveRepository: async (repoId) => {
    const sid = serverId();
    if (!sid) return;
    await repositoriesApi.archive(sid, repoId);
    const { currentRepo } = get();
    if (currentRepo && currentRepo.id === repoId) {
      set({ currentRepo: { ...currentRepo, is_archived: true } });
    }
  },

  unarchiveRepository: async (repoId) => {
    const sid = serverId();
    if (!sid) return;
    await repositoriesApi.unarchive(sid, repoId);
    const { currentRepo } = get();
    if (currentRepo && currentRepo.id === repoId) {
      set({ currentRepo: { ...currentRepo, is_archived: false } });
    }
  },

  fetchTree: async (repoId, ref, path) => {
    const sid = serverId();
    if (!sid) return;
    try {
      const entries = await repositoriesApi.getTree(sid, repoId, ref, path);
      if (path) {
        set((state) => {
          const merged = new Map(state.files.map((f) => [f.path, f]));
          for (const e of entries) merged.set(e.path, e);
          return { files: Array.from(merged.values()) };
        });
      } else {
        set({ files: entries });
      }
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },

  fetchBlob: async (repoId, path, ref) => {
    const sid = serverId();
    if (!sid) return null;
    try {
      const currentBlob = await repositoriesApi.getBlob(sid, repoId, path, ref || undefined);
      set({ currentBlob });
      return currentBlob;
    } catch {
      set({ currentBlob: null });
      return null;
    }
  },

  fetchReadme: async (repoId, ref) => {
    const sid = serverId();
    if (!sid) return;
    try {
      const result = await repositoriesApi.getReadme(sid, repoId, ref);
      set({ readme: result.content });
    } catch {
      set({ readme: null });
    }
  },

  fetchBranches: async (repoId) => {
    const sid = serverId();
    if (!sid) return;
    try {
      const branches = await repositoriesApi.getBranches(sid, repoId);
      set({ branches });
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },

  fetchCommits: async (repoId, params) => {
    const sid = serverId();
    if (!sid) return;
    try {
      const data = await repositoriesApi.getCommits(sid, repoId, params);
      const commits = data.commits.map((c) => ({
        id: c.sha,
        hash: c.sha,
        message: c.message,
        author_name: c.author.name,
        author_email: c.author.email,
        author_date: c.author.date,
      }));
      set({ commits });
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },

  starRepository: async (repoId) => {
    const sid = serverId();
    if (!sid) return;
    await repositoriesApi.star(sid, repoId);
    const { currentRepo } = get();
    if (currentRepo && currentRepo.id === repoId) {
      set({ currentRepo: { ...currentRepo, star_count: currentRepo.star_count + 1 } });
    }
  },

  unstarRepository: async (repoId) => {
    const sid = serverId();
    if (!sid) return;
    await repositoriesApi.unstar(sid, repoId);
    const { currentRepo } = get();
    if (currentRepo && currentRepo.id === repoId) {
      set({ currentRepo: { ...currentRepo, star_count: Math.max(0, currentRepo.star_count - 1) } });
    }
  },

  clearCurrent: () => {
    set({
      currentRepo: null,
      files: [],
      currentBlob: null,
      readme: null,
      branches: [],
      commits: [],
      members: [],
    });
  },
}));