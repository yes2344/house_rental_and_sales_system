import type { ListingType } from '../api/properties';
import type { ManagedRentalFrequency } from '../api/management';
import type { Locale, MessageKey } from '../i18n';

type RentalPeriod = ManagedRentalFrequency;

export function formatPropertyPrice(
  price: string,
  listingType: ListingType,
  rentalFrequency: RentalPeriod,
  locale: Locale,
  text: (key: MessageKey) => string,
): string {
  const formattedPrice = new Intl.NumberFormat(locale === 'am' ? 'am-ET' : 'en-ET', {
    maximumFractionDigits: 0,
  }).format(Number(price));
  const periodKey: Record<Exclude<RentalPeriod, ''>, MessageKey> = {
    daily: 'daily',
    weekly: 'weekly',
    monthly: 'monthly',
    yearly: 'yearly',
  };
  const period = listingType === 'rent' && rentalFrequency
    ? ` ${text(periodKey[rentalFrequency])}`
    : '';
  return `${text('ethiopianBirr')} ${formattedPrice}${period}`;
}

export function formatRegistrationDate(createdAt: string | null | undefined, locale: Locale): string | null {
  if (!createdAt) return null;
  const date = new Date(createdAt);
  if (Number.isNaN(date.getTime())) return null;
  return new Intl.DateTimeFormat(locale === 'am' ? 'am-ET' : 'en-ET', {
    dateStyle: 'medium',
  }).format(date);
}
