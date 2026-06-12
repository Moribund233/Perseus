import { api } from './client'
import type {
  Repository,
  RepositoryCreateRequest,
  PaginatedResponse,
} from '@/types/api'

export const repositoryApi = {
  list(): Promise<Repository[]> {
    return api.get<Repository[]>('/repositories')
  },

  listPublic(): Promise<Repository[]> {
    return api.get<Repository[]>('/repositories/public', true)
  },

  listByUser(userId: number): Promise<Repository[]> {
    return api.get<Repository[]>(`/repositories/user/${userId}`)
  },

  get(repoId: number): Promise<Repository> {
    return api.get<Repository>(`/repositories/${repoId}`)
  },

  create(data: RepositoryCreateRequest): Promise<Repository> {
    return api.post<Repository>('/repositories', data)
  },

  update(repoId: number, data: Partial<RepositoryCreateRequest>): Promise<Repository> {
    return api.put<Repository>(`/repositories/${repoId}`, data)
  },

  delete(repoId: number): Promise<void> {
    return api.delete<void>(`/repositories/${repoId}`)
  },

  checkAccess(repoId: number, userId: number): Promise<{ has_access: boolean }> {
    return api.get<{ has_access: boolean }>(
      `/repositories/${repoId}/access?user_id=${userId}`
    )
  },
}
