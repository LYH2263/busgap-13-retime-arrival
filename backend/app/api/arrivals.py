from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models.models import Arrival
router = APIRouter(prefix="/arrivals", tags=["arrivals"])

class ArrivalUpdate(BaseModel):
    actual_arrive: datetime

    @field_validator("actual_arrive", mode="before")
    @classmethod
    def parse_actual_arrive(cls, v):
        if v is None or (isinstance(v, str) and not v.strip()):
            raise ValueError("到站时刻不能为空")
        if isinstance(v, str):
            try:
                v = datetime.fromisoformat(v.strip())
            except ValueError:
                raise ValueError("无法解析的到站时刻") from None
        if isinstance(v, datetime) and v.tzinfo is not None:
            v = v.astimezone(timezone.utc).replace(tzinfo=None)
        return v

def to_dict(r: Arrival) -> dict:
    return {"id": r.id, "trip_id": r.trip_id, "trip_no": r.trip.trip_no, "line_id": r.trip.line_id,
            "stop_name": r.stop_name, "stop_seq": r.stop_seq, "actual_arrive": r.actual_arrive.isoformat()}

@router.get("")
def list_arrivals(line_id: int | None = None, db: Session = Depends(get_db)):
    rows = db.scalars(select(Arrival).options(joinedload(Arrival.trip)).order_by(Arrival.actual_arrive)).unique().all()
    return [to_dict(r) for r in rows if line_id is None or r.trip.line_id == line_id]

@router.patch("/{arrival_id}")
def update_arrival(arrival_id: int, body: ArrivalUpdate, db: Session = Depends(get_db)):
    r = db.get(Arrival, arrival_id)
    if r is None: raise HTTPException(404, "到站记录不存在")
    r.actual_arrive = body.actual_arrive
    db.commit(); db.refresh(r)
    return to_dict(r)
