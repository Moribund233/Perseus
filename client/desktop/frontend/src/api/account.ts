import { proxyRequest } from './client';

export interface SSHKey {
  id: string;
  name: string;
  public_key: string;
  fingerprint: string;
  created_at: string;
}

export interface CreateSSHKeyRequest {
  name: string;
  public_key: string;
}

export interface OAuthAccount {
  provider: string;
  provider_username: string;
  created_at: string;
}

// accountApi：用户中心（SSH Keys / OAuth 关联），经本地网关代理转发到服务器。
export const accountApi = {
  listSSHKeys: (serverId: string) =>
    proxyRequest<SSHKey[]>(serverId, '/api/v1/keys'),

  addSSHKey: (serverId: string, data: CreateSSHKeyRequest) =>
    proxyRequest<SSHKey>(serverId, '/api/v1/keys', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  deleteSSHKey: (serverId: string, keyId: string) =>
    proxyRequest<void>(serverId, `/api/v1/keys/${keyId}`, { method: 'DELETE' }),

  listOAuthAccounts: (serverId: string) =>
    proxyRequest<OAuthAccount[]>(serverId, '/api/v1/users/me/oauth'),

  unlinkOAuth: (serverId: string, provider: string) =>
    proxyRequest<void>(serverId, `/api/v1/users/me/oauth/${provider}`, { method: 'DELETE' }),
};
