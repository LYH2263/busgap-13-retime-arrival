from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models.models import Arrival
from app.services.timeparse import parse_actual_arrive
router = APIRouter(prefix="/arrivals", tags=["arrivals"])

class ArrivalUpdate(BaseModel):
    actual_arrive: str

def to_dict(r: Arrival) -> dict:
    return {"id": r.id, "trip_id": r.trip_id, "trip_no": r.trip.trip_no, "line_id": r.trip.line_id,
            "stop_name": r.stop_name, "stop_seq": r.stop_seq, "actual_arrive": r.actual_arrive.isoformat()}

@router.get("")
def list_arrivals(line_id: int | None = None, db: Session = Depends(get_db)):
    rows = db.scalars(select(Arrival).options(joinedload(Arrival.trip)).order_by(Arrival.actual_arrive)).unique().all()
    return [to_dict(r) for r in rows if line_id is None or r.trip.line_id == line_id]

@router.put("/{arrival_id}")
def update_arrival(arrival_id: int, body: ArrivalUpdate, db: Session = Depends(get_db)):
    r = db.get(Arrival, arrival_id)
    if not r: raise HTTPException(404, "到站记录不存在")
    try:
        r.actual_arrive = parse_actual_arrive(body.actual_arrive)
    except ValueError as e:
        raise HTTPException(400, str(e)) from None
    db.commit(); db.refresh(r)
    return to_dict(r)
