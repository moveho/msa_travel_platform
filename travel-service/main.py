from fastapi import FastAPI, Depends, HTTPException, Header
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import List, Optional
import os
import requests

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL")
AUTH_SERVICE_URL = "http://auth-service:8000/verify"

# Database Setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models
class Travel(Base):
    __tablename__ = "travels"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(Text)

app = FastAPI()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Auth Middleware (Manual for simplicity in MSA)
def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    token = authorization.replace("Bearer ", "")
    try:
        response = requests.get(AUTH_SERVICE_URL, headers={"Authorization": f"Bearer {token}"})
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid token")
        return response.json() # Returns {"username": "...", "user_id": ..., "role": ...}
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=500, detail="Auth service unavailable")

# Pydantic Models
class TravelCreate(BaseModel):
    title: str
    description: Optional[str] = None

class TravelResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: Optional[str]

    class Config:
        orm_mode = True

# Routes
@app.post("/travels", response_model=TravelResponse)
def create_travel(travel: TravelCreate, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    new_travel = Travel(
        user_id=user['user_id'],
        title=travel.title,
        description=travel.description
    )
    db.add(new_travel)
    db.commit()
    db.refresh(new_travel)
    return new_travel

@app.get("/travels", response_model=List[TravelResponse])
def read_travels(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    # Show only user's travels
    return db.query(Travel).filter(Travel.user_id == user['user_id']).all()

@app.get("/admin/travels", response_model=List[TravelResponse])
def read_all_travels(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return db.query(Travel).all()

@app.get("/travels/{travel_id}", response_model=TravelResponse)
def read_travel(travel_id: int, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    # Allow admin to view any travel
    if user.get('role') == 'admin':
        travel = db.query(Travel).filter(Travel.id == travel_id).first()
    else:
        travel = db.query(Travel).filter(Travel.id == travel_id, Travel.user_id == user['user_id']).first()
        
    if not travel:
        raise HTTPException(status_code=404, detail="Travel not found")
    return travel

@app.put("/travels/{travel_id}", response_model=TravelResponse)
def update_travel(travel_id: int, travel_update: TravelCreate, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    travel = db.query(Travel).filter(Travel.id == travel_id, Travel.user_id == user['user_id']).first()
    if not travel:
        raise HTTPException(status_code=404, detail="Travel not found")
    
    travel.title = travel_update.title
    travel.description = travel_update.description
    db.commit()
    db.refresh(travel)
    return travel

@app.delete("/travels/{travel_id}")
def delete_travel(travel_id: int, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    # Allow admin to delete any travel
    if user.get('role') == 'admin':
        travel = db.query(Travel).filter(Travel.id == travel_id).first()
    else:
        travel = db.query(Travel).filter(Travel.id == travel_id, Travel.user_id == user['user_id']).first()
        
    if not travel:
        raise HTTPException(status_code=404, detail="Travel not found")
    
    db.delete(travel)
    db.commit()
    return {"detail": "Travel deleted"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
