import { create } from 'zustand';
import { pullRequestsApi, type PR, type PRComment, type CreatePRCommentRequest, type CreatePRReviewRequest } from '../api/pullRequests';

interface PullRequestsState {
  pullRequests: PR[];
  currentPR: PR | null;
  comments: PRComment[];
  isLoading: boolean;
  error: string | null;

  fetchPullRequests: (repoId: number, status?: string) => Promise<void>;
  fetchPullRequest: (repoId: number, prNumber: number) => Promise<void>;
  createPullRequest: (repoId: number, data: { title: string; description?: string; source_branch: string; target_branch: string }) => Promise<PR>;
  updatePullRequest: (repoId: number, prNumber: number, data: { title?: string; description?: string }) => Promise<void>;
  closePullRequest: (repoId: number, prNumber: number) => Promise<void>;
  mergePullRequest: (repoId: number, prNumber: number, mergeMethod?: 'merge' | 'squash' | 'rebase') => Promise<void>;
  fetchComments: (repoId: number, prNumber: number) => Promise<void>;
  createComment: (repoId: number, prNumber: number, data: CreatePRCommentRequest) => Promise<PRComment>;
  createReview: (repoId: number, prNumber: number, data: CreatePRReviewRequest) => Promise<void>;
  clearCurrent: () => void;
}

export const usePullRequestsStore = create<PullRequestsState>((set) => ({
  pullRequests: [],
  currentPR: null,
  comments: [],
  isLoading: false,
  error: null,

  fetchPullRequests: async (repoId, status) => {
    set({ isLoading: true, error: null });
    try {
      const data = await pullRequestsApi.list(repoId, status ? { status } : undefined);
      const pullRequests = Array.isArray(data) ? data : (data as { items: PR[] }).items;
      set({ pullRequests, isLoading: false });
    } catch (e) {
      set({ error: (e as Error).message, isLoading: false });
    }
  },

  fetchPullRequest: async (repoId, prNumber) => {
    set({ isLoading: true, error: null });
    try {
      const currentPR = await pullRequestsApi.get(repoId, prNumber);
      set({ currentPR, isLoading: false });
    } catch (e) {
      set({ error: (e as Error).message, isLoading: false });
    }
  },

  createPullRequest: async (repoId, data) => {
    const pr = await pullRequestsApi.create(repoId, data);
    set((state) => ({ pullRequests: [pr, ...state.pullRequests] }));
    return pr;
  },

  updatePullRequest: async (repoId, prNumber, data) => {
    const currentPR = await pullRequestsApi.update(repoId, prNumber, data);
    set((state) => ({
      currentPR,
      pullRequests: state.pullRequests.map((p) => (p.pr_number === prNumber ? { ...p, ...currentPR } : p)),
    }));
  },

  closePullRequest: async (repoId, prNumber) => {
    const currentPR = await pullRequestsApi.close(repoId, prNumber);
    set((state) => ({
      currentPR,
      pullRequests: state.pullRequests.map((p) => (p.pr_number === prNumber ? { ...p, ...currentPR } : p)),
    }));
  },

  mergePullRequest: async (repoId, prNumber, mergeMethod) => {
    const currentPR = await pullRequestsApi.merge(repoId, prNumber, mergeMethod ? { merge_method: mergeMethod } : undefined);
    set((state) => ({
      currentPR,
      pullRequests: state.pullRequests.map((p) => (p.pr_number === prNumber ? { ...p, ...currentPR } : p)),
    }));
  },

  fetchComments: async (repoId, prNumber) => {
    try {
      const comments = await pullRequestsApi.getComments(repoId, prNumber);
      set({ comments });
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },

  createComment: async (repoId, prNumber, data) => {
    const comment = await pullRequestsApi.createComment(repoId, prNumber, data);
    set((state) => ({ comments: [...state.comments, comment] }));
    return comment;
  },

  createReview: async (repoId, prNumber, data) => {
    await pullRequestsApi.createReview(repoId, prNumber, data);
  },

  clearCurrent: () => {
    set({ currentPR: null, comments: [] });
  },
}));
