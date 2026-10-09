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
  status: 'pending' | 'proposed' | 'confirmed' | 'rejected' | 'declined';
  created_at: string;
  receipt_token: string;
}

export interface ViewingRequestStatus {
  id: number;
  property_title: string;
  status: 'pending' | 'proposed' | 'confirmed' | 'rejected' | 'declined';
  preferred_date: string;
  preferred_time: string | null;
  proposed_date: string | null;
  proposed_time: string | null;
  scheduled_date: string | null;
  scheduled_time: string | null;
  appointment_timezone: string;
  created_at: string;
}

export async function createViewingRequest(
  payload: ViewingRequestPayload,
): Promise<ViewingRequestReceipt> {
  const response = await apiClient.post<ViewingRequestReceipt>('/viewing-requests/', payload);
  return response.data;
}

export async function getViewingRequestStatus(receiptToken: string): Promise<ViewingRequestStatus> {
  const response = await apiClient.get<ViewingRequestStatus>('/viewing-requests/receipt/', {
    headers: { 'X-Viewing-Receipt': receiptToken },
  });
  return response.data;
}

export async function respondToViewingProposal(
  receiptToken: string,
  decision: 'accept' | 'decline',
): Promise<ViewingRequestStatus> {
  const response = await apiClient.post<ViewingRequestStatus>(
    '/viewing-requests/receipt/',
    { decision },
    { headers: { 'X-Viewing-Receipt': receiptToken } },
  );
  return response.data;
}
