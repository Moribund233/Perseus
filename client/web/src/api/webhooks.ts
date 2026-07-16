import { apiRequest } from './client';

export interface Webhook {
  id: string;
  repository_id: string;
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
  id: string;
  webhook_id: string;
  event: string;
  payload: string;
  status: string;
  status_code: number | null;
  response_body: string | null;
  duration_ms: number | null;
  triggered_at: string;
}

export const webhooksApi = {
  list: (repoId: string) =>
    apiRequest<Webhook[]>(`/api/v1/repositories/${repoId}/webhooks`),

  get: (repoId: string, webhookId: string) =>
    apiRequest<Webhook>(`/api/v1/repositories/${repoId}/webhooks/${webhookId}`),

  create: (repoId: string, data: CreateWebhookRequest) =>
    apiRequest<Webhook>(`/api/v1/repositories/${repoId}/webhooks`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (repoId: string, webhookId: string, data: Partial<CreateWebhookRequest>) =>
    apiRequest<Webhook>(`/api/v1/repositories/${repoId}/webhooks/${webhookId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  delete: (repoId: string, webhookId: string) =>
    apiRequest<void>(`/api/v1/repositories/${repoId}/webhooks/${webhookId}`, {
      method: 'DELETE',
    }),

  test: (repoId: string, webhookId: string) =>
    apiRequest<WebhookDelivery>(`/api/v1/repositories/${repoId}/webhooks/${webhookId}/test`, {
      method: 'POST',
    }),

  listDeliveries: (repoId: string, webhookId: string) =>
    apiRequest<WebhookDelivery[]>(`/api/v1/repositories/${repoId}/webhooks/${webhookId}/deliveries`),

  getDelivery: (repoId: string, webhookId: string, deliveryId: string) =>
    apiRequest<WebhookDelivery>(`/api/v1/repositories/${repoId}/webhooks/${webhookId}/deliveries/${deliveryId}`),
};
