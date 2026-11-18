import config from '../../../frontend/src/config/cities.json';
export const CITY = config.cities[config.activeCity as keyof typeof config.cities];
// Public server address only. Provider keys and database credentials stay on FastAPI.
export const API_BASE = (process.env.EXPO_PUBLIC_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
export const CATEGORIES = {
  shop: { label: 'Shops', symbol: 'S', color: '#50ad91' },
  fuel: { label: 'Petrol', symbol: 'P', color: '#e4ab4e' },
  pharmacy: { label: 'Pharmacies', symbol: '+', color: '#b58bdc' },
  hospital: { label: 'Hospitals', symbol: 'H', color: '#df8091' },
  police: { label: 'Police', symbol: '◆', color: '#7ea9e0' },
} as const;
export type Category = keyof typeof CATEGORIES;
export const CATEGORY_KEYS = Object.keys(CATEGORIES) as Category[];
export function inCity(lat: number, lon: number) {
  const [w, s, e, n] = CITY.bounds;
  return lat >= s && lat <= n && lon >= w && lon <= e;
}
