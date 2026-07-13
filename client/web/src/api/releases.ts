import { apiRequest } from './client';

export interface Release {
  id: number;
  repository_id: number;
  release_number: number;
  tag_name: string;
  name: string;
  description: string;
  commit_hash: string;
  author_id: number;
  is_draft: boolean;
  is_prerelease: boolean;
  created_at: string;
  author?: { id: number; username: string; full_name: string | null };
  assets?: ReleaseAsset[];
}

export interface ReleaseAsset {
  id: number;
  release_id: number;
  name: string;
  file_size: number;
  content_type: string;
  uploader_id: number;
  created_at: string;
}

export interface CreateReleaseRequest {
  tag_name: string;
  name?: string;
  description?: string;
  commit_hash?: string;
  is_draft?: boolean;
  is_prerelease?: boolean;
  create_git_tag?: boolean;
}

export const releasesApi = {
  list: (repoId: number) =>
    apiRequest<Release[]>(`/api/v1/repositories/${repoId}/releases`),

  get: (repoId: number, releaseNumber: number) =>
    apiRequest<Release>(`/api/v1/repositories/${repoId}/releases/${releaseNumber}`),

  getByTag: (repoId: number, tagName: string) =>
    apiRequest<Release>(`/api/v1/repositories/${repoId}/releases/tag/${encodeURIComponent(tagName)}`),

  create: (repoId: number, data: CreateReleaseRequest) =>
    apiRequest<Release>(`/api/v1/repositories/${repoId}/releases`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (repoId: number, releaseNumber: number, data: Partial<CreateReleaseRequest>) =>
    apiRequest<Release>(`/api/v1/repositories/${repoId}/releases/${releaseNumber}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  delete: (repoId: number, releaseNumber: number) =>
    apiRequest<void>(`/api/v1/repositories/${repoId}/releases/${releaseNumber}`, {
      method: 'DELETE',
    }),
};
