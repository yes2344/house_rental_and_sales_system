import { apiClient } from './client';

export type SocialPlatform =
  | 'facebook'
  | 'whatsapp'
  | 'telegram'
  | 'instagram'
  | 'tiktok'
  | 'youtube'
  | 'linkedin';

export interface BrokerageSocialLink {
  platform: SocialPlatform;
  url: string;
  is_enabled: boolean;
  display_order: number;
}

export interface BrokerageContact {
  business_name: string;
  phone: string;
  email: string;
  social_links: BrokerageSocialLink[];
}

export const emptyBrokerageContact: BrokerageContact = {
  business_name: '',
  phone: '',
  email: '',
  social_links: [],
};

export async function getBrokerageContact(signal?: AbortSignal): Promise<BrokerageContact> {
  const response = await apiClient.get<BrokerageContact>('/brokerage/contact/', { signal });
  return response.data;
}

export async function updateBrokerageContact(
  updates: Partial<BrokerageContact>,
): Promise<BrokerageContact> {
  const response = await apiClient.patch<BrokerageContact>('/brokerage/contact/', updates);
  return response.data;
}
