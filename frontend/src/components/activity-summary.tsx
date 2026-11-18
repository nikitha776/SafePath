import type { ActivityEntry } from '@/lib/route-places';
export default function ActivitySummary({ entry, valid }: { entry?: ActivityEntry; valid: boolean }) {
  if (!valid) return <div className="activity-pending">Choose a valid departure time.</div>;
  if (entry?.error) return <div className="activity-pending activity-error" role="status">Business activity unavailable. Select the route to see details.</div>;
  const data = entry?.data, summary = data?.summary;
  if (!summary) return <div className="activity-pending" role="status">Checking business schedules…</div>;
  const counts = summary.businesses;
  return <div className="activity-mini" aria-label="Expected business activity at arrival">
    <div className="activity-caption">Businesses at arrival <span>Scheduled</span></div>
    <div className="activity-counts"><span className="expected-open"><strong>{counts.expected_open}</strong> expected open</span><span className="expected-closed"><strong>{counts.expected_closed}</strong> expected closed</span><span><strong>{counts.hours_unknown}</strong> hours unknown</span></div>
    <div className="activity-coverage">Shops, fuel & pharmacies · {summary.schedule_coverage_percent === null ? 'No business listings' : `${summary.schedule_coverage_percent}% with usable hours`}{!!(data?.truncated_categories?.length || data?.unavailable_categories?.length) && ' · partial listing'}</div>
  </div>;
}
