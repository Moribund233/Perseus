import { create } from 'zustand';
import { repositoriesApi, type Repository, type RepoFile, type RepoBlob, type RepoBranch, type RepoCommit, type RepoMember, type PaginationResponse } from '../api/repositories';

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
  fetchPublicRepositories: () => Promise<void>;
  fetchRepositoriesByUser: (userId: string) => Promise<void>;
  fetchRepository: (repoId: string) => Promise<void>;
  fetchRepositoryByPath: (owner: string, repo: string) => Promise<void>;
  createRepository: (data: { name: string; description?: string; is_public?: boolean }) => Promise<Repository>;
  updateRepository: (repoId: string, data: Record<string, unknown>) => Promise<void>;
  deleteRepository: (repoId: string) => Promise<void>;
  archiveRepository: (repoId: string) => Promise<void>;
  unarchiveRepository: (repoId: string) => Promise<void>;
  fetchTree: (repoId: string, ref?: string, path?: string) => Promise<void>;
  fetchBlob: (repoId: string, path: string, ref?: string) => Promise<void>;
  fetchReadme: (repoId: string, ref?: string) => Promise<void>;
  fetchBranches: (repoId: string) => Promise<void>;
  fetchCommits: (repoId: string, params?: { page?: number; per_page?: number; branch?: string }) => Promise<void>;
  starRepository: (repoId: string) => Promise<void>;
  unstarRepository: (repoId: string) => Promise<void>;
  forkRepository: (repoId: string, data?: { name?: string; description?: string; is_public?: boolean }) => Promise<Repository>;
  fetchMembers: (repoId: string) => Promise<void>;
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
    set({ isLoading: true, error: null });
    try {
      const data = await repositoriesApi.list();
      const repositories = Array.isArray(data) ? data : (data as PaginationResponse<Repository>).items;
      set({ repositories, isLoading: false });
    } catch (e) {
      set({ error: (e as Error).message, isLoading: false });
    }
  },

  fetchPublicRepositories: async () => {
    set({ isLoading: true, error: null });
    try {
      const data = await repositoriesApi.listPublic();
      const repositories = Array.isArray(data) ? data : (data as PaginationResponse<Repository>).items;
      set({ repositories, isLoading: false });
    } catch (e) {
      set({ error: (e as Error).message, isLoading: false });
    }
  },

  fetchRepositoriesByUser: async (userId) => {
    set({ isLoading: true, error: null });
    try {
      const data = await repositoriesApi.listByUser(userId);
      const repositories = Array.isArray(data) ? data : (data as PaginationResponse<Repository>).items;
      set({ repositories, isLoading: false });
    } catch (e) {
      set({ error: (e as Error).message, isLoading: false });
    }
  },

  fetchRepository: async (repoId) => {
    set({ isLoading: true, error: null });
    try {
      const currentRepo = await repositoriesApi.get(repoId);
      set({ currentRepo, isLoading: false });
    } catch (e) {
      set({ error: (e as Error).message, isLoading: false });
    }
  },

  fetchRepositoryByPath: async (owner, repo) => {
    set({ isLoading: true, error: null });
    try {
      const currentRepo = await repositoriesApi.getByPath(owner, repo);
      set({ currentRepo, isLoading: false });
    } catch (e) {
      set({ error: (e as Error).message, isLoading: false });
    }
  },

  createRepository: async (data) => {
    const repo = await repositoriesApi.create(data);
    set((state) => ({ repositories: [repo, ...state.repositories] }));
    return repo;
  },

  updateRepository: async (repoId, data) => {
    const currentRepo = await repositoriesApi.update(repoId, data);
    set((state) => ({
      currentRepo,
      repositories: state.repositories.map((r) => (r.id === repoId ? currentRepo : r)),
    }));
  },

  deleteRepository: async (repoId) => {
    await repositoriesApi.delete(repoId);
    set((state) => ({
      repositories: state.repositories.filter((r) => r.id !== repoId),
      currentRepo: state.currentRepo?.id === repoId ? null : state.currentRepo,
    }));
  },

  archiveRepository: async (repoId) => {
    await repositoriesApi.archive(repoId);
    const { currentRepo } = get();
    if (currentRepo && currentRepo.id === repoId) {
      set({ currentRepo: { ...currentRepo, is_archived: true } });
    }
  },

  unarchiveRepository: async (repoId) => {
    await repositoriesApi.unarchive(repoId);
    const { currentRepo } = get();
    if (currentRepo && currentRepo.id === repoId) {
      set({ currentRepo: { ...currentRepo, is_archived: false } });
    }
  },

  fetchTree: async (repoId, ref, path) => {
    try {
      const entries = await repositoriesApi.getTree(repoId, ref, path);
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
    try {
      const currentBlob = await repositoriesApi.getBlob(repoId, path, ref);
      set({ currentBlob });
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },

  fetchReadme: async (repoId, ref) => {
    try {
      const result = await repositoriesApi.getReadme(repoId, ref);
      set({ readme: result.content });
    } catch {
      set({ readme: null });
    }
  },

  fetchBranches: async (repoId) => {
    try {
      const branches = await repositoriesApi.getBranches(repoId);
      set({ branches });
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },

  fetchCommits: async (repoId, params) => {
    try {
      const data = await repositoriesApi.getCommits(repoId, params);
      const result = data.commits;
      const commits = result.map((c) => ({
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
    await repositoriesApi.star(repoId);
    const { currentRepo } = get();
    if (currentRepo && currentRepo.id === repoId) {
      set({ currentRepo: { ...currentRepo, star_count: currentRepo.star_count + 1 } });
    }
  },

  unstarRepository: async (repoId) => {
    await repositoriesApi.unstar(repoId);
    const { currentRepo } = get();
    if (currentRepo && currentRepo.id === repoId) {
      set({ currentRepo: { ...currentRepo, star_count: Math.max(0, currentRepo.star_count - 1) } });
    }
  },

  forkRepository: async (repoId, data) => {
    const fork = await repositoriesApi.fork(repoId, data);
    set((state) => ({ repositories: [fork, ...state.repositories] }));
    return fork;
  },

  fetchMembers: async (repoId) => {
    try {
      const members = await repositoriesApi.getMembers(repoId);
      set({ members });
    } catch (e) {
      set({ error: (e as Error).message });
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
