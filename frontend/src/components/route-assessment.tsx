import { arrivalLabel, type RouteAssessment } from '@/lib/route-places';
export function AssessmentBadge({ data }: { data?: RouteAssessment }) {
  if (!data) return null;
  return <div className="assessment-badge"><span>Mapped concerns <strong>{data.concern_label}</strong></span><span>Evidence confidence <strong>{data.confidence_label} · {data.confidence_percent}%</strong></span><small className="assessment-caption">Prototype evidence coverage index.</small></div>;
}
export default function AssessmentDetails({ data }: { data?: RouteAssessment }) {
  if (!data) return <p className="places-status">Choose a route and departure time to inspect section evidence.</p>;
  return <div className="assessment-details">
    <AssessmentBadge data={data} />
    <div className="assessment-metrics"><p><strong>{data.lighting_coverage_percent}%</strong> mapped lighting coverage</p><p><strong>{data.road_coverage_percent}%</strong> cached road coverage</p><p><strong>{data.longest_mapped_support_gap_m} m</strong> longest stretch without mapped support</p></div>
    <small>A mapped-support gap means no scheduled-open business within 100 m and no hospital/police listing within 200 m. Unknown hours and incomplete listings can create gaps; this does not establish isolation.</small>
    <div className="section-key" aria-label="Section evidence band colours"><span><i className="concern-key" />Mapped concerns</span><span><i className="unknown-key" />Unknown</span><span><i className="favorable-key" />Fewer concerns</span><span><i className="mixed-key" />Mixed</span></div>
    <ul className="assessment-reasons">{data.reasons.map(reason => <li key={reason}>{reason}</li>)}</ul>
    <details><summary>Inspect {data.segments.features.length} route sections</summary><ol className="section-evidence">{data.segments.features.map(feature => { const p = feature.properties; return <li key={p.index}><div><strong>Section {p.index} · {p.distance_from_start_m}–{Math.round(p.distance_from_start_m + p.length_m)} m</strong><span>{arrivalLabel(p.estimated_arrival)}</span></div><p>{p.concern === 'more_concerns' ? 'Mapped concerns identified' : p.concern === 'unknown' ? 'Concern unknown' : p.concern === 'mixed' ? 'Mixed mapped conditions' : 'Fewer mapped concerns'} · Evidence confidence {p.confidence_percent}%</p><ul>{p.reasons.map(reason => <li key={reason}>{reason}</li>)}</ul></li>; })}</ol></details>
    <details><summary>How this assessment works</summary><p>{data.method}</p><p>{data.notice}</p><p>Confidence is a prototype evidence-coverage index, not a probability of safety or harm. The nighttime lighting window is 6 PM–6 AM IST, not measured sunset or visibility.</p></details>
  </div>;
}
