'use client';
import dynamic from 'next/dynamic';
import { useEffect, useRef, useState } from 'react';
import type { FeatureCollection, Geometry } from 'geojson';
import LocationField, { Place } from '@/components/location-field';
import ActivitySummary from '@/components/activity-summary';
import AssessmentDetails, { AssessmentBadge } from '@/components/route-assessment';
import { compareAssessments } from '@/lib/assessment-comparison';
import { defaultDeparture, arrivalLabel, type ActivityEntry, ALL_CATEGORIES, PLACE_CATEGORIES, CategoryIcon, EMPTY_PLACES, type RoutePlaces, type PlaceCategory } from '@/lib/route-places';
const MapCanvas = dynamic(() => import('@/components/map-canvas'), { ssr: false, loading: () => <div className="map-loading">Preparing your map…</div> });
import { CITY } from '@/config/city';
const ORIGIN: Place = CITY.origin;
const DESTINATION: Place = CITY.destination;
const EMPTY: FeatureCollection<Geometry> = { type: 'FeatureCollection', features: [] };
const activityKey = (route: FeatureCollection<Geometry>['features'][number], departure: string) => JSON.stringify([route.geometry, route.properties?.time, departure]);

export default function Home() {
  const [panelOpen, setPanelOpen] = useState(true);
  const [section, setSection] = useState('directions');
  function openSection(id: string) {
    setPanelOpen(true); setSection(id);
    requestAnimationFrame(() => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
  }
  const [start, setStart] = useState<Place | null>(ORIGIN);
  const [end, setEnd] = useState<Place | null>(DESTINATION);
  const [routes, setRoutes] = useState<FeatureCollection<Geometry>>(EMPTY);
  const [selected, setSelected] = useState(0);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [evidence, setEvidence] = useState<FeatureCollection<Geometry>>(EMPTY);
  const [evidenceStatus, setEvidenceStatus] = useState('Loading cached evidence…');
  const [showLighting, setShowLighting] = useState(true);
  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/evidence', { signal: controller.signal }).then(async response => {
      if (!response.ok) throw new Error('Evidence unavailable');
      const data = await response.json();
      setEvidence(data);
      const lamps = data.features.filter((f: {properties: {kind: string}}) => f.properties.kind === 'street_lamp').length;
      setEvidenceStatus(lamps ? `${lamps} mapped streetlights in the pilot sample` : 'No mapped streetlights in this sample. Lighting conditions are unknown.');
    }).catch(() => { if (!controller.signal.aborted) setEvidenceStatus('Cached evidence is temporarily unavailable.'); });
    return () => controller.abort();
  }, []);
  const [departure, setDeparture] = useState('');
  useEffect(() => { setDeparture(defaultDeparture()); }, []);
  const departureISO = departure && Number.isFinite(Date.parse(`${departure}+05:30`)) && Number(departure.slice(0, 4)) >= 2020 && Number(departure.slice(0, 4)) <= 2100 ? `${departure}+05:30` : '';
  const [activities, setActivities] = useState<Record<number, ActivityEntry>>({});
  const [visibleCategories, setVisibleCategories] = useState<PlaceCategory[]>(ALL_CATEGORIES);
  const activityCache = useRef(new Map<string, { expires: number; data: RoutePlaces }>());
  const selectedRoute = routes.features[selected];
  const entryFor = (index: number) => {
    const route = routes.features[index], entry = activities[index];
    return route && entry?.key === activityKey(route, departureISO) ? entry : undefined;
  };
  const currentActivity = entryFor(selected);
  const places = currentActivity?.data || EMPTY_PLACES;
  const placesStatus = !selectedRoute ? 'Choose a route to see nearby places.' : !departureISO ? 'Choose a valid departure date and time.' : currentActivity?.error || (currentActivity?.data ? `${places.features.length} places within 100 m of this route` : 'Checking places and schedules at your arrival time…');
  const hasMappedLights = evidence.features.some(feature => feature.properties?.kind === 'street_lamp');
  useEffect(() => {
    if (!routes.features.length || !departureISO) return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      routes.features.forEach(async (route, index) => {
        const key = activityKey(route, departureISO);
        const cached = activityCache.current.get(key);
        if (cached && cached.expires > Date.now()) {
          setActivities(current => ({ ...current, [index]: { key, data: cached.data } })); return;
        }
        try {
          const response = await fetch('/api/route-activity', { method: 'POST', headers: { 'Content-Type': 'application/json' }, signal: controller.signal,
            body: JSON.stringify({ geometry: route.geometry, buffer_m: 100, departure_time: departureISO, duration_seconds: route.properties?.time }) });
          const data = await response.json();
          if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Activity could not be loaded. Check the departure time and retry.');
          if (controller.signal.aborted) return;
          setActivities(current => ({ ...current, [index]: { key, data } }));
          if (!data.unavailable_categories?.length) {
            if (activityCache.current.size >= 16) activityCache.current.clear();
            activityCache.current.set(key, { expires: Date.now() + 300000, data });
          }
        } catch (error) {
          if (!controller.signal.aborted) setActivities(current => ({ ...current, [index]: { key, error: error instanceof Error ? error.message : 'Activity unavailable.' } }));
        }
      });
    }, 300);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [routes, departureISO]);
  function toggleCategory(kind: PlaceCategory) {
    setVisibleCategories(current => current.includes(kind) ? current.filter(value => value !== kind) : [...current, kind]);
  }
  const change = (which: 'start' | 'end', value: Place | null) => { (which === 'start' ? setStart : setEnd)(value); setRoutes(EMPTY); setMessage(''); };
  async function findRoutes() {
    if (!start || !end) return;
    setBusy(true); setMessage(''); setRoutes(EMPTY); setActivities({});
    try {
      const response = await fetch('/api/routes', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ start: { lat: start.lat, lon: start.lon }, end: { lat: end.lat, lon: end.lon } }) });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Could not calculate this journey.');
      setRoutes(data); setSelected(0);
      if (data.partial) setMessage('One routing preference was unavailable. Showing the available result.');
    } catch (e) { setMessage(e instanceof Error ? e.message : 'Route service unavailable. Please retry.'); }
    finally { setBusy(false); }
  }
  return <div className={`app-shell ${panelOpen ? '' : 'panel-collapsed'}`}>
    <nav className="map-rail" aria-label="Main navigation">
      <a className="rail-brand" href="/" aria-label="SafePath home">↗</a>
      <div className="rail-links">
        <button className={section === 'directions' && panelOpen ? 'active' : ''} onClick={() => openSection('directions')} aria-label="Open directions"><span className="rail-icon">↱</span><span>Directions</span></button>
        <button className={section === 'nearby' && panelOpen ? 'active' : ''} onClick={() => openSection('nearby')} aria-label="Open nearby places"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true"><path d="M20 10c0 6-8 11-8 11S4 16 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/></svg><span>Nearby</span></button>
        <button className={section === 'evidence' && panelOpen ? 'active' : ''} onClick={() => openSection('evidence')} aria-label="Open safety evidence"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true"><path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6l8-3Z"/><path d="m8 12 3 3 5-6"/></svg><span>Evidence</span></button>
      </div>
      <span className="rail-bottom" title="SafePath pilot">SP</span>
    </nav>
    <main className="map-workspace" aria-label="SafePath route planner">
      <section className="map-panel" aria-label="Route map">
        <MapCanvas data={routes} selected={selected} evidence={evidence} showLighting={showLighting} places={places} visibleCategories={visibleCategories} panelOpen={panelOpen} assessment={places.assessment?.segments} />
        <div className="map-label"><span className="live-dot" /><div><strong>{CITY.name}</strong><small>Walking-route pilot</small></div></div>
        <div className="map-legend"><span><i className="green-line" />Selected route</span><span><i className="gray-line" />Other candidate</span>{places.assessment && <span><i className="section-band" />Section evidence band</span>}{showLighting && hasMappedLights && <span><i className="lamp-glow" />Mapped lighting</span>}</div>
      </section>
      <div className="map-category-bar" aria-label="Map place filters">{ALL_CATEGORIES.map(kind => {
        const meta = PLACE_CATEGORIES[kind];
        return <button key={kind} className={`map-category ${visibleCategories.includes(kind) ? 'active' : ''}`} onClick={() => toggleCategory(kind)} aria-pressed={visibleCategories.includes(kind)} aria-label={`${meta.label} markers`} style={{ '--category-color': meta.color } as React.CSSProperties}><CategoryIcon kind={kind} /><span>{meta.label}</span></button>;
      })}</div>
      {!panelOpen && <button className="open-panel" onClick={() => openSection('directions')} aria-label="Open directions panel"><span className="mini-brand">↗</span><span>Search a journey</span><span>⌕</span></button>}
      <aside id="journey-panel" className="journey-panel" aria-label="Journey planning" hidden={!panelOpen}>
        <header className="panel-header"><a className="brand" href="/" aria-label="SafePath home">Safe<span>Path</span><span className="brand-dot" /></a><button className="icon-button" onClick={() => setPanelOpen(false)} aria-label="Collapse directions panel" title="Collapse panel">‹</button></header>
        <div className="journey-scroll">
          <section id="directions" className="directions-section">
            <div className="panel-title"><div><h1>Where are you heading?</h1><p>Explore a little more of your route.</p></div><span className="walking-badge">Walking</span></div>
            <form onSubmit={e => { e.preventDefault(); findRoutes(); }}>
              <div className="locations"><div className="location-symbols" aria-hidden="true"><span className="origin-circle" /><i /><span className="destination-square" /></div><div className="location-fields"><LocationField label="STARTING POINT" initial={ORIGIN} onSelect={p => change('start', p)} /><LocationField label="DESTINATION" initial={DESTINATION} onSelect={p => change('end', p)} /></div></div>
              <div className="departure-field"><label htmlFor="departure-time">DEPARTURE · INDIA STANDARD TIME</label><input id="departure-time" aria-label="Departure time (IST)" type="datetime-local" value={departure} required min="2020-01-01T00:00" max="2100-12-31T23:59" onInput={e => setDeparture(e.currentTarget.value)} onChange={e => setDeparture(e.target.value)} /><small>Changing the time updates all route summaries.</small></div>
              <button className="primary-button" disabled={!start || !end || busy || !departureISO}>{busy ? 'Finding walking routes…' : 'Find walking routes'} <span>→</span></button>
            </form>
            {message && <p className="feedback" role="status">{message}</p>}
            <div className="pilot"><span /> {CITY.name.toUpperCase()} PILOT <span className="pilot-note">In development</span></div>
          </section>
          <section className="route-section" aria-label="Route options">
            <div className="routes-header"><h2>{routes.features.length ? 'Your route options' : 'A little more context'}</h2>{routes.features.length > 0 && <span>{routes.features.length} found</span>}</div>
            {routes.features.length > 0 && <div className="comparison-note" role="status">{routes.features.some((_, i) => !entryFor(i)?.data?.assessment && !entryFor(i)?.error) ? <><strong>Checking route evidence…</strong><p>Available routes remain selectable while indicators load.</p></> : (() => { const comparison = compareAssessments(routes.features.map((route, i) => ({ assessment: entryFor(i)?.data?.assessment, duration: Number(route.properties?.time) }))); return <><strong>{comparison.title}</strong><p>{comparison.detail}</p></>; })()}</div>}
            {routes.features.length ? <div className="route-options">{routes.features.map((route, i) => { const p = route.properties!; return <button type="button" key={i} className={`route-card ${selected === i ? 'selected' : ''}`} onClick={() => setSelected(i)} aria-pressed={selected === i}><div className="route-card-top"><span><span className="radio" />{p.preference === 'balanced' ? 'Balanced walking route' : 'Shortest-distance route'}</span></div><div className="route-numbers"><strong>{Math.round(Number(p.time) / 60)} <small>min</small></strong><span>{(Number(p.distance) / 1000).toFixed(2)} km</span><span className="route-arrow">↗</span></div><ActivitySummary entry={entryFor(i)} valid={!!departureISO} /><AssessmentBadge data={entryFor(i)?.data?.assessment} /></button>; })}<p className="route-note">Arrival times use average walking pace and exclude stops and access detours. Schedule estimates are not confirmed live availability. Options may overlap; these are not safety rankings.</p></div> : <div className="empty-state"><div className="empty-route-art" aria-hidden="true"><span>○</span><i /><span>◇</span></div><h3>Two places. A clearer picture.</h3><p>Find a walking route, then explore the shops and assistance points along the way.</p><div className="empty-tags"><span>Route comparison</span><span>Nearby places</span></div></div>}
          </section>
          <section id="nearby" className="route-places-panel" aria-label="Places along the selected route">
            <div className="places-heading"><h2>Along your route</h2><span>100 m corridor</span></div>
            <p className="places-status" role="status">{placesStatus}</p>
            {places.estimated_route_arrival && <p className="journey-arrival">Estimated journey arrival · {arrivalLabel(places.estimated_route_arrival)}</p>}
            {currentActivity?.data?.summary && <ActivitySummary entry={currentActivity} valid={!!departureISO} />}
            <div className="category-summary">{ALL_CATEGORIES.map(kind => { const meta = PLACE_CATEGORIES[kind]; const count = places.features.filter(f => f.properties.kind === kind).length; return <div key={kind}><i style={{ background: meta.color }}><CategoryIcon kind={kind} /></i><span>{meta.label}</span><strong>{count}</strong></div>; })}</div>
            {!!places.unavailable_categories?.length && <p className="places-warning">Could not load: {places.unavailable_categories.map(k => PLACE_CATEGORIES[k].label).join(', ')}. Counts are incomplete.</p>}
            {!!places.truncated_categories?.length && <p className="places-warning">Some categories reached the search limit. This is a partial listing.</p>}
            <small>Use the map filters to show or hide categories. Tap a pin for details. Listings do not confirm current opening or access.</small>
          </section>
          <section id="evidence" className="evidence-section"><div className="places-heading"><h2>Route evidence</h2><span className="evidence-status">Prototype</span></div><AssessmentDetails data={places.assessment} /><div className="places-heading lighting-heading"><h2>Lighting overlay</h2></div><div className="lighting-control"><label><input type="checkbox" checked={showLighting} onChange={e => setShowLighting(e.target.checked)} disabled={!hasMappedLights} /> Show lighting glow</label><p role="status">{evidenceStatus}</p><small>Glow follows road sections near mapped lamps. Its extent is illustrative; actual illumination and lamp operation are unverified.</small></div><div className="evidence-note"><span>ⓘ</span><p>These are prototype mapped-condition indicators, not a prediction of personal safety. Business schedules, streetlight operation and assistance access are unverified.</p></div></section>
          <footer>Geoapify · © OpenStreetMap contributors</footer>
        </div>
      </aside>
    </main>
  </div>;
}
