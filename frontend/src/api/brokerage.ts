import { apiClient } from './client';

export interface BrokerageContact {
  business_name: string;
  phone: string;
  whatsapp_url: string;
  telegram_url: string;
  email: string;
  facebook_url: string;
  instagram_url: string;
  tiktok_url: string;
  youtube_url: string;
  linkedin_url: string;
}

export const emptyBrokerageContact: BrokerageContact = {
  business_name: '',
  phone: '',
  whatsapp_url: '',
  telegram_url: '',
  email: '',
  facebook_url: '',
  instagram_url: '',
  tiktok_url: '',
  youtube_url: '',
  linkedin_url: '',
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
