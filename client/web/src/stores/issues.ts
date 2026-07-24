import { create } from 'zustand';
import { issuesApi, type Issue, type IssueComment, type CreateIssueRequest, type UpdateIssueRequest, type IssueFilter, type PaginationResponse } from '../api/issues';

interface IssuesState {
  issues: Issue[];
  currentIssue: Issue | null;
  comments: IssueComment[];
  isLoading: boolean;
  error: string | null;

  fetchIssues: (repoId: string, status?: string) => Promise<void>;
  filterIssues: (repoId: string, filter: IssueFilter) => Promise<void>;
  fetchIssue: (repoId: string, issueNumber: number) => Promise<void>;
  createIssue: (repoId: string, data: CreateIssueRequest) => Promise<Issue>;
  updateIssue: (repoId: string, issueNumber: number, data: UpdateIssueRequest) => Promise<void>;
  closeIssue: (repoId: string, issueNumber: number) => Promise<void>;
  reopenIssue: (repoId: string, issueNumber: number) => Promise<void>;
  fetchComments: (repoId: string, issueNumber: number) => Promise<void>;
  createComment: (repoId: string, issueNumber: number, content: string) => Promise<IssueComment>;
  clearCurrent: () => void;
}

export const useIssuesStore = create<IssuesState>((set) => ({
  issues: [],
  currentIssue: null,
  comments: [],
  isLoading: false,
  error: null,

  fetchIssues: async (repoId, status) => {
    set({ isLoading: true, error: null });
    try {
      const response = await issuesApi.list(repoId, status ? { status } : undefined);
      const issues = (response as PaginationResponse<Issue>).items ?? (response as unknown as Issue[]);
      set({ issues, isLoading: false });
    } catch (e) {
      set({ error: (e as Error).message, isLoading: false });
    }
  },

  filterIssues: async (repoId, filter) => {
    set({ isLoading: true, error: null });
    try {
      const response = await issuesApi.filter(repoId, filter);
      const issues = (response as PaginationResponse<Issue>).items ?? (response as unknown as Issue[]);
      set({ issues, isLoading: false });
    } catch (e) {
      set({ error: (e as Error).message, isLoading: false });
    }
  },

  fetchIssue: async (repoId, issueNumber) => {
    set({ isLoading: true, error: null });
    try {
      const currentIssue = await issuesApi.get(repoId, issueNumber);
      set({ currentIssue, isLoading: false });
    } catch (e) {
      set({ error: (e as Error).message, isLoading: false });
    }
  },

  createIssue: async (repoId, data) => {
    const issue = await issuesApi.create(repoId, data);
    set((state) => ({ issues: [issue, ...state.issues] }));
    return issue;
  },

  updateIssue: async (repoId, issueNumber, data) => {
    const currentIssue = await issuesApi.update(repoId, issueNumber, data);
    set((state) => ({
      currentIssue,
      issues: state.issues.map((i) => (i.issue_number === issueNumber ? { ...i, ...currentIssue } : i)),
    }));
  },

  closeIssue: async (repoId, issueNumber) => {
    const currentIssue = await issuesApi.close(repoId, issueNumber);
    set((state) => ({
      currentIssue,
      issues: state.issues.map((i) => (i.issue_number === issueNumber ? { ...i, ...currentIssue } : i)),
    }));
  },

  reopenIssue: async (repoId, issueNumber) => {
    const currentIssue = await issuesApi.reopen(repoId, issueNumber);
    set((state) => ({
      currentIssue,
      issues: state.issues.map((i) => (i.issue_number === issueNumber ? { ...i, ...currentIssue } : i)),
    }));
  },

  fetchComments: async (repoId, issueNumber) => {
    try {
      const comments = await issuesApi.getComments(repoId, issueNumber);
      set({ comments });
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },

  createComment: async (repoId, issueNumber, content) => {
    const comment = await issuesApi.createComment(repoId, issueNumber, { content });
    set((state) => ({ comments: [...state.comments, comment] }));
    return comment;
  },

  clearCurrent: () => {
    set({ currentIssue: null, comments: [] });
  },
}));
