import { apiClient } from './client';

export type ListingType = 'sale' | 'rent';
export type PropertyType =
  | 'house' | 'villa' | 'apartment' | 'condominium' | 'land'
  | 'office' | 'shop' | 'warehouse' | 'commercial' | 'other';

export interface PropertySummary {
  id: number;
  title: string;
  slug: string;
  location: string;
  latitude: number | string | null;
  longitude: number | string | null;
  category: string;
  listing_type: ListingType;
  rental_frequency: 'daily' | 'weekly' | 'monthly' | 'yearly' | '';
  price: string;
  currency: 'ETB';
  bedrooms: number;
  bathrooms: number;
  area_sqft: number;
  status: 'available' | 'rented' | 'sold' | 'inactive';
  service_type: 'broker_managed' | 'owner_announced';
  public_contact_name: string;
  public_contact_phone: string;
  public_contact_email: string;
  primary_image: string | null;
  images: { id: number; url: string | null; caption: string; is_primary: boolean }[];
  created_at: string;
}

export interface PropertyDetail extends PropertySummary {
  description: string;
  features: string;
  amenities: { id: number; name: string; name_am: string; slug: string }[];
  updated_at: string;
}

export interface PropertyFilters {
  search?: string;
  listing_type?: ListingType;
  property_type?: PropertyType;
  location?: string;
  location_id?: number;
  min_price?: string;
  max_price?: string;
  min_bedrooms?: string;
  min_bathrooms?: string;
  max_bedrooms?: string;
  max_bathrooms?: string;
  min_size?: string;
  max_size?: string;
  amenities?: string;
  ordering?: string;
  page?: number;
  page_size?: number;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export async function getLatestProperties(signal?: AbortSignal): Promise<PropertySummary[]> {
  const response = await apiClient.get<PaginatedResponse<PropertySummary>>('/properties/', {
    params: { page_size: 3, ordering: '-created_at' },
    signal,
  });
  return response.data.results;
}

export async function getProperties(
  filters: PropertyFilters,
  signal?: AbortSignal,
): Promise<PaginatedResponse<PropertySummary>> {
  const response = await apiClient.get<PaginatedResponse<PropertySummary>>('/properties/', {
    params: filters,
    signal,
  });
  return response.data;
}

export async function getProperty(slug: string, signal?: AbortSignal): Promise<PropertyDetail> {
  const response = await apiClient.get<PropertyDetail>(
    `/properties/${encodeURIComponent(slug)}/`,
    { signal },
  );
  return response.data;
}
