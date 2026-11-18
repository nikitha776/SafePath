'use client';
import { CITY } from '@/config/city';
import { lightingPaths } from '@/lib/lighting';
import { useEffect, useRef, useState } from 'react';
import * as maplibregl from 'maplibre-gl';
import type { Map, GeoJSONSource } from 'maplibre-gl';
import type { FeatureCollection, Geometry } from 'geojson';
import { arrivalLabel, PLACE_CATEGORIES, type PlaceCategory, type RoutePlaces } from '@/lib/route-places';

// Keep DOM marker sizes independent of MapLibre's positioning transform.
function markerScale(zoom: number) {
  return Math.max(0.3, Math.min(1, 2 ** ((zoom - 18) / 3)));
}

export default function MapCanvas({ data, selected, evidence, showLighting, places, visibleCategories, panelOpen, assessment }: { data: FeatureCollection<Geometry>; selected: number; evidence: FeatureCollection<Geometry>; showLighting: boolean; places: RoutePlaces; visibleCategories: PlaceCategory[]; panelOpen: boolean; assessment?: FeatureCollection<Geometry> }) {
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<Map | null>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    if (!container.current) return;
    setReady(false);
    maplibregl.setWorkerUrl('/maplibre/maplibre-gl-worker.mjs');
    let instance: Map;
    try {
      instance = new maplibregl.Map({ container: container.current, center: [CITY.center[0], CITY.center[1]], zoom: 14.5,
        style: { version: 8, sources: { base: { type: 'raster', tiles: [`${window.location.origin}/api/map/tiles/{z}/{x}/{y}.png?style=dark-matter`], tileSize: 256, maxzoom: 19, attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors · <a href="https://www.geoapify.com/">Geoapify</a>' } }, layers: [{ id: 'base', type: 'raster', source: 'base' }] } });
    } catch { setError('Your browser could not initialize the map. Route details are still available.'); return; }
    map.current = instance;
    instance.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-right');
    instance.on('error', () => setError('Some map data could not load. Check that the backend is running.'));
    instance.on('load', () => {
      instance.addSource('routes', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
      instance.addLayer({ id: 'route-casing', type: 'line', source: 'routes', paint: { 'line-color': '#10171b', 'line-width': 9 }, layout: { 'line-cap': 'round', 'line-join': 'round' } });
      instance.addLayer({ id: 'route-lines', type: 'line', source: 'routes', paint: { 'line-color': ['case', ['get', 'selected'], '#76bda7', '#697382'], 'line-width': ['case', ['get', 'selected'], 6, 4] }, layout: { 'line-cap': 'round', 'line-join': 'round' } });
      instance.addSource('lighting', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
      // Layered, road-following glow. This is a visual proxy for mapped lamp proximity.
      for (const layer of [
        { id: 'lighting-halo', width: [4, 10, 22, 44], blur: 7, opacity: 0.11 },
        { id: 'lighting-glow', width: [2, 5, 12, 24], blur: 3, opacity: 0.18 },
        { id: 'lighting-core', width: [1, 2, 4, 8], blur: 1, opacity: 0.28 },
      ]) {
        instance.addLayer({ id: layer.id, type: 'line', source: 'lighting', layout: { 'line-cap': 'round', 'line-join': 'round' },
          paint: { 'line-color': '#c7b582', 'line-width': ['interpolate', ['linear'], ['zoom'], 12, layer.width[0], 14, layer.width[1], 16, layer.width[2], 18, layer.width[3]], 'line-blur': layer.blur, 'line-opacity': layer.opacity },
        }, 'route-casing');
      }
      instance.addSource('section-evidence', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
      instance.addLayer({ id: 'section-evidence-band', type: 'line', source: 'section-evidence', layout: { 'line-cap': 'round', 'line-join': 'round' }, paint: {
        'line-color': ['match', ['get', 'concern'], 'more_concerns', '#d6a178', 'fewer_concerns', '#82b9a0', 'mixed', '#c1b17f', '#8795a5'],
        'line-width': ['interpolate', ['linear'], ['zoom'], 12, 10, 16, 14, 18, 18], 'line-opacity': 0.6, 'line-dasharray': [2, 2],
      } }, 'route-casing');
      setReady(true);
    });
    return () => { instance.remove(); map.current = null; };
  }, []);
  useEffect(() => {
    if (!ready || !map.current?.getSource('section-evidence')) return;
    (map.current.getSource('section-evidence') as GeoJSONSource).setData(assessment || { type: 'FeatureCollection', features: [] });
  }, [assessment, ready]);
  useEffect(() => {
    const instance = map.current;
    if (!ready || !instance || !instance.getSource('routes')) return;
    const enriched: FeatureCollection<Geometry> = { ...data, features: data.features.map((f, i) => ({ ...f, properties: { ...f.properties, selected: i === selected } })).sort((a, b) => Number(a.properties.selected) - Number(b.properties.selected)) };
    (instance.getSource('routes') as GeoJSONSource).setData(enriched);
    const feature = data.features[selected];
    if (!feature) return;
    const coordinates = feature.geometry.type === 'MultiLineString' ? feature.geometry.coordinates.flat() : feature.geometry.type === 'LineString' ? feature.geometry.coordinates : [];
    if (coordinates.length) {
      const bounds = new maplibregl.LngLatBounds();
      coordinates.forEach(p => bounds.extend([p[0], p[1]]));
      function fitRoute() {
        const mobile = window.innerWidth <= 700;
        const padding = mobile ? { top: Math.min(165, window.innerHeight * .2), right: 40, bottom: panelOpen ? Math.min(window.innerHeight * .49 + 35, 460) : Math.min(100, window.innerHeight * .2), left: 40 } : { top: 110, right: 80, bottom: 100, left: panelOpen ? (window.innerWidth >= 1600 ? 450 : 420) : 80 };
        instance!.resize();
        instance!.fitBounds(bounds, { padding, maxZoom: 16, duration: 500 });
      }
      fitRoute();
      window.addEventListener('resize', fitRoute);
      return () => window.removeEventListener('resize', fitRoute);
    }
  }, [data, selected, ready, panelOpen]);
  useEffect(() => {
    if (!ready || !map.current || !map.current.getSource('lighting')) return;
    (map.current.getSource('lighting') as GeoJSONSource).setData(lightingPaths(evidence));
    for (const id of ['lighting-halo', 'lighting-glow', 'lighting-core']) {
      map.current.setLayoutProperty(id, 'visibility', showLighting ? 'visible' : 'none');
    }
  }, [evidence, showLighting, ready]);
  useEffect(() => {
    const instance = map.current;
    if (!ready || !instance || !instance.getSource('routes')) return;
    const markers: maplibregl.Marker[] = [];
    const positioned: { element: HTMLButtonElement; coordinates: [number, number]; priority: number; popup: maplibregl.Popup }[] = [];
    const priorities = { police: 0, hospital: 1, pharmacy: 2, fuel: 3, shop: 4 };
    const popups: maplibregl.Popup[] = [];
    for (const feature of places.features) {
      const p = feature.properties;
      if (!visibleCategories.includes(p.kind) || !(p.kind in PLACE_CATEGORIES)) continue;
      const meta = PLACE_CATEGORIES[p.kind];
      const element = document.createElement('button');
      element.type = 'button';
      element.className = 'place-marker';
      element.style.setProperty('--pin-color', meta.color);
      element.setAttribute('aria-label', `${meta.singular}: ${p.name}`);
      element.title = `${meta.singular} · ${p.name}`;
      // Icon markup is an internal constant; provider text only uses textContent below.
      element.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${meta.icon}</svg>`;
      const content = document.createElement('div');
      content.className = 'place-popup';
      const tag = document.createElement('div'); tag.className = 'place-popup-category'; tag.style.color = meta.color; tag.textContent = meta.singular;
      const name = document.createElement('h3'); name.textContent = p.name;
      const address = document.createElement('p'); address.textContent = p.address;
      const distance = document.createElement('p'); distance.textContent = `About ${p.distance_from_route_m} m from the route (straight-line)`;
      const hours = document.createElement('p'); hours.textContent = p.opening_hours ? `Scheduled hours: ${p.opening_hours}` : 'Opening hours unknown';
      const note = document.createElement('small'); note.textContent = 'Mapped listing · availability and accessible entrance unverified.';
      content.append(tag, name, address, distance, hours);
      if (p.estimated_arrival) {
        const arrival = document.createElement('p'); arrival.textContent = `Estimated arrival nearby: ${arrivalLabel(p.estimated_arrival)}`;
        const status = document.createElement('div'); status.className = `schedule-badge ${p.schedule_status || 'hours_unknown'}`;
        status.textContent = p.schedule_status === 'expected_open' ? 'Expected open at arrival' : p.schedule_status === 'expected_closed' ? 'Expected closed at arrival' : 'Hours unknown at arrival';
        const reason = document.createElement('p'); reason.textContent = p.schedule_reason || 'Schedule information is unavailable.';
        content.append(arrival, status, reason);
      }
      content.append(note);
      const popup = new maplibregl.Popup({ offset: 16, maxWidth: '280px' }).setDOMContent(content);
      popups.push(popup);
      const marker = new maplibregl.Marker({ element, anchor: 'bottom', offset: [0, -2] }).setLngLat([feature.geometry.coordinates[0], feature.geometry.coordinates[1]]).setPopup(popup).addTo(instance);
      markers.push(marker);
      positioned.push({ element, coordinates: [feature.geometry.coordinates[0], feature.geometry.coordinates[1]], priority: priorities[p.kind], popup });
    }
    // Declutter screen-space collisions without shifting real place coordinates.
    // All results remain available as the map zooms or the category filters change.
    function layoutMarkers() {
      const scale = markerScale(instance!.getZoom());
      const compact = scale < 0.5;
      const occupied: { x: number; y: number }[] = [];
      const { clientWidth: width, clientHeight: height } = instance!.getContainer();
      for (const item of [...positioned].sort((a, b) => a.priority - b.priority)) {
        item.element.style.setProperty('--marker-scale', String(scale));
        item.element.dataset.compact = String(compact);
        item.popup.setOffset(Math.round(12 * scale));
        const point = instance!.project(item.coordinates);
        const outside = point.x < 0 || point.y < 0 || point.x > width || point.y > height;
        const overlaps = occupied.some(other => Math.abs(other.x - point.x) < 18 * scale + 6 && Math.abs(other.y - point.y) < (compact ? 18 : 21) * scale + 6);
        item.element.style.display = outside || overlaps ? 'none' : 'grid';
        item.element.style.zIndex = String(10 - item.priority);
        if (!outside && !overlaps) occupied.push(point);
      }
    }
    layoutMarkers();
    instance.on('moveend', layoutMarkers);
    instance.on('zoom', layoutMarkers);
    return () => { instance.off('moveend', layoutMarkers); instance.off('zoom', layoutMarkers); markers.forEach(marker => marker.remove()); popups.forEach(popup => popup.remove()); };
  }, [places, visibleCategories, ready]);
  useEffect(() => {
    const instance = map.current;
    if (!ready || !instance) return;
    const route = data.features[selected];
    const points = route?.geometry.type === 'MultiLineString' ? route.geometry.coordinates.flat() : route?.geometry.type === 'LineString' ? route.geometry.coordinates : [];
    if (!points.length) return;
    const markers = [points[0], points[points.length - 1]].map((point, i) => {
      const element = document.createElement('div');
      element.className = `route-endpoint ${i ? 'destination' : 'origin'}`;
      element.textContent = i ? 'B' : 'A';
      element.setAttribute('aria-label', i ? 'Route destination' : 'Route start');
      return new maplibregl.Marker({ element }).setLngLat([point[0], point[1]]).addTo(instance);
    });
    function resizeEndpoints() {
      const scale = Math.max(0.5, markerScale(instance!.getZoom()));
      markers.forEach(marker => marker.getElement().style.setProperty('--marker-scale', String(scale)));
    }
    resizeEndpoints();
    instance.on('zoom', resizeEndpoints);
    return () => { instance.off('zoom', resizeEndpoints); markers.forEach(marker => marker.remove()); };
  }, [data, selected, ready]);
  return <><div className="map-surface" ref={container} aria-label={`Interactive ${CITY.name} walking-route map`} />{error && <div className="map-error" role="status">{error}</div>}</>;
}
