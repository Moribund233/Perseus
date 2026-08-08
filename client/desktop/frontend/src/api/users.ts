import { proxyRequest } from './client';

export interface User {
  id: string;
  username: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
  updated_at: string;
}

// usersApi：全部经本地网关 proxy 转发到目标服务器，首个参数为服务器 id。
export const usersApi = {
  getMe: (serverId: string) =>
    proxyRequest<User>(serverId, '/api/v1/users/me'),
};