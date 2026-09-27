"""到站时刻编辑接口:合法保存、非法拒绝、检测随新时刻重算。"""
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.models import Arrival, Line, Trip

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)  # 不触发 lifespan,无需 Postgres/种子

BASE = datetime(2026, 9, 17, 7, 0)


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    line = Line(code="L1", name="测试线", planned_headway_min=8.0, bunch_threshold=3.0, large_threshold=15.0)
    db.add(line)
    db.flush()
    for i, no in enumerate(["T1", "T2"]):
        t = Trip(line_id=line.id, trip_no=no, planned_depart=BASE + timedelta(minutes=8 * i), vehicle_no="V")
        db.add(t)
        db.flush()
        db.add(Arrival(trip_id=t.id, stop_name="市民中心", stop_seq=1, actual_arrive=BASE + timedelta(minutes=8 * i)))
    db.commit()
    ids = {a.trip.trip_no: a.id for a in db.query(Arrival).all()}
    db.close()
    yield ids


def arrival_of(trip_no: str) -> dict:
    rows = client.get("/api/arrivals").json()
    return next(r for r in rows if r["trip_no"] == trip_no)


def test_update_arrival_persists(fresh_db):
    r = client.patch(f"/api/arrivals/{fresh_db['T1']}", json={"actual_arrive": "2026-09-17T07:05"})
    assert r.status_code == 200
    assert r.json()["actual_arrive"].startswith("2026-09-17T07:05")
    # 重新拉取(离开再进来)仍是新时刻
    assert arrival_of("T1")["actual_arrive"].startswith("2026-09-17T07:05")
    assert arrival_of("T2")["actual_arrive"].startswith("2026-09-17T07:08")


def test_update_arrival_accepts_date_and_seconds(fresh_db):
    assert client.patch(f"/api/arrivals/{fresh_db['T1']}", json={"actual_arrive": "2026-09-17 07:06:30"}).status_code == 200
    assert arrival_of("T1")["actual_arrive"].startswith("2026-09-17T07:06:30")


@pytest.mark.parametrize("bad", ["", "   ", None, "不是时间", "2026-13-40T99:99"])
def test_update_arrival_rejects_unparseable(fresh_db, bad):
    before = arrival_of("T1")["actual_arrive"]
    r = client.patch(f"/api/arrivals/{fresh_db['T1']}", json={"actual_arrive": bad})
    assert r.status_code == 422
    # 拒绝后保持改前
    assert arrival_of("T1")["actual_arrive"] == before


def test_update_arrival_missing_body_field(fresh_db):
    before = arrival_of("T1")["actual_arrive"]
    assert client.patch(f"/api/arrivals/{fresh_db['T1']}", json={}).status_code == 422
    assert arrival_of("T1")["actual_arrive"] == before


def test_update_arrival_not_found(fresh_db):
    assert client.patch("/api/arrivals/99999", json={"actual_arrive": "2026-09-17T07:05"}).status_code == 404


def test_pairing_follows_new_time_after_swap(fresh_db):
    # T1 改到 T2 之后:合法但与邻班颠倒,配对顺序按新时间
    r = client.patch(f"/api/arrivals/{fresh_db['T1']}", json={"actual_arrive": "2026-09-17T07:20"})
    assert r.status_code == 200
    events = client.post("/api/reports/run?line_id=1").json()["events"]
    assert len(events) == 1
    ev = events[0]
    assert (ev["earlier_trip"], ev["later_trip"]) == ("T2", "T1")
    assert ev["gap_min"] == 12.0
    assert ev["status"] == "normal"
    # 时间轴该点位置移动:首班变为 T2
    marks = client.get("/api/reports/timeline?line_id=1&stop_name=市民中心").json()["marks"]
    assert [m["trip_no"] for m in marks] == ["T2", "T1"]
    assert marks[0]["pct"] == 0.0 and marks[1]["pct"] == 100.0


def test_detection_status_changes_with_new_time(fresh_db):
    # T1 改到紧贴 T2(间隔 1 分钟)→ 串车
    client.patch(f"/api/arrivals/{fresh_db['T1']}", json={"actual_arrive": "2026-09-17T07:07"})
    events = client.post("/api/reports/run?line_id=1").json()["events"]
    assert events[0]["status"] == "bunching"
    assert events[0]["gap_min"] == 1.0
