import { api } from './client'
import type { User, UserUpdateRequest } from '@/types/api'

export const userApi = {
  me(): Promise<User> {
    return api.get<User>('/users/me')
  },

  get(userId: number): Promise<User> {
    return api.get<User>(`/users/${userId}`)
  },

  list(): Promise<User[]> {
    return api.get<User[]>('/users')
  },

  update(userId: number, data: UserUpdateRequest): Promise<User> {
    return api.put<User>(`/users/${userId}`, data)
  },
}
