import type { Feature, FeatureCollection, LineString, MultiLineString, Point } from 'geojson';
import { API_BASE, type Category } from './config';
export type Place = { id?: string; label: string; lat: number; lon: number };
export type Route = Feature<LineString | MultiLineString, { preference: string; distance: number; time: number }>;
export type Routes = FeatureCollection<LineString | MultiLineString, Route['properties']> & { partial?: boolean };
export type PlaceProperties = { id: string; kind: Category; name: string; address: string; opening_hours: string | null; distance_from_route_m: number };
export type Nearby = Feature<Point, PlaceProperties>;
export type Places = FeatureCollection<Point, PlaceProperties> & { unavailable_categories?: Category[]; truncated_categories?: Category[] };
export const EMPTY_PLACES: Places = { type: 'FeatureCollection', features: [] };
export async function api<T>(path: string, options: RequestInit = {}, signal?: AbortSignal): Promise<T> {
  const controller = new AbortController();
  const abort = () => controller.abort();
  if (signal?.aborted) controller.abort();
  signal?.addEventListener('abort', abort, { once: true });
  const timeout = setTimeout(abort, 45000);
  try {
    const response = await fetch(`${API_BASE}${path}`, { ...options, headers: { 'Content-Type': 'application/json', ...options.headers }, signal: controller.signal });
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'This request could not be completed.');
    return data;
  } catch (error) {
    if (signal?.aborted) throw error;
    if (controller.signal.aborted) throw new Error('Request timed out. Check your connection and retry.');
    if (error instanceof TypeError) throw new Error('Cannot reach SafePath. Check the backend address in App info.');
    throw error;
  } finally {
    clearTimeout(timeout);
    signal?.removeEventListener('abort', abort);
  }
}
export const post = (data: unknown): RequestInit => ({ method: 'POST', body: JSON.stringify(data) });
export function routeBounds(route: Route): [number, number, number, number] {
  const points = route.geometry.type === 'LineString' ? route.geometry.coordinates : route.geometry.coordinates.flat();
  const lons = points.map(p => p[0]), lats = points.map(p => p[1]);
  return [Math.min(...lons), Math.min(...lats), Math.max(...lons), Math.max(...lats)];
}
