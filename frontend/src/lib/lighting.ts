import type { FeatureCollection, Geometry, LineString, Position } from 'geojson';

type Road = { points: Position[]; meters: [number, number][]; lengths: number[]; total: number; intervals: [number, number][]; unlit: boolean };
const RADIUS = 20; // Display extent along the mapped road, not a measured light throw.

/** Draw only short sections of mapped roads close to lamps; never join lamp points across blocks. */
export function lightingPaths(evidence: FeatureCollection<Geometry>): FeatureCollection<LineString> {
  const lamps = evidence.features.filter(f => f.properties?.kind === 'street_lamp' && f.geometry.type === 'Point');
  const latitude = lamps.length && lamps[0].geometry.type === 'Point' ? lamps[0].geometry.coordinates[1] : 0;
  const xScale = 111320 * Math.cos(latitude * Math.PI / 180);
  const project = (p: Position): [number, number] => [p[0] * xScale, p[1] * 111320];
  const roads: Road[] = [];
  for (const feature of evidence.features) {
    if (feature.properties?.kind !== 'road') continue;
    const lines = feature.geometry.type === 'LineString' ? [feature.geometry.coordinates] : feature.geometry.type === 'MultiLineString' ? feature.geometry.coordinates : [];
    for (const points of lines) {
      if (points.length < 2) continue;
      const meters = points.map(project), lengths = [0];
      for (let i = 1; i < meters.length; i++) lengths.push(lengths[i - 1] + Math.hypot(meters[i][0] - meters[i - 1][0], meters[i][1] - meters[i - 1][1]));
      roads.push({ points, meters, lengths, total: lengths.at(-1)!, intervals: [], unlit: feature.properties?.lit === 'no' });
    }
  }
  for (const lamp of lamps) {
    if (lamp.geometry.type !== 'Point') continue;
    const [x, y] = project(lamp.geometry.coordinates);
    let match: { road: Road; along: number } | undefined;
    let closest = 15; // Reject lamps too far from any cached road centerline.
    for (const road of roads) {
      for (let i = 1; i < road.meters.length; i++) {
        const [ax, ay] = road.meters[i - 1], [bx, by] = road.meters[i];
        const dx = bx - ax, dy = by - ay, squared = dx * dx + dy * dy;
        if (!squared) continue;
        const t = Math.max(0, Math.min(1, ((x - ax) * dx + (y - ay) * dy) / squared));
        const distance = Math.hypot(x - ax - t * dx, y - ay - t * dy);
        if (distance < closest) { closest = distance; match = { road, along: road.lengths[i - 1] + t * Math.sqrt(squared) }; }
      }
    }
    if (match && !match.road.unlit) match.road.intervals.push([Math.max(0, match.along - RADIUS), Math.min(match.road.total, match.along + RADIUS)]);
  }
  const features: FeatureCollection<LineString>['features'] = [];
  for (const road of roads) {
    const merged: [number, number][] = [];
    for (const interval of road.intervals.sort((a, b) => a[0] - b[0])) {
      const previous = merged.at(-1);
      if (previous && interval[0] <= previous[1]) previous[1] = Math.max(previous[1], interval[1]);
      else merged.push([...interval]);
    }
    function pointAt(distance: number): Position {
      for (let i = 1; i < road.lengths.length; i++) {
        if (road.lengths[i] < distance) continue;
        const length = road.lengths[i] - road.lengths[i - 1];
        const t = length ? (distance - road.lengths[i - 1]) / length : 0;
        return [road.points[i - 1][0] + t * (road.points[i][0] - road.points[i - 1][0]), road.points[i - 1][1] + t * (road.points[i][1] - road.points[i - 1][1])];
      }
      return road.points.at(-1)!;
    }
    for (const [start, end] of merged) {
      if (end <= start) continue;
      const coordinates = [pointAt(start), ...road.points.filter((_, i) => road.lengths[i] > start && road.lengths[i] < end), pointAt(end)];
      features.push({ type: 'Feature', geometry: { type: 'LineString', coordinates }, properties: { basis: 'mapped_lamp_proximity', illumination: 'unverified' } });
    }
  }
  return { type: 'FeatureCollection', features };
}
