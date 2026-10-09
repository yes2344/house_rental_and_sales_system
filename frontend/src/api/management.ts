import { apiClient } from './client';
import type { PaginatedResponse } from './properties';

export type ManagedListingType = 'sale' | 'rent';
export type ManagedPropertyType = 'house' | 'villa' | 'apartment' | 'land' | 'commercial';
export type ManagedPropertyStatus = 'available' | 'rented' | 'sold' | 'inactive';
export type PublicationStatus = 'draft' | 'pending_review' | 'published' | 'rejected';
export type ViewingRequestStatus = 'pending' | 'confirmed' | 'rejected';

export interface AmenityOption {
  id: number;
  name: string;
  name_am: string;
  slug: string;
}

export interface ManagedProperty {
  id: number;
  title: string;
  slug: string;
  location: string;
  category: ManagedPropertyType;
  listing_type: ManagedListingType;
  price: string;
  currency: 'ETB';
  bedrooms: number;
  bathrooms: number;
  area_sqft: number;
  description: string;
  features: string;
  status: ManagedPropertyStatus;
  publication_status: PublicationStatus;
  is_featured: boolean;
  owner_id: number | null;
  amenities: number[];
  contact_name: string;
  contact_phone: string;
  contact_email: string;
  created_at: string;
  updated_at: string;
}

export interface ManagedPropertyPayload {
  title: string;
  location: string;
  category: ManagedPropertyType;
  listing_type: ManagedListingType;
  price: string;
  bedrooms: number;
  bathrooms: number;
  area_sqft: number;
  description: string;
  features: string;
  status: ManagedPropertyStatus;
  amenities: number[];
  contact_name: string;
  contact_phone: string;
  contact_email: string;
}

export interface ManagedImage {
  id: number;
  image: string;
  caption: string;
  is_primary: boolean;
  created_at: string;
}

export interface ManagedViewingRequest {
  id: number;
  property: {
    id: number;
    title: string;
    slug: string;
    location: string;
  };
  full_name: string;
  email: string;
  phone: string;
  preferred_date: string;
  preferred_time: string | null;
  message: string;
  status: ViewingRequestStatus;
  scheduled_date: string | null;
  scheduled_time: string | null;
  agent_notes: string;
  created_at: string;
}

export interface ManagedViewingRequestPayload {
  status: ViewingRequestStatus;
  scheduled_date: string | null;
  scheduled_time: string | null;
  agent_notes: string;
}

export interface ManagedPropertyFilters {
  search?: string;
  status?: ManagedPropertyStatus;
  publication_status?: PublicationStatus;
  listing_type?: ManagedListingType;
  property_type?: ManagedPropertyType;
  ordering?: string;
  page?: number;
  page_size?: number;
}

export async function getAmenities(signal?: AbortSignal): Promise<AmenityOption[]> {
  const response = await apiClient.get<PaginatedResponse<AmenityOption>>('/amenities/', { signal });
  return response.data.results;
}

export async function getManagedProperties(
  filters: ManagedPropertyFilters,
  signal?: AbortSignal,
): Promise<PaginatedResponse<ManagedProperty>> {
  const response = await apiClient.get<PaginatedResponse<ManagedProperty>>('/owner/properties/', {
    params: filters,
    signal,
  });
  return response.data;
}

export async function getManagedProperty(id: number, signal?: AbortSignal): Promise<ManagedProperty> {
  const response = await apiClient.get<ManagedProperty>(`/owner/properties/${id}/`, { signal });
  return response.data;
}

export async function createManagedProperty(payload: ManagedPropertyPayload): Promise<ManagedProperty> {
  const response = await apiClient.post<ManagedProperty>('/owner/properties/', payload);
  return response.data;
}

export async function updateManagedProperty(
  id: number,
  payload: ManagedPropertyPayload,
): Promise<ManagedProperty> {
  const response = await apiClient.patch<ManagedProperty>(`/owner/properties/${id}/`, payload);
  return response.data;
}

export async function deleteManagedProperty(id: number): Promise<void> {
  await apiClient.delete(`/owner/properties/${id}/`);
}

export async function getManagedImages(propertyId: number, signal?: AbortSignal): Promise<ManagedImage[]> {
  const response = await apiClient.get<PaginatedResponse<ManagedImage>>(
    `/owner/properties/${propertyId}/images/`,
    { signal },
  );
  return response.data.results;
}

export async function uploadManagedImage(
  propertyId: number,
  image: File,
  caption: string,
  isPrimary: boolean,
): Promise<ManagedImage> {
  const formData = new FormData();
  formData.append('image', image);
  formData.append('caption', caption);
  formData.append('is_primary', String(isPrimary));
  const response = await apiClient.post<ManagedImage>(
    `/owner/properties/${propertyId}/images/`,
    formData,
  );
  return response.data;
}

export async function updateManagedImage(
  propertyId: number,
  imageId: number,
  payload: { is_primary?: boolean; caption?: string },
): Promise<ManagedImage> {
  const response = await apiClient.patch<ManagedImage>(
    `/owner/properties/${propertyId}/images/${imageId}/`,
    payload,
  );
  return response.data;
}

export async function deleteManagedImage(propertyId: number, imageId: number): Promise<void> {
  await apiClient.delete(`/owner/properties/${propertyId}/images/${imageId}/`);
}

export interface ManagedViewingRequestFilters {
  status?: ViewingRequestStatus;
  ordering?: string;
  page?: number;
  page_size?: number;
}

export async function getManagedViewingRequests(
  filters: ManagedViewingRequestFilters,
  signal?: AbortSignal,
): Promise<PaginatedResponse<ManagedViewingRequest>> {
  const response = await apiClient.get<PaginatedResponse<ManagedViewingRequest>>(
    '/owner/viewing-requests/',
    { params: filters, signal },
  );
  return response.data;
}

export async function getManagedViewingRequest(
  id: number,
): Promise<ManagedViewingRequest> {
  const response = await apiClient.get<ManagedViewingRequest>(`/owner/viewing-requests/${id}/`);
  return response.data;
}

export async function updateManagedViewingRequest(
  id: number,
  payload: ManagedViewingRequestPayload,
): Promise<ManagedViewingRequest> {
  const response = await apiClient.patch<ManagedViewingRequest>(
    `/owner/viewing-requests/${id}/`,
    payload,
  );
  return response.data;
}
