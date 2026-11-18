import { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { api, type Place } from '../lib/api';
import { CITY } from '../lib/config';
import { colors as c } from '../lib/theme';
export default function LocationField({ label, value, onChange }: { label: string; value: Place | null; onChange: (p: Place | null) => void }) {
  const [query, setQuery] = useState(value?.label || '');
  const [results, setResults] = useState<Place[]>([]);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (value || query.trim().length < 3) return;
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      setBusy(true); setMessage('');
      try {
        const data = await api<{ results: Place[] }>(`/api/search?q=${encodeURIComponent(query.trim())}`, {}, controller.signal);
        if (controller.signal.aborted) return;
        setResults(data.results);
        setMessage(data.results.length ? '' : 'No precise match. Try a landmark or full address.');
      } catch (e) { if (!controller.signal.aborted) setMessage(e instanceof Error ? e.message : 'Search unavailable.'); }
      finally { if (!controller.signal.aborted) setBusy(false); }
    }, 450);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [query, value]);
  return <View style={s.wrap}>
    <Text style={s.label}>{label}</Text>
    <View style={s.inputRow}><TextInput accessibilityLabel={label} style={s.input} value={value?.label ?? query} placeholder={`Search ${CITY.name}`} placeholderTextColor={c.muted} autoCorrect={false} onChangeText={text => { setQuery(text); setResults([]); setMessage(''); setBusy(false); onChange(null); }} />{busy && !value && <ActivityIndicator color={c.mint} />}</View>
    {!value && results.map((place, i) => <Pressable accessibilityRole="button" key={place.id || i} style={s.result} onPress={() => { onChange(place); setQuery(place.label); setResults([]); setMessage(''); }}><Text style={s.text}>{place.label}</Text></Pressable>)}
    {!value && !!message && <Text accessibilityLiveRegion="polite" style={s.note}>{message}</Text>}
  </View>;
}
const s = StyleSheet.create({ wrap: { marginBottom: 14 }, label: { color: c.muted, fontSize: 10, fontWeight: '700', letterSpacing: 1.5, marginBottom: 7 }, inputRow: { flexDirection: 'row', borderWidth: 1, borderColor: c.border, borderRadius: 12, backgroundColor: c.background, paddingRight: 10 }, input: { color: c.text, padding: 13, fontSize: 14, flex: 1, minHeight: 48 }, result: { padding: 14, backgroundColor: c.raised, borderBottomWidth: 1, borderColor: c.border }, text: { color: c.text, fontSize: 13 }, note: { color: c.amber, fontSize: 12, marginTop: 7 } });
