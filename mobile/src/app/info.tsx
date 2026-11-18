import { ScrollView, StyleSheet, Text } from 'react-native';
import { API_BASE, CITY } from '../lib/config';
import { colors as c } from '../lib/theme';
export default function Info() {
  return <ScrollView contentContainerStyle={s.body}>
    <Text style={s.title}>A clearer picture of your route.</Text>
    <Text style={s.text}>SafePath is a walking-route prototype for {CITY.name}. Routes are distance and time candidates. Safety ranking, turn-by-turn navigation, SOS and trusted-contact sharing are still in development.</Text>
    <Text style={s.heading}>Your location</Text><Text style={s.text}>Location permission is requested only when you tap “Use my location”. This version takes one position reading, displays it on the map, and uses it as your start if it is within the pilot area. It does not track you in the background or store journey history. Finding routes sends the selected endpoints to SafePath and Geoapify.</Text>
    <Text style={s.heading}>Evidence and uncertainty</Text><Text style={s.text}>Places are mapped listings. Scheduled opening hours, accessible entrances and current availability are unverified. Missing streetlight records mean unknown lighting, not darkness. Cached infrastructure does not confirm that a lamp works.</Text>
    <Text style={s.heading}>Mapping credits</Text><Text style={s.text}>© OpenStreetMap contributors (ODbL). Map tiles, location search, routes and place listings supplied through Geoapify.</Text>
    <Text style={s.heading}>Backend address</Text><Text selectable style={s.text}>{API_BASE}</Text><Text style={s.text}>For USB testing, forward port 8000 to your computer with ADB. See mobile/README.md for setup. API keys and database credentials stay on the backend.</Text>
  </ScrollView>;
}
const s = StyleSheet.create({ body: { padding: 24, paddingBottom: 50, gap: 16 }, title: { fontSize: 27, fontWeight: '700', color: c.text }, heading: { fontSize: 17, color: c.mint, fontWeight: '600', marginTop: 10 }, text: { color: c.muted, fontSize: 15, lineHeight: 24 } });
