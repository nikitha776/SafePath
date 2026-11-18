import type { FeatureCollection, Point } from 'geojson';
export const PLACE_CATEGORIES = {
  shop: { label: 'Shops', singular: 'Shop', color: '#217b68', icon: '<path d="M6 8h12l1 12H5L6 8Z"/><path d="M9 8V6a3 3 0 0 1 6 0v2"/>' },
  fuel: { label: 'Petrol bunks', singular: 'Petrol station', color: '#bd7918', icon: '<path d="M4 21V4h10v17M3 21h12M6 7h6v5H6zM14 10h2l2 2v6a2 2 0 0 0 4 0v-7l-4-4M20 9v4h2"/>' },
  pharmacy: { label: 'Pharmacies', singular: 'Pharmacy', color: '#8658b1', icon: '<path d="M9 3h6v6h6v6h-6v6H9v-6H3V9h6V3Z"/>' },
  hospital: { label: 'Hospitals', singular: 'Hospital', color: '#cc536b', icon: '<path d="M6 4v16M18 4v16M6 12h12" stroke-width="3"/>' },
  police: { label: 'Police stations', singular: 'Police station', color: '#386cac', icon: '<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6l8-3Z"/><path d="m8 12 3 3 5-6"/>' },
} as const;
export type PlaceCategory = keyof typeof PLACE_CATEGORIES;
export const ALL_CATEGORIES = Object.keys(PLACE_CATEGORIES) as PlaceCategory[];
export function CategoryIcon({ kind }: { kind: PlaceCategory }) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" dangerouslySetInnerHTML={{__html:PLACE_CATEGORIES[kind].icon}} />;
}
export type RoutePlaceProperties = { id: string; kind: PlaceCategory; name: string; address: string; opening_hours: string | null; distance_from_route_m: number; availability: string; schedule_status?: 'expected_open' | 'expected_closed' | 'hours_unknown'; schedule_reason?: string; estimated_arrival?: string; arrival_offset_seconds?: number };
export type RoutePlaces = FeatureCollection<Point, RoutePlaceProperties> & { unavailable_categories?: PlaceCategory[]; truncated_categories?: PlaceCategory[]; departure_time?: string; estimated_route_arrival?: string; arrival_method?: string; summary?: ActivitySummary; assessment?: RouteAssessment };
export const EMPTY_PLACES: RoutePlaces = { type: 'FeatureCollection', features: [] };

export type ActivityCounts = { expected_open: number; expected_closed: number; hours_unknown: number; total: number };
export type ActivitySummary = ActivityCounts & { businesses: ActivityCounts; schedule_coverage_percent: number | null };
export type ActivityEntry = { key: string; data?: RoutePlaces; error?: string };
export function arrivalLabel(value: string) {
  return new Intl.DateTimeFormat('en-IN', { timeZone: 'Asia/Kolkata', day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' }).format(new Date(value)) + ' IST';
}
export function defaultDeparture() {
  const parts = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kolkata', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).formatToParts(new Date());
  const part = (name: string) => parts.find(p => p.type === name)?.value;
  return `${part('year')}-${part('month')}-${part('day')}T${part('hour')}:${part('minute')}`;
}

export type AssessmentSection = { index: number; length_m: number; distance_from_start_m: number; estimated_arrival: string; concern: 'unknown' | 'more_concerns' | 'mixed' | 'fewer_concerns'; confidence_percent: number; reasons: string[] };
export type RouteAssessment = { rankable: boolean; concern_score: number | null; concern_label: string; confidence_percent: number; confidence_label: string; lighting_coverage_percent: number; road_coverage_percent: number; longest_mapped_support_gap_m: number; mapped_concern_length_m: number; reasons: string[]; method: string; notice: string; segments: FeatureCollection<import('geojson').LineString, AssessmentSection> };
