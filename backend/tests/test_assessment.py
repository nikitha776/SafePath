from datetime import datetime, timezone
import copy
from app.activity import ActivityRequest, analyze_activity
from app.assessment import assess_route, split_route, load_route_evidence
from app.city import CITY

NOW = datetime(2026,10,23,tzinfo=timezone.utc)


def fixtures(hours='24/7', lit='yes'):
    x,y=CITY['center']
    geometry={'type':'LineString','coordinates':[[x,y],[x+.006,y]]}
    body=ActivityRequest(geometry=geometry,departure_time='2026-10-23T22:00:00+05:30',duration_seconds=600)
    raw={'features':[{'type':'Feature','geometry':{'type':'Point','coordinates':[x+i*.0008,y]},'properties':{'kind':'shop','opening_hours':hours}} for i in range(8)]}
    activity=analyze_activity(body,raw)
    ev={'available':True,'truncated':False,'features':[{'type':'Feature','geometry':geometry,'properties':{'kind':'road','lit':lit,'foot':'yes','fetched_at':NOW.isoformat()}}]}
    return body,activity,ev


def test_sections_preserve_bends_and_disconnected_legs():
    geometry={'type':'MultiLineString','coordinates':[[[77.6,13],[77.601,13],[77.601,13.001]],[[77.61,13],[77.611,13]]]}
    sections,total=split_route(geometry)
    assert all(0<s['length']<=100.00001 for s in sections)
    assert 300<total<350
    assert all(not (s['coordinates'][0][0]<77.605<s['coordinates'][-1][0]) for s in sections)
    assert sum(s['length'] for s in sections)==total


def test_missing_data_does_not_become_an_adverse_condition():
    body,activity,_=fixtures(None)
    result=assess_route(body,activity,{'available':False,'truncated':False,'features':[]},NOW)
    assert result['concern_score'] is None and not result['rankable']
    assert result['confidence_percent']==0
    assert result['mapped_concern_length_m']==0
    assert all(s['properties']['concern']=='unknown' for s in result['segments']['features'])


def test_explicit_unlit_tag_is_distinct_from_unknown():
    body,activity,evidence=fixtures(None,'no')
    unlit=assess_route(body,activity,evidence,NOW)
    evidence['features'][0]['properties']['lit']='unknown'
    unknown=assess_route(body,activity,evidence,NOW)
    assert unlit['mapped_concern_length_m']>0
    assert unknown['mapped_concern_length_m']==0
    assert not unknown['rankable']


def test_complete_fresh_evidence_can_be_compared_but_partial_or_stale_cannot():
    body,activity,evidence=fixtures()
    result=assess_route(body,activity,evidence,NOW)
    assert result['rankable'] and result['confidence_percent']==100 and result['concern_score']==0
    partial=copy.deepcopy(activity);partial['truncated_categories']=['shop']
    assert not assess_route(body,partial,evidence,NOW)['rankable']
    evidence['features'][0]['properties']['fetched_at']='2020-01-01T00:00:00+00:00'
    assert not assess_route(body,activity,evidence,NOW)['rankable']


def test_schedules_are_evaluated_at_section_arrival():
    body,activity,evidence=fixtures('09:00-23:00')
    early=assess_route(body,activity,evidence,NOW)
    late_body=body.model_copy(update={'departure_time':datetime.fromisoformat('2026-10-23T23:00:00+05:30')})
    late=assess_route(late_body,analyze_activity(late_body,activity),evidence,NOW)
    assert early['segments']['features'][0]['properties']['businesses']['expected_open']>0
    assert late['segments']['features'][0]['properties']['businesses']['expected_closed']>0
    assert late['concern_score']>early['concern_score']


def test_explicit_access_restriction_is_explained():
    body,activity,evidence=fixtures()
    evidence['features'][0]['properties']['foot']='no'
    result=assess_route(body,activity,evidence,NOW)
    assert result['mapped_concern_length_m']>0
    assert any('restrictions' in reason for reason in result['segments']['features'][0]['properties']['reasons'])


def test_database_failure_degrades_to_missing_evidence(monkeypatch):
    import app.assessment as module
    def fail():raise RuntimeError('No database')
    monkeypatch.setattr(module,'get_engine',fail)
    body,_,_=fixtures()
    assert load_route_evidence(body.geometry.model_dump())['available'] is False


def test_support_gap_is_a_listing_gap_and_does_not_bridge_legs():
    x,y=CITY['center']
    body=ActivityRequest(geometry={'type':'MultiLineString','coordinates':[[[x,y],[x+.001,y]],[[x+.004,y],[x+.005,y]]]},departure_time='2026-10-23T23:00:00+05:30',duration_seconds=300)
    activity=analyze_activity(body,{'features':[]})
    result=assess_route(body,activity,{'available':False,'features':[]},NOW)
    assert 100<result['longest_mapped_support_gap_m']<115
    assert result['mapped_concern_length_m']==0
    assert result['concern_score'] is None
    assert 'does not establish' in result['notice']
