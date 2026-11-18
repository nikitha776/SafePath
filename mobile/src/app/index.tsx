import { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Alert, Keyboard, Modal, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Link } from 'expo-router';
import * as Location from 'expo-location';
import JourneyMap from '../components/JourneyMap';
import LocationField from '../components/LocationField';
import { api, post, EMPTY_PLACES, type Place, type Routes, type Route, type Places, type Nearby } from '../lib/api';
import { CITY, CATEGORIES, CATEGORY_KEYS, inCity, type Category } from '../lib/config';
import { colors as c } from '../lib/theme';
export default function Home() {
  const [start, setStart] = useState<Place | null>(CITY.origin);
  const [end, setEnd] = useState<Place | null>(CITY.destination);
  const [current, setCurrent] = useState<Place | null>(null);
  const [locating, setLocating] = useState(false);
  const [routes, setRoutes] = useState<Route[]>([]);
  const [selected, setSelected] = useState(0);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [nearby, setNearby] = useState<{ route: Route; data: Places; status: string } | null>(null);
  const [categories, setCategories] = useState<Category[]>(CATEGORY_KEYS);
  const [detail, setDetail] = useState<Nearby | null>(null);
  const [evidence, setEvidence] = useState('Loading cached lighting evidence…');
  const request = useRef<AbortController | null>(null);
  const mounted = useRef(true);
  const active = routes[selected];
  const places = active && nearby?.route === active ? nearby.data : EMPTY_PLACES;
  const placeStatus = !active ? 'Choose a route to find nearby places.' : nearby?.route === active ? nearby.status : 'Finding places within 100 m of this route…';
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; request.current?.abort(); }; }, []);
  useEffect(() => {
    const controller = new AbortController();
    api<{ features: { properties: { kind: string } }[]; truncated: boolean }>('/api/evidence', {}, controller.signal).then(data => {
      if (controller.signal.aborted) return;
      const count = data.features.filter(f => f.properties.kind === 'street_lamp').length;
      setEvidence(count ? `${count} mapped lamps in the cached sample${data.truncated ? ' (partial)' : ''}. Current operation is unverified.` : 'No mapped streetlights in this sample. Lighting conditions are unknown.');
    }).catch(() => { if (!controller.signal.aborted) setEvidence('Lighting evidence unavailable. Conditions are unknown.'); });
    return () => controller.abort();
  }, []);
  useEffect(() => {
    if (!active) return;
    const controller = new AbortController();
    api<Places>('/api/route-places', post({ geometry: active.geometry, buffer_m: 100 }), controller.signal).then(data => {
      if (controller.signal.aborted) return;
      setNearby({ route: active, data, status: `${data.features.length} mapped ${data.features.length === 1 ? 'place' : 'places'} within 100 m of this route` });
    }).catch(e => { if (!controller.signal.aborted) setNearby({ route: active, data: EMPTY_PLACES, status: e instanceof Error ? e.message : 'Nearby places unavailable.' }); });
    return () => controller.abort();
  }, [active]);
  function change(which: 'start' | 'end', place: Place | null) {
    request.current?.abort(); setDetail(null); setBusy(false); setRoutes([]); setSelected(0); setMessage('');
    (which === 'start' ? setStart : setEnd)(place);
  }
  async function findRoutes() {
    if (!start || !end) return;
    Keyboard.dismiss(); request.current?.abort(); const controller = new AbortController(); request.current = controller;
    setBusy(true); setRoutes([]); setMessage('');
    try {
      const data = await api<Routes>('/api/routes', post({ start: { lat: start.lat, lon: start.lon }, end: { lat: end.lat, lon: end.lon } }), controller.signal);
      if (controller.signal.aborted) return;
      setRoutes(data.features); setSelected(0);
      if (data.partial) setMessage('One route preference was unavailable. Showing available options.');
    } catch (e) { if (!controller.signal.aborted) setMessage(e instanceof Error ? e.message : 'Could not find routes.'); }
    finally { if (!controller.signal.aborted) setBusy(false); }
  }
  async function locate() {
    setLocating(true);
    try {
      const permission = await Location.requestForegroundPermissionsAsync();
      if (permission.status !== 'granted') { Alert.alert('Location permission', 'Permission was not granted. You can still search for your starting point.'); return; }
      if (!await Location.hasServicesEnabledAsync()) { Alert.alert('Location is off', 'Enable device location or enter a starting point manually.'); return; }
      const result = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
      if (!mounted.current) return;
      const point: Place = { label: 'My current location', lat: result.coords.latitude, lon: result.coords.longitude };
      setCurrent(point);
      if (inCity(point.lat, point.lon)) change('start', point);
      else Alert.alert('Outside the pilot area', `Your location is outside ${CITY.name}. Choose a starting point within the pilot area to find routes.`);
    } catch { if (mounted.current) Alert.alert('Location unavailable', 'Could not read your location. Try again outdoors or search for a starting point.'); }
    finally { if (mounted.current) setLocating(false); }
  }
  return <SafeAreaView style={s.safe} edges={['top', 'left', 'right']}>
    <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={s.body}>
      <View style={s.header}><View style={s.brandRow}><View style={s.logo}><Text style={s.logoText}>↗</Text></View><Text style={s.brand}>SafePath</Text></View><Link href="/info" accessibilityLabel="App info" style={s.info}>ⓘ</Link></View>
      <Text style={s.eyebrow}>●  {CITY.name.toUpperCase()} PILOT</Text>
      <Text style={s.title}>Know your way.{`\n`}Understand your route.</Text>
      <Text style={s.subtitle}>A little more context for your next walk.</Text>
      <JourneyMap routes={routes} selected={selected} places={places} categories={categories} current={current} onPlace={setDetail} />
      <View style={s.panel}>
        <Text style={s.heading}>Plan a journey</Text>
        <LocationField label="STARTING POINT" value={start} onChange={p => change('start', p)} />
        <Pressable accessibilityRole="button" style={s.location} disabled={locating} onPress={locate}>{locating ? <ActivityIndicator color={c.mint} /> : <Text style={s.locationText}>◎  Use my location</Text>}</Pressable>
        <Text style={s.small}>One position reading. No background tracking.</Text>
        <LocationField label="DESTINATION" value={end} onChange={p => change('end', p)} />
        <Pressable accessibilityRole="button" accessibilityState={{ disabled: !start || !end || busy }} disabled={!start || !end || busy} style={[s.primary, (!start || !end || busy) && s.disabled]} onPress={findRoutes}>{busy ? <ActivityIndicator color={c.background} /> : <Text style={s.primaryText}>Find walking routes  →</Text>}</Pressable>
        {!!message && <Text accessibilityLiveRegion="polite" style={s.warning}>{message}</Text>}
      </View>
      {!!routes.length && <View style={s.section}><Text style={s.heading}>Your route options</Text>{routes.map((route, i) => <Pressable key={i} accessibilityRole="radio" accessibilityState={{ checked: selected === i }} onPress={() => setSelected(i)} style={[s.route, selected === i && s.routeSelected]}><Text style={s.routeName}>{selected === i ? '◉' : '○'}  {route.properties.preference === 'balanced' ? 'Balanced walking route' : 'Shortest-distance route'}</Text><View style={s.numbers}><Text style={s.minutes}>{Math.round(route.properties.time / 60)} <Text style={s.unit}>min</Text></Text><Text style={s.distance}>{(route.properties.distance / 1000).toFixed(2)} km</Text></View><Text style={s.small}>Safety assessment pending</Text></Pressable>)}<Text style={s.small}>Options may overlap. These are routing preferences, not safety rankings.</Text></View>}
      <View style={s.panel}><Text style={s.heading}>Along your route</Text><Text accessibilityLiveRegion="polite" style={s.note}>{placeStatus}</Text><View style={s.filters}>{CATEGORY_KEYS.map(kind => { const meta = CATEGORIES[kind], enabled = categories.includes(kind); return <Pressable key={kind} accessibilityRole="checkbox" accessibilityLabel={`${meta.label} markers`} accessibilityState={{ checked: enabled }} style={[s.chip, enabled && { borderColor: meta.color }]} onPress={() => setCategories(values => enabled ? values.filter(v => v !== kind) : [...values, kind])}><View style={[s.dot, { backgroundColor: enabled ? meta.color : c.muted }]} /><Text style={s.chipText}>{meta.label} {places.features.filter(p => p.properties.kind === kind).length}</Text></Pressable>; })}</View>
      {!!places.unavailable_categories?.length && <Text style={s.warning}>Could not load: {places.unavailable_categories.map(k => CATEGORIES[k].label).join(', ')}. Counts are incomplete.</Text>}
      {!!places.truncated_categories?.length && <Text style={s.warning}>Some categories reached the search limit. Results are partial.</Text>}
      <Text style={s.small}>Tap a coloured map marker or a listing for details. Listings do not confirm current opening or access.</Text>
      {places.features.filter(f => categories.includes(f.properties.kind)).map(place => <Pressable accessibilityRole="button" key={place.properties.id} onPress={() => setDetail(place)} style={s.listing}><View style={[s.dot, { backgroundColor: CATEGORIES[place.properties.kind].color }]} /><Text numberOfLines={2} style={s.listingName}>{place.properties.name}</Text><Text style={s.small}>{place.properties.distance_from_route_m} m</Text></Pressable>)}
      </View>
      <View style={s.panel}><Text style={s.heading}>Lighting evidence</Text><Text style={s.note}>{evidence}</Text><Text style={s.small}>Cached OpenStreetMap infrastructure covers a small sample, not the whole city. No route is currently assessed for safety.</Text></View>
      <Text style={s.footer}>Geoapify · © OpenStreetMap contributors</Text>
    </ScrollView>
    <Modal visible={!!detail} transparent animationType="slide" onRequestClose={() => setDetail(null)}><View style={s.modalBackdrop}><View style={s.modal}><ScrollView>{detail && <><Text style={[s.eyebrow, { color: CATEGORIES[detail.properties.kind].color }]}>{CATEGORIES[detail.properties.kind].label}</Text><Text style={s.modalTitle}>{detail.properties.name}</Text><Text style={s.note}>{detail.properties.address || 'Address unavailable'}</Text><Text style={s.note}>About {detail.properties.distance_from_route_m} m from the route (straight-line).</Text><Text style={s.note}>{detail.properties.opening_hours ? `Scheduled hours: ${detail.properties.opening_hours}` : 'Opening hours unknown'}</Text><Text style={s.small}>Mapped listing. Current availability and accessible entrance are unverified.</Text></>}</ScrollView><Pressable accessibilityRole="button" style={s.primary} onPress={() => setDetail(null)}><Text style={s.primaryText}>Close details</Text></Pressable></View></View></Modal>
  </SafeAreaView>;
}
const s = StyleSheet.create({
  safe: { flex: 1, backgroundColor: c.background }, body: { padding: 20, paddingBottom: 44, gap: 18 }, header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }, brandRow: { flexDirection: 'row', gap: 10, alignItems: 'center' }, logo: { backgroundColor: '#d8dde5', borderRadius: 12, width: 36, height: 36, alignItems: 'center', justifyContent: 'center' }, logoText: { color: c.background, fontSize: 25 }, brand: { color: c.text, fontSize: 24, fontWeight: '700', letterSpacing: -1 }, info: { fontSize: 24, color: c.muted, padding: 10 }, eyebrow: { fontSize: 10, letterSpacing: 2, color: c.mint, fontWeight: '600' }, title: { fontSize: 29, lineHeight: 36, fontWeight: '700', letterSpacing: -1, color: c.text }, subtitle: { color: c.muted, fontSize: 14, marginTop: -8 }, panel: { backgroundColor: c.panel, borderWidth: 1, borderColor: c.border, padding: 18, borderRadius: 20, gap: 10 }, heading: { color: c.text, fontSize: 18, fontWeight: '600', marginBottom: 5 }, primary: { backgroundColor: '#dce1e9', padding: 16, borderRadius: 12, alignItems: 'center', minHeight: 50, justifyContent: 'center' }, primaryText: { color: c.background, fontSize: 15, fontWeight: '700' }, disabled: { opacity: .45 }, location: { paddingVertical: 8, minHeight: 44, justifyContent: 'center', marginTop: -12 }, locationText: { color: c.mint, fontSize: 13, fontWeight: '600' }, small: { color: c.muted, fontSize: 11, lineHeight: 17 }, warning: { color: c.amber, fontSize: 12, lineHeight: 19 }, section: { gap: 12 }, route: { borderRadius: 15, padding: 17, borderWidth: 1, borderColor: c.border, backgroundColor: c.panel, gap: 10 }, routeSelected: { borderColor: c.mint, backgroundColor: '#26342f' }, routeName: { color: c.text, fontSize: 13, fontWeight: '600' }, numbers: { flexDirection: 'row', gap: 20, alignItems: 'baseline' }, minutes: { color: c.text, fontSize: 29, fontWeight: '600' }, unit: { fontSize: 13, color: c.muted }, distance: { color: c.muted, fontSize: 14 }, note: { fontSize: 13, lineHeight: 21, color: c.muted }, filters: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 }, chip: { minHeight: 44, borderWidth: 1, borderColor: c.border, padding: 10, borderRadius: 10, flexDirection: 'row', alignItems: 'center', gap: 7 }, chipText: { color: c.text, fontSize: 12 }, dot: { width: 10, height: 10, borderRadius: 5 }, listing: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingVertical: 14, borderTopWidth: 1, borderColor: c.border }, listingName: { color: c.text, flex: 1, fontSize: 13 }, footer: { color: c.muted, fontSize: 10, textAlign: 'center' }, modalBackdrop: { flex: 1, backgroundColor: '#00000099', justifyContent: 'flex-end' }, modal: { backgroundColor: c.panel, padding: 26, paddingBottom: 40, borderTopLeftRadius: 24, borderTopRightRadius: 24, maxHeight: '75%', gap: 24 }, modalTitle: { color: c.text, fontSize: 24, fontWeight: '700', marginVertical: 14 }
});
