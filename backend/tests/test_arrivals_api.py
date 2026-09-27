from datetime import datetime, timedelta
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.api.arrivals import router as arrivals_router
from app.database import Base, get_db
from app.models.models import Arrival, Line, Trip

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture()
def client():
    Base.metadata.create_all(bind=engine)
    db = TestingSession()
    line = Line(code="B12", name="城东环线")
    db.add(line); db.flush()
    base = datetime(2026, 9, 17, 7, 0, 0)
    t1 = Trip(line_id=line.id, trip_no="T01", planned_depart=base)
    t2 = Trip(line_id=line.id, trip_no="T02", planned_depart=base + timedelta(minutes=8))
    db.add_all([t1, t2]); db.flush()
    a1 = Arrival(trip_id=t1.id, stop_name="市民中心", stop_seq=1, actual_arrive=base + timedelta(minutes=6))
    a2 = Arrival(trip_id=t2.id, stop_name="市民中心", stop_seq=1, actual_arrive=base + timedelta(minutes=14))
    db.add_all([a1, a2]); db.commit()
    ids = (a1.id, a2.id)
    db.close()

    app = FastAPI()
    app.include_router(arrivals_router, prefix="/api")
    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app), ids
    Base.metadata.drop_all(bind=engine)

def test_update_arrival_ok(client):
    api, (a1, _) = client
    resp = api.put(f"/api/arrivals/{a1}", json={"actual_arrive": "2026-09-17 07:30"})
    assert resp.status_code == 200
    assert resp.json()["actual_arrive"] == "2026-09-17T07:30:00"
    rows = api.get("/api/arrivals").json()
    assert rows[-1]["id"] == a1  # 列表按新时刻排序，改后的记录排到最后

def test_update_arrival_rejects_empty(client):
    api, (a1, _) = client
    resp = api.put(f"/api/arrivals/{a1}", json={"actual_arrive": "  "})
    assert resp.status_code == 400
    rows = api.get("/api/arrivals").json()
    assert rows[0]["actual_arrive"] == "2026-09-17T07:06:00"  # 保持改前

def test_update_arrival_rejects_unparseable(client):
    api, (a1, _) = client
    resp = api.put(f"/api/arrivals/{a1}", json={"actual_arrive": "早上七点半"})
    assert resp.status_code == 400
    rows = api.get("/api/arrivals").json()
    assert rows[0]["actual_arrive"] == "2026-09-17T07:06:00"

def test_update_arrival_not_found(client):
    api, _ = client
    resp = api.put("/api/arrivals/9999", json={"actual_arrive": "2026-09-17 07:30"})
    assert resp.status_code == 404
