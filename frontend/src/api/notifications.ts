import { apiClient } from './client';
import type { PaginatedResponse } from './properties';

export interface MarketplaceNotification {
  id: number;
  notification_type: string;
  message: string;
  announcement_id: number | null;
  read_at: string | null;
  created_at: string;
}

export async function getMarketplaceNotifications(
  signal?: AbortSignal,
): Promise<PaginatedResponse<MarketplaceNotification>> {
  const response = await apiClient.get<PaginatedResponse<MarketplaceNotification>>('/notifications/', {
    signal,
  });
  return response.data;
}

export async function markMarketplaceNotificationRead(id: number): Promise<MarketplaceNotification> {
  const response = await apiClient.post<MarketplaceNotification>(`/notifications/${id}/read/`);
  return response.data;
}
