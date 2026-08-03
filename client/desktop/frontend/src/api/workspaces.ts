import { apiRequest } from './client';

export interface Workspace {
  id: string;
  name: string;
  path: string;
  remote_url?: string;
}

export interface FileNode {
  name: string;
  path: string;
  is_dir: boolean;
  children?: FileNode[];
}

export interface FileContent {
  content: string;
  binary: boolean;
  truncated: boolean;
  size: number;
}

export interface WriteResult { lines: number; bytes: number }

export interface GitStatus {
  branch: string;
  ahead: number;
  behind: number;
  staged: Array<{ x: string; y: string; path: string }>;
  modified: Array<{ x: string; y: string; path: string }>;
  untracked: string[];
}

export const listWorkspaces = () =>
  apiRequest<{ items: Workspace[] }>('/api/local/workspaces').then((r) => r.items);

export const createWorkspace = (input: { name: string; path: string; url?: string; clone?: boolean }) =>
  apiRequest<Workspace>('/api/local/workspaces', { method: 'POST', body: JSON.stringify(input) });

export const getTree = (wsId: string) =>
  apiRequest<FileNode>(`/api/local/workspaces/${wsId}/tree`);

export const readFile = (wsId: string, path: string) =>
  apiRequest<FileContent>(`/api/local/workspaces/${wsId}/file?path=${encodeURIComponent(path)}`);

export const writeFile = (wsId: string, path: string, content: string) =>
  apiRequest<WriteResult>(`/api/local/workspaces/${wsId}/file`, {
    method: 'PUT',
    body: JSON.stringify({ path, content }),
  });

export const gitStatus = (wsId: string) =>
  apiRequest<GitStatus>(`/api/local/workspaces/${wsId}/git/status`, { method: 'POST' });

export const gitAdd = (wsId: string, paths: string[]) =>
  apiRequest<{ ok: boolean }>(`/api/local/workspaces/${wsId}/git/add`, {
    method: 'POST', body: JSON.stringify({ paths }),
  });

export const gitCommit = (wsId: string, message: string) =>
  apiRequest<{ ok: boolean }>(`/api/local/workspaces/${wsId}/git/commit`, {
    method: 'POST', body: JSON.stringify({ message }),
  });
