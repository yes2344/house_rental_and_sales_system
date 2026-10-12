import { apiClient } from './client';
import type { PaginatedResponse } from './properties';

export interface MarketplaceLocation {
  id: number;
  name: string;
  name_am: string;
  slug: string;
  location_type: string;
  parent_id: number | null;
  is_active: boolean;
  display_order: number;
}

export interface OwnerAnnouncement {
  id: number;
  property: {
    id: number;
    title: string;
    slug: string;
    location: string;
    administrative_location: number | null;
    administrative_location_name: string;
    administrative_location_path: string[];
    publication_status: string;
    property_type: string;
    listing_type: 'sale' | 'rent';
    rental_frequency: string;
    price: string;
    description: string;
    features: string;
    latitude: number | string | null;
    longitude: number | string | null;
    bedrooms: number;
    bathrooms: number;
    area_sqft: number;
    area_value: string | null;
    area_unit: string;
    images: { id: number; url: string | null; caption: string; is_primary: boolean }[];
  };
  status: string;
  submitter_name: string;
  broker_feedback: string;
  owner_contact_name: string;
  owner_contact_phone: string;
  owner_contact_email: string;
  public_contact_name: string;
  public_contact_phone: string;
  public_contact_email: string;
  public_contact_visible: boolean;
  renewal_requested_at: string | null;
  agreements: {
    start_date: string;
    end_date: string;
    duration_months: number;
    terms: string;
    renewal_conditions: string;
    status: string;
  }[];
  submitted_at: string;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
}

export type BrokerAnnouncementQueue =
  | 'pending_review'
  | 'approved'
  | 'changes'
  | 'renewal_requested'
  | 'expiring_soon'
  | 'expired'
  | 'closed';

export interface BrokerAnnouncementFilters {
  queue?: BrokerAnnouncementQueue;
  search?: string;
  property_type?: string;
  listing_type?: 'sale' | 'rent';
  publication_status?: string;
  location?: string;
  expiring_soon?: boolean;
  expired?: boolean;
  ordering?: 'submitted_at' | '-submitted_at' | 'updated_at' | '-updated_at'
    | 'property__title' | '-property__title'
    | 'active_agreement_end_date' | '-active_agreement_end_date';
  page?: number;
  page_size?: number;
}

export interface BrokerAnnouncementSummary {
  total: number;
  pending_review: number;
  approved: number;
  changes: number;
  renewal_requested: number;
  expiring_soon: number;
  expired: number;
  closed: number;
}

export interface BrokerAnnouncementPage extends PaginatedResponse<OwnerAnnouncement> {
  summary: BrokerAnnouncementSummary;
}

export interface OwnerAnnouncementPayload {
  title: string;
  location: string;
  administrative_location?: number | null;
  property_type: string;
  listing_type: 'sale' | 'rent';
  price: string;
  rental_frequency?: string;
  bedrooms: number;
  bathrooms: number;
  area_sqft: number;
  description: string;
  features: string;
  latitude?: string | null;
  longitude?: string | null;
  owner_contact_name: string;
  owner_contact_phone: string;
  owner_contact_email: string;
  authorization_confirmed: boolean;
  terms_accepted: boolean;
  images?: File[];
}

export interface AnnouncementDecision {
  action: 'approve' | 'request_corrections' | 'reject' | 'suspend';
  feedback?: string;
  confirm_summary?: boolean;
  agreement_start_date?: string;
  agreement_end_date?: string;
  duration_months?: number;
  agreement_terms?: string;
  renewal_conditions?: string;
  public_contact_visible?: boolean;
  public_contact_name?: string;
  public_contact_phone?: string;
  public_contact_email?: string;
  exact_location_is_public?: boolean;
}

export interface MarketplaceNotification {
  id: number;
  notification_type: string;
  message: string;
  announcement_id: number | null;
  read_at: string | null;
  created_at: string;
}

function toFormData(payload: OwnerAnnouncementPayload): FormData {
  const data = new FormData();
  for (const [key, value] of Object.entries(payload)) {
    if (key === 'images') {
      value?.forEach((image: File) => data.append('images', image));
    } else if (value !== undefined && value !== null) {
      data.append(key, String(value));
    }
  }
  return data;
}

export async function getLocations(
  parentId?: number,
  signal?: AbortSignal,
  includeAll = false,
): Promise<MarketplaceLocation[]> {
  const response = await apiClient.get<MarketplaceLocation[]>('/locations/', {
    params: includeAll ? { all: 1 } : parentId ? { parent_id: parentId } : undefined,
    signal,
  });
  return response.data;
}

export async function getOwnerAnnouncements(signal?: AbortSignal): Promise<PaginatedResponse<OwnerAnnouncement>> {
  const response = await apiClient.get<PaginatedResponse<OwnerAnnouncement>>('/owner/announcements/', { signal });
  return response.data;
}

export async function submitOwnerAnnouncement(payload: OwnerAnnouncementPayload): Promise<OwnerAnnouncement> {
  const response = await apiClient.post<OwnerAnnouncement>('/owner/announcements/', toFormData(payload));
  return response.data;
}

export async function updateOwnerAnnouncement(
  id: number,
  payload: OwnerAnnouncementPayload,
): Promise<OwnerAnnouncement> {
  const response = await apiClient.patch<OwnerAnnouncement>(
    `/owner/announcements/${id}/`,
    toFormData(payload),
  );
  return response.data;
}

export async function deleteOwnerAnnouncementImage(announcementId: number, imageId: number): Promise<void> {
  await apiClient.delete(`/owner/announcements/${announcementId}/images/${imageId}/`);
}

export async function withdrawOwnerAnnouncement(id: number): Promise<void> {
  await apiClient.post(`/owner/announcements/${id}/withdraw/`);
}

export async function requestAnnouncementRenewal(id: number): Promise<void> {
  await apiClient.post(`/owner/announcements/${id}/renew/`);
}

export async function getBrokerAnnouncements(
  filters: BrokerAnnouncementFilters = {},
  signal?: AbortSignal,
): Promise<BrokerAnnouncementPage> {
  const response = await apiClient.get<BrokerAnnouncementPage>('/management/owner-announcements/', {
    params: filters,
    signal,
  });
  return response.data;
}

export async function getBrokerAnnouncement(id: number, signal?: AbortSignal): Promise<OwnerAnnouncement> {
  const response = await apiClient.get<OwnerAnnouncement>(`/management/owner-announcements/${id}/`, { signal });
  return response.data;
}

export async function requestBrokerAnnouncementRenewal(id: number): Promise<OwnerAnnouncement> {
  const response = await apiClient.post<OwnerAnnouncement>(`/management/owner-announcements/${id}/renewal/`);
  return response.data;
}

export async function decideOwnerAnnouncement(
  id: number,
  decision: AnnouncementDecision,
): Promise<OwnerAnnouncement> {
  const response = await apiClient.post<OwnerAnnouncement>(
    `/management/owner-announcements/${id}/decision/`,
    decision,
  );
  return response.data;
}

export async function getMarketplaceNotifications(signal?: AbortSignal): Promise<PaginatedResponse<MarketplaceNotification>> {
  const response = await apiClient.get<PaginatedResponse<MarketplaceNotification>>('/notifications/', { signal });
  return response.data;
}

export async function markMarketplaceNotificationRead(id: number): Promise<MarketplaceNotification> {
  const response = await apiClient.post<MarketplaceNotification>(`/notifications/${id}/read/`);
  return response.data;
}
