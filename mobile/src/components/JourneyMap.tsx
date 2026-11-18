import { useMemo, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { Map, Camera, GeoJSONSource, Layer } from '@maplibre/maplibre-react-native';
import type { FeatureCollection, Point } from 'geojson';
import { API_BASE, CITY, CATEGORIES, inCity, type Category } from '../lib/config';
import { routeBounds, type Route, type Places, type Nearby, type Place } from '../lib/api';
import { colors as c } from '../lib/theme';
type Props = { routes: Route[]; selected: number; places: Places; categories: Category[]; current: Place | null; onPlace: (place: Nearby) => void };
export default function JourneyMap({ routes, selected, places, categories, current, onPlace }: Props) {
  const [error, setError] = useState(false);
  const style = useMemo(() => ({ version: 8 as const, sources: { base: { type: 'raster' as const, tiles: [`${API_BASE}/api/map/tiles/{z}/{x}/{y}.png?style=dark-matter`], tileSize: 256, maxzoom: 19, attribution: '© OpenStreetMap contributors · Geoapify' } }, layers: [{ id: 'base', type: 'raster' as const, source: 'base' }] }), []);
  const active = routes[selected];
  const data: FeatureCollection = { type: 'FeatureCollection', features: routes.map((f, i) => ({ ...f, properties: { ...f.properties, selected: i === selected } })).sort((a, b) => Number(a.properties.selected) - Number(b.properties.selected)) };
  const filtered: Places = { ...places, features: places.features.filter(f => categories.includes(f.properties.kind)) };
  const position: FeatureCollection<Point> = { type: 'FeatureCollection', features: current ? [{ type: 'Feature', properties: {}, geometry: { type: 'Point', coordinates: [current.lon, current.lat] } }] : [] };
  return <View style={s.frame}>
    <Map style={s.map} mapStyle={style} onDidFailLoadingMap={() => setError(true)} onDidFinishLoadingMap={() => setError(false)}>
      <Camera key={active ? JSON.stringify(routeBounds(active)) : current ? `${current.lat},${current.lon}` : 'city'} initialViewState={active ? { bounds: routeBounds(active), padding: { top: 45, bottom: 45, left: 35, right: 35 } } : { center: current && inCity(current.lat, current.lon) ? [current.lon, current.lat] : [CITY.center[0], CITY.center[1]], zoom: current && inCity(current.lat, current.lon) ? 15 : 13.5 }} />
      <GeoJSONSource id="routes" data={data}>
        <Layer id="route-casing" type="line" paint={{ 'line-color': '#101216', 'line-width': 8 }} layout={{ 'line-cap': 'round', 'line-join': 'round' }} />
        <Layer id="route-lines" type="line" paint={{ 'line-color': ['case', ['get', 'selected'], c.mint, '#707b89'], 'line-width': ['case', ['get', 'selected'], 5, 3] }} layout={{ 'line-cap': 'round', 'line-join': 'round' }} />
      </GeoJSONSource>
      <GeoJSONSource id="places" data={filtered} onPress={event => { const id = event.nativeEvent.features[0]?.properties?.id; const place = places.features.find(f => f.properties.id === id); if (place) onPlace(place); }}>
        {Object.entries(CATEGORIES).map(([kind, meta]) => <Layer key={kind} id={`place-${kind}`} type="circle" filter={['==', ['get', 'kind'], kind]} paint={{ 'circle-color': meta.color, 'circle-radius': 7, 'circle-stroke-color': '#eef1f5', 'circle-stroke-width': 1.5 }} />)}
      </GeoJSONSource>
      <GeoJSONSource id="current" data={position}><Layer id="current-dot" type="circle" paint={{ 'circle-color': '#69b9ff', 'circle-radius': 7, 'circle-stroke-width': 3, 'circle-stroke-color': '#ffffff' }} /></GeoJSONSource>
    </Map>
    <View pointerEvents="none" style={s.badge}><Text style={s.badgeText}>●  {CITY.name} · Walking</Text></View>
    {error && <View style={s.error}><Text style={s.errorText}>Map unavailable. Check the backend connection. Route details remain below.</Text></View>}
  </View>;
}
const s = StyleSheet.create({ frame: { height: 340, borderRadius: 20, overflow: 'hidden', borderWidth: 1, borderColor: c.border, backgroundColor: c.panel }, map: { flex: 1 }, badge: { position: 'absolute', top: 14, left: 14, backgroundColor: '#1b2027ed', borderRadius: 10, padding: 10 }, badgeText: { color: c.mint, fontSize: 11, fontWeight: '600' }, error: { position: 'absolute', bottom: 34, left: 12, right: 12, padding: 10, borderRadius: 8, backgroundColor: c.panel }, errorText: { color: c.amber, fontSize: 12 } });
