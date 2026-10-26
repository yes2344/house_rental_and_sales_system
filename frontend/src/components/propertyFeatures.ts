export const PROPERTY_FACILITIES = [
  'Hot Water',
  'Balcony',
  '24-hour Electricity',
  'Dining Area',
  'Air Conditioning',
  'Appliances',
  'Backup Generator',
  'CCTV',
  'Electricity Backup',
  'Elevator / Lift',
  'Emergency Exits',
  'Firefighting Equipment',
  'TV',
  'En Suite Bathroom',
  'Wi-Fi',
  'Wardrobe',
  'Fitted Kitchen',
] as const;

export interface ParsedPropertyFeatures {
  facilities: string[];
  additional: string;
}

const facilitySet = new Set<string>(PROPERTY_FACILITIES);

export function parsePropertyFeatures(features: string): ParsedPropertyFeatures {
  const facilities: string[] = [];
  const additional: string[] = [];

  for (const line of features.split(/\r?\n/)) {
    const trimmedLine = line.trim();
    if (facilitySet.has(trimmedLine)) {
      facilities.push(trimmedLine);
    } else if (line.trim()) {
      additional.push(line);
    }
  }

  return { facilities, additional: additional.join('\n').trim() };
}

export function formatPropertyFeatures(facilities: string[], additional: string): string {
  const selectedFacilities = PROPERTY_FACILITIES.filter((facility) => facilities.includes(facility));
  const additionalText = additional.trim();
  return [...selectedFacilities, ...(additionalText ? [additionalText] : [])].join('\n');
}
