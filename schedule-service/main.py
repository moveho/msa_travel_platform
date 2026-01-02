from fastapi import FastAPI, Depends, HTTPException, Header
from sqlalchemy import create_engine, Column, Integer, String, Text, Date, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import date
import os
import requests

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL")
AUTH_SERVICE_URL = "http://auth-service:8000/verify"
TRAVEL_SERVICE_URL = "http://travel-service:8000/travels"

# Database Setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models
class Schedule(Base):
    __tablename__ = "schedules"
    id = Column(Integer, primary_key=True, index=True)
    travel_id = Column(Integer, nullable=False)
    date = Column(Date, nullable=False)
    place = Column(String(100), nullable=False)
    memo = Column(Text)

app = FastAPI()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Auth Middleware
def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    token = authorization.replace("Bearer ", "")
    try:
        response = requests.get(AUTH_SERVICE_URL, headers={"Authorization": f"Bearer {token}"})
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid token")
        return response.json()
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=500, detail="Auth service unavailable")

# Helper to verify travel ownership
def verify_travel_ownership(travel_id: int, token: str):
    try:
        response = requests.get(f"{TRAVEL_SERVICE_URL}/{travel_id}", headers={"Authorization": f"Bearer {token}"})
        if response.status_code != 200:
            return False
        return True
    except:
        return False

# Pydantic Models
class ScheduleCreate(BaseModel):
    travel_id: int
    date: date
    place: str
    memo: Optional[str] = None

class ScheduleResponse(BaseModel):
    id: int
    travel_id: int
    date: date
    place: str
    memo: Optional[str]

    class Config:
        orm_mode = True

# Routes
@app.post("/schedules", response_model=ScheduleResponse)
def create_schedule(schedule: ScheduleCreate, authorization: Optional[str] = Header(None), user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    token = authorization.replace("Bearer ", "")
    # Verify user owns the travel
    if not verify_travel_ownership(schedule.travel_id, token):
        raise HTTPException(status_code=403, detail="Not authorized to add schedule to this travel")

    new_schedule = Schedule(
        travel_id=schedule.travel_id,
        date=schedule.date,
        place=schedule.place,
        memo=schedule.memo
    )
    db.add(new_schedule)
    db.commit()
    db.refresh(new_schedule)
    return new_schedule

@app.get("/schedules", response_model=List[ScheduleResponse])
def read_schedules(travel_id: int, authorization: Optional[str] = Header(None), user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    token = authorization.replace("Bearer ", "")
    if not verify_travel_ownership(travel_id, token):
         raise HTTPException(status_code=403, detail="Not authorized to view schedules for this travel")
         
    return db.query(Schedule).filter(Schedule.travel_id == travel_id).all()

@app.put("/schedules/{schedule_id}", response_model=ScheduleResponse)
def update_schedule(schedule_id: int, schedule_update: ScheduleCreate, authorization: Optional[str] = Header(None), user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    token = authorization.replace("Bearer ", "")
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    if not verify_travel_ownership(schedule.travel_id, token):
        raise HTTPException(status_code=403, detail="Not authorized")

    schedule.date = schedule_update.date
    schedule.place = schedule_update.place
    schedule.memo = schedule_update.memo
    db.commit()
    db.refresh(schedule)
    return schedule

@app.delete("/schedules/{schedule_id}")
def delete_schedule(schedule_id: int, authorization: Optional[str] = Header(None), user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    token = authorization.replace("Bearer ", "")
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    if not verify_travel_ownership(schedule.travel_id, token):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    db.delete(schedule)
    db.commit()
    return {"detail": "Schedule deleted"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
