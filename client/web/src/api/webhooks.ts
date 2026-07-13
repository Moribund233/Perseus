import { apiRequest } from './client';

export interface Webhook {
  id: number;
  repository_id: number;
  url: string;
  events: string[];
  secret: string;
  content_type: string;
  is_active: boolean;
  created_at: string;
}

export interface CreateWebhookRequest {
  url: string;
  events: string[];
  secret?: string;
  content_type?: string;
  is_active?: boolean;
}

export interface WebhookDelivery {
  id: number;
  webhook_id: number;
  event: string;
  payload: string;
  status: string;
  status_code: number | null;
  response_body: string | null;
  duration_ms: number | null;
  triggered_at: string;
}

export const webhooksApi = {
  list: (repoId: number) =>
    apiRequest<Webhook[]>(`/api/v1/repositories/${repoId}/webhooks`),

  get: (repoId: number, webhookId: number) =>
    apiRequest<Webhook>(`/api/v1/repositories/${repoId}/webhooks/${webhookId}`),

  create: (repoId: number, data: CreateWebhookRequest) =>
    apiRequest<Webhook>(`/api/v1/repositories/${repoId}/webhooks`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (repoId: number, webhookId: number, data: Partial<CreateWebhookRequest>) =>
    apiRequest<Webhook>(`/api/v1/repositories/${repoId}/webhooks/${webhookId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  delete: (repoId: number, webhookId: number) =>
    apiRequest<void>(`/api/v1/repositories/${repoId}/webhooks/${webhookId}`, {
      method: 'DELETE',
    }),

  test: (repoId: number, webhookId: number) =>
    apiRequest<WebhookDelivery>(`/api/v1/repositories/${repoId}/webhooks/${webhookId}/test`, {
      method: 'POST',
    }),

  listDeliveries: (repoId: number, webhookId: number) =>
    apiRequest<WebhookDelivery[]>(`/api/v1/repositories/${repoId}/webhooks/${webhookId}/deliveries`),

  getDelivery: (repoId: number, webhookId: number, deliveryId: number) =>
    apiRequest<WebhookDelivery>(`/api/v1/repositories/${repoId}/webhooks/${webhookId}/deliveries/${deliveryId}`),
};
