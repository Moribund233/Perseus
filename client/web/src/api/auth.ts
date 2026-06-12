import { api } from './client'
import type {
  LoginRequest,
  LoginResponse,
  RefreshTokenRequest,
  RefreshTokenResponse,
  User,
  UserCreateRequest,
} from '@/types/api'

export const authApi = {
  login(data: LoginRequest): Promise<LoginResponse> {
    return api.post<LoginResponse>('/auth/login', data, true)
  },

  register(data: UserCreateRequest): Promise<User> {
    return api.post<User>('/users', data, true)
  },

  refresh(data: RefreshTokenRequest): Promise<RefreshTokenResponse> {
    return api.post<RefreshTokenResponse>('/auth/refresh', data, true)
  },
}
