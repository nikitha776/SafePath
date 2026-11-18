'use client';
import { useEffect, useState } from 'react';
import { CITY } from '@/config/city';
export type Place = { id?: string; label: string; lat: number; lon: number };
export default function LocationField({ label, initial, onSelect }: { label: string; initial: Place; onSelect: (p: Place | null) => void }) {
  const [query, setQuery] = useState(initial.label);
  const [chosen, setChosen] = useState(true);
  const [results, setResults] = useState<Place[]>([]);
  const [status, setStatus] = useState('');
  useEffect(() => {
    if (chosen || query.trim().length < 3) return;
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      setStatus(`Searching ${CITY.name}…`);
      try {
        const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`, { signal: controller.signal });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Search unavailable.');
        setResults(data.results);
        setStatus(data.results.length ? '' : 'No precise match. Try a landmark or full address.');
      } catch (e) { if (!controller.signal.aborted) setStatus(e instanceof Error ? e.message : 'Search unavailable.'); }
    }, 450);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [query, chosen]);
  return <div className="location-field"><label>{label}<input value={query} onChange={e => { setQuery(e.target.value); setChosen(false); setResults([]); setStatus(''); onSelect(null); }} autoComplete="off" placeholder={`Search a ${CITY.name} location`} /></label>
    {!chosen && results.length > 0 && <ul className="search-results" aria-label={`${label} search results`}>{results.map((place, i) => <li key={place.id || i}><button type="button" onClick={() => { setQuery(place.label); setChosen(true); setResults([]); setStatus(''); onSelect(place); }}>{place.label}</button></li>)}</ul>}
    {!chosen && status && <small role="status">{status}</small>}
  </div>;
}
