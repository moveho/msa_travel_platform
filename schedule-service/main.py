from fastapi import FastAPI, Depends, HTTPException, Header
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from typing import List, Optional
import os
import requests

# Configuration
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000/verify")
TRAVEL_SERVICE_URL = os.getenv("TRAVEL_SERVICE_URL", "http://travel-service:8000/travels")
DB_NAME = "travel_db"

app = FastAPI()

# DB
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]
schedules_collection = db["schedules"]

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
def verify_travel_ownership(travel_id: str, token: str):
    try:
        response = requests.get(f"{TRAVEL_SERVICE_URL}/{travel_id}", headers={"Authorization": f"Bearer {token}"})
        if response.status_code != 200:
            return False
        return True
    except:
        return False

# Models
class ScheduleCreate(BaseModel):
    travel_id: str
    date: str
    place: str
    memo: Optional[str] = None

class ScheduleResponse(BaseModel):
    id: str
    travel_id: str
    date: str
    place: str
    memo: Optional[str]

# Routes
@app.post("/schedules", response_model=ScheduleResponse)
async def create_schedule(schedule: ScheduleCreate, authorization: Optional[str] = Header(None), user: dict = Depends(get_current_user)):
    token = authorization.replace("Bearer ", "")
    # Verify user owns the travel
    if not verify_travel_ownership(schedule.travel_id, token):
        raise HTTPException(status_code=403, detail="Not authorized to add schedule to this travel")

    new_schedule = {
        "travel_id": schedule.travel_id,
        "date": schedule.date,
        "place": schedule.place,
        "memo": schedule.memo
    }
    
    result = await schedules_collection.insert_one(new_schedule)
    return {
        "id": str(result.inserted_id),
        **new_schedule
    }

@app.get("/schedules", response_model=List[ScheduleResponse])
async def read_schedules(travel_id: str, authorization: Optional[str] = Header(None), user: dict = Depends(get_current_user)):
    token = authorization.replace("Bearer ", "")
    if not verify_travel_ownership(travel_id, token):
         raise HTTPException(status_code=403, detail="Not authorized to view schedules for this travel")
         
    schedules = []
    cursor = schedules_collection.find({"travel_id": travel_id})
    async for doc in cursor:
        schedules.append({
            "id": str(doc["_id"]),
            "travel_id": doc["travel_id"],
            "date": doc["date"],
            "place": doc["place"],
            "memo": doc.get("memo")
        })
    return schedules

@app.delete("/schedules/{schedule_id}")
async def delete_schedule(schedule_id: str, authorization: Optional[str] = Header(None), user: dict = Depends(get_current_user)):
    token = authorization.replace("Bearer ", "")
    from bson import ObjectId
    try:
        oid = ObjectId(schedule_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid ID")

    # Get schedule to find travel_id
    schedule = await schedules_collection.find_one({"_id": oid})
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    if not verify_travel_ownership(schedule["travel_id"], token):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await schedules_collection.delete_one({"_id": oid})
    return {"detail": "Schedule deleted"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
