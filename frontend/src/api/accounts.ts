import { apiClient } from './client';

export type AccountRole = 'customer' | 'owner' | 'broker' | 'administrator' | null;

export interface Account {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: AccountRole;
  phone: string;
  management_permissions: string[];
  is_platform_owner: boolean;
}

export interface RegistrationPayload {
  username: string;
  email: string;
  password: string;
  phone?: string;
}

export interface AccountUpdatePayload {
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
}

export interface AccountActivity {
  favorites: {
    id: number;
    property: {
      id: number;
      title: string;
      slug: string;
      listing_type: 'sale' | 'rent';
      status: string;
    };
    created_at: string;
  }[];
  viewing_requests: {
    id: number;
    property: {
      id: number;
      title: string;
      slug: string;
      listing_type: 'sale' | 'rent';
      status: string;
    };
    status: 'pending' | 'proposed' | 'confirmed' | 'rejected' | 'declined';
    preferred_date: string;
    preferred_time: string | null;
    scheduled_date: string | null;
    scheduled_time: string | null;
    created_at: string;
  }[];
}

export async function getCsrfToken(): Promise<string> {
  const response = await apiClient.get<{ csrf_token: string }>('/auth/csrf/');
  return response.data.csrf_token;
}

export async function getCurrentAccount(signal?: AbortSignal): Promise<Account> {
  const response = await apiClient.get<Account>('/auth/me/', { signal });
  return response.data;
}

export async function registerAccount(payload: RegistrationPayload): Promise<Account> {
  const response = await apiClient.post<Account>('/auth/register/', payload);
  return response.data;
}

export async function startSession(username: string, password: string): Promise<Account> {
  const csrfToken = await getCsrfToken();
  const response = await apiClient.post<Account & { csrf_token: string }>(
    '/auth/login/',
    { username, password },
    { headers: { 'X-CSRFToken': csrfToken } },
  );
  return response.data;
}

export async function endSession(): Promise<void> {
  await apiClient.post('/auth/logout/', {});
}

export async function updateAccount(payload: AccountUpdatePayload): Promise<Account> {
  const response = await apiClient.patch<Account>('/auth/me/', payload);
  return response.data;
}

export async function getAccountActivity(signal?: AbortSignal): Promise<AccountActivity> {
  const response = await apiClient.get<AccountActivity>('/auth/activity/', { signal });
  return response.data;
}
