import type { RouteAssessment } from './route-places';
export function compareAssessments(items: { assessment?: RouteAssessment; duration: number }[]) {
  if (items.length < 2) return { title: 'One candidate available', detail: 'There is no alternative route to compare.' };
  if (items.some(item => !item.assessment?.rankable || typeof item.assessment.concern_score !== 'number' || !Number.isFinite(item.assessment.concern_score) || !Number.isFinite(item.duration) || item.duration <= 0)) return { title: 'Insufficient evidence to rank', detail: 'Compare the available indicators below. Missing information prevents a supported route preference.' };
  const ordered = items.map((item, index) => ({ ...item, index })).sort((a,b) => a.assessment!.concern_score! - b.assessment!.concern_score!);
  const best = ordered[0], other = ordered[1];
  if (other.assessment!.concern_score! - best.assessment!.concern_score! < 10) return { title: 'No meaningful difference', detail: 'Mapped-condition scores are too close to support a preference.' };
  const fastest = Math.min(...items.map(item => item.duration));
  if (best.duration > fastest * 1.5 || best.duration - fastest > 600) return { title: 'Conditions and time trade-off', detail: 'The lower-concern candidate takes substantially longer. Review both routes; no automatic preference is selected.' };
  return { title: `Route ${best.index + 1}: more favorable mapped conditions`, detail: `Prototype indicators suggest fewer mapped concerns, with about ${Math.round((best.duration - fastest)/60)} extra minutes versus the fastest candidate. This is not a safety guarantee.` };
}
