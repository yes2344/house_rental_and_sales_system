import { apiClient } from './client';

export interface ViewingRequestPayload {
  property_id: number;
  full_name: string;
  email: string;
  phone: string;
  preferred_date: string;
  message?: string;
}

export interface ViewingRequestReceipt {
  id: number;
  status: 'pending' | 'confirmed' | 'rejected';
  created_at: string;
}

export async function createViewingRequest(
  payload: ViewingRequestPayload,
): Promise<ViewingRequestReceipt> {
  const response = await apiClient.post<ViewingRequestReceipt>('/viewing-requests/', payload);
  return response.data;
}
