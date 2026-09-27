from datetime import datetime, timedelta
from app.services.bunch_engine import classify_gap, detect_bunching

def test_classify_bunching():
    assert classify_gap(2.0, 8.0, 3.0, 15.0)[0] == "bunching"

def test_classify_large():
    assert classify_gap(16.0, 8.0, 3.0, 15.0)[0] == "large_gap"

def test_classify_normal():
    assert classify_gap(8.0, 8.0, 3.0, 15.0)[0] == "normal"

def test_detect_bunching_events():
    base = datetime(2026, 1, 1, 8, 0)
    arrivals = [
        {"stop_name": "A", "trip_no": "T1", "actual_arrive": base},
        {"stop_name": "A", "trip_no": "T2", "actual_arrive": base + timedelta(minutes=2)},
        {"stop_name": "A", "trip_no": "T3", "actual_arrive": base + timedelta(minutes=20)},
    ]
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0)
    assert len(events) == 2
    assert events[0].status == "bunching"
    assert events[1].status == "large_gap"

def test_detect_bunching_reorders_after_time_change():
    base = datetime(2026, 1, 1, 8, 0)
    arrivals = [
        {"stop_name": "A", "trip_no": "T1", "actual_arrive": base},
        {"stop_name": "A", "trip_no": "T2", "actual_arrive": base + timedelta(minutes=8)},
        {"stop_name": "A", "trip_no": "T3", "actual_arrive": base + timedelta(minutes=16)},
    ]
    # T2 改到 T3 之后：配对顺序按新时间，T1→T3、T3→T2
    arrivals[1]["actual_arrive"] = base + timedelta(minutes=20)
    events = detect_bunching(arrivals, 8.0, 3.0, 15.0)
    assert [(e.earlier_trip, e.later_trip) for e in events] == [("T1", "T3"), ("T3", "T2")]
    assert events[0].gap_min == 16.0
    assert events[1].gap_min == 4.0
