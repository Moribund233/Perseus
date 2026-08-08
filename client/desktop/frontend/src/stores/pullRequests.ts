import { create } from 'zustand';
import {
  pullRequestsApi,
  type PR,
  type PRComment,
  type CreatePRCommentRequest,
  type CreatePRReviewRequest,
  type PaginationResponse,
} from '../api/pullRequests';
import { useServersStore } from './servers';

// 当前连接的服务器 id；单服务器同时工作，取自 servers store。
function serverId(): string | null {
  return useServersStore.getState().currentServerId;
}

interface PullRequestsState {
  pullRequests: PR[];
  currentPR: PR | null;
  comments: PRComment[];
  isLoading: boolean;
  error: string | null;

  fetchPullRequests: (repoId: string, status?: string) => Promise<void>;
  fetchPullRequest: (repoId: string, prNumber: number) => Promise<void>;
  createPullRequest: (repoId: string, data: { title: string; description?: string; source_branch: string; target_branch: string }) => Promise<PR>;
  updatePullRequest: (repoId: string, prNumber: number, data: { title?: string; description?: string }) => Promise<void>;
  closePullRequest: (repoId: string, prNumber: number) => Promise<void>;
  mergePullRequest: (repoId: string, prNumber: number, mergeMethod?: 'merge' | 'squash' | 'rebase') => Promise<void>;
  fetchComments: (repoId: string, prNumber: number) => Promise<void>;
  createComment: (repoId: string, prNumber: number, data: CreatePRCommentRequest) => Promise<PRComment>;
  createReview: (repoId: string, prNumber: number, data: CreatePRReviewRequest) => Promise<void>;
  clearCurrent: () => void;
}

export const usePullRequestsStore = create<PullRequestsState>((set) => ({
  pullRequests: [],
  currentPR: null,
  comments: [],
  isLoading: false,
  error: null,

  fetchPullRequests: async (repoId, status) => {
    const sid = serverId();
    if (!sid) { set({ error: 'no server' }); return; }
    set({ isLoading: true, error: null });
    try {
      const data = await pullRequestsApi.list(sid, repoId, status ? { status } : undefined);
      const pullRequests = Array.isArray(data) ? data : (data as PaginationResponse<PR>).items;
      set({ pullRequests, isLoading: false });
    } catch (e) {
      set({ error: (e as Error).message, isLoading: false });
    }
  },

  fetchPullRequest: async (repoId, prNumber) => {
    const sid = serverId();
    if (!sid) { set({ error: 'no server' }); return; }
    set({ isLoading: true, error: null });
    try {
      const currentPR = await pullRequestsApi.get(sid, repoId, prNumber);
      set({ currentPR, isLoading: false });
    } catch (e) {
      set({ error: (e as Error).message, isLoading: false });
    }
  },

  createPullRequest: async (repoId, data) => {
    const sid = serverId();
    if (!sid) throw new Error('no server');
    const pr = await pullRequestsApi.create(sid, repoId, data);
    set((state) => ({ pullRequests: [pr, ...state.pullRequests] }));
    return pr;
  },

  updatePullRequest: async (repoId, prNumber, data) => {
    const sid = serverId();
    if (!sid) return;
    const currentPR = await pullRequestsApi.update(sid, repoId, prNumber, data);
    set((state) => ({
      currentPR,
      pullRequests: state.pullRequests.map((p) => (p.pr_number === prNumber ? { ...p, ...currentPR } : p)),
    }));
  },

  closePullRequest: async (repoId, prNumber) => {
    const sid = serverId();
    if (!sid) return;
    const currentPR = await pullRequestsApi.close(sid, repoId, prNumber);
    set((state) => ({
      currentPR,
      pullRequests: state.pullRequests.map((p) => (p.pr_number === prNumber ? { ...p, ...currentPR } : p)),
    }));
  },

  mergePullRequest: async (repoId, prNumber, mergeMethod) => {
    const sid = serverId();
    if (!sid) return;
    const currentPR = await pullRequestsApi.merge(sid, repoId, prNumber, mergeMethod ? { merge_method: mergeMethod } : undefined);
    set((state) => ({
      currentPR,
      pullRequests: state.pullRequests.map((p) => (p.pr_number === prNumber ? { ...p, ...currentPR } : p)),
    }));
  },

  fetchComments: async (repoId, prNumber) => {
    const sid = serverId();
    if (!sid) return;
    try {
      const comments = await pullRequestsApi.getComments(sid, repoId, prNumber);
      set({ comments });
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },

  createComment: async (repoId, prNumber, data) => {
    const sid = serverId();
    if (!sid) throw new Error('no server');
    const comment = await pullRequestsApi.createComment(sid, repoId, prNumber, data);
    set((state) => ({ comments: [...state.comments, comment] }));
    return comment;
  },

  createReview: async (repoId, prNumber, data) => {
    const sid = serverId();
    if (!sid) return;
    await pullRequestsApi.createReview(sid, repoId, prNumber, data);
  },

  clearCurrent: () => {
    set({ currentPR: null, comments: [] });
  },
}));