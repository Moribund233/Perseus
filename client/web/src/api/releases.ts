import { apiRequest } from './client';

export interface Release {
  id: string;
  repository_id: string;
  release_number: number;
  tag_name: string;
  name: string;
  description: string;
  commit_hash: string;
  author_id: string;
  is_draft: boolean;
  is_prerelease: boolean;
  created_at: string;
  author?: { id: string; username: string; full_name: string | null };
  assets?: ReleaseAsset[];
}

export interface ReleaseAsset {
  id: string;
  release_id: string;
  name: string;
  file_size: number;
  content_type: string;
  uploader_id: string;
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
  list: (repoId: string) =>
    apiRequest<Release[]>(`/api/v1/repositories/${repoId}/releases`),

  get: (repoId: string, releaseNumber: number) =>
    apiRequest<Release>(`/api/v1/repositories/${repoId}/releases/${releaseNumber}`),

  getByTag: (repoId: string, tagName: string) =>
    apiRequest<Release>(`/api/v1/repositories/${repoId}/releases/tag/${encodeURIComponent(tagName)}`),

  create: (repoId: string, data: CreateReleaseRequest) =>
    apiRequest<Release>(`/api/v1/repositories/${repoId}/releases`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (repoId: string, releaseNumber: number, data: Partial<CreateReleaseRequest>) =>
    apiRequest<Release>(`/api/v1/repositories/${repoId}/releases/${releaseNumber}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  delete: (repoId: string, releaseNumber: number) =>
    apiRequest<void>(`/api/v1/repositories/${repoId}/releases/${releaseNumber}`, {
      method: 'DELETE',
    }),
};
