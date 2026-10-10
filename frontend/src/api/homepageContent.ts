import { apiClient } from './client';
import type { PaginatedResponse } from './properties';

export interface HomepageNote {
  id: number;
  title: string;
  text: string;
  is_published: boolean;
  display_order: number;
  created_at: string;
  updated_at: string;
}

export type HomepageNotePayload = Pick<
  HomepageNote,
  'title' | 'text' | 'is_published' | 'display_order'
>;

export async function getHomepageNotes(signal?: AbortSignal): Promise<HomepageNote[]> {
  const response = await apiClient.get<PaginatedResponse<HomepageNote>>('/homepage-notes/', { signal });
  return response.data.results;
}

export async function getManagedHomepageNotes(signal?: AbortSignal): Promise<HomepageNote[]> {
  const response = await apiClient.get<PaginatedResponse<HomepageNote>>('/management/homepage-notes/', { signal });
  return response.data.results;
}

export async function createHomepageNote(payload: HomepageNotePayload): Promise<HomepageNote> {
  const response = await apiClient.post<HomepageNote>('/management/homepage-notes/', payload);
  return response.data;
}

export async function updateHomepageNote(
  id: number,
  payload: Partial<HomepageNotePayload>,
): Promise<HomepageNote> {
  const response = await apiClient.patch<HomepageNote>(`/management/homepage-notes/${id}/`, payload);
  return response.data;
}

export async function deleteHomepageNote(id: number): Promise<void> {
  await apiClient.delete(`/management/homepage-notes/${id}/`);
}
