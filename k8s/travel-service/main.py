from fastapi import FastAPI, Depends, HTTPException, Header
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import List, Optional
from aiokafka import AIOKafkaProducer
import os
import requests
import json
import asyncio

# Configuration
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000/verify")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
DB_NAME = "travel_db"

app = FastAPI()

# DB Connection
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]
travels_collection = db["travels"]

# Kafka Producer
producer = None

@app.on_event("startup")
async def startup_event():
    global producer
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    # Retry connection logic
    for _ in range(5):
        try:
            await producer.start()
            break
        except Exception as e:
            print(f"Kafka connection failed: {e}. Retrying...")
            await asyncio.sleep(2)

@app.on_event("shutdown")
async def shutdown_event():
    if producer:
        await producer.stop()

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

# Models
class TravelCreate(BaseModel):
    title: str
    description: Optional[str] = None
    image_url: Optional[str] = None

class TravelResponse(BaseModel):
    id: str
    user_id: str
    title: str
    description: Optional[str]
    image_url: Optional[str]

# Routes
@app.post("/travels", response_model=TravelResponse)
async def create_travel(travel: TravelCreate, user: dict = Depends(get_current_user)):
    new_travel = {
        "user_id": user['user_id'],
        "title": travel.title,
        "description": travel.description,
        "image_url": travel.image_url,
        "username": user['username'] # Added for recommendation display
    }
    
    result = await travels_collection.insert_one(new_travel)
    created_travel = {
        "id": str(result.inserted_id),
        **new_travel
    }
    
    # Publish to Kafka
    try:
        if producer:
            # Create a copy for Kafka message to avoid ObjectId serialization error
            kafka_message = {
                "id": str(result.inserted_id),
                "user_id": new_travel["user_id"],
                "title": new_travel["title"],
                "description": new_travel["description"],
                "image_url": new_travel.get("image_url"),
                "username": new_travel["username"]
            }
            message = json.dumps(kafka_message).encode("utf-8")
            await producer.send_and_wait("travel-topic", message)
    except Exception as e:
        print(f"Failed to publish to Kafka: {e}")

    return created_travel

@app.get("/travels", response_model=List[TravelResponse])
async def read_travels(user: dict = Depends(get_current_user)):
    travels = []
    cursor = travels_collection.find({"user_id": user['user_id']})
    async for doc in cursor:
        travels.append({
            "id": str(doc["_id"]),
            "user_id": doc["user_id"],
            "title": doc["title"],
            "description": doc.get("description"),
            "image_url": doc.get("image_url")
        })
    return travels

@app.get("/admin/travels", response_model=List[TravelResponse])
async def read_all_travels(user: dict = Depends(get_current_user)):
    if user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    travels = []
    cursor = travels_collection.find({})
    async for doc in cursor:
        travels.append({
            "id": str(doc["_id"]),
            "user_id": doc["user_id"],
            "title": doc["title"],
            "description": doc.get("description"),
            "image_url": doc.get("image_url")
        })
    return travels

@app.get("/travels/{travel_id}", response_model=TravelResponse)
async def read_travel(travel_id: str, user: dict = Depends(get_current_user)):
    from bson import ObjectId
    try:
        oid = ObjectId(travel_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid ID")

    query = {"_id": oid}
    if user.get('role') != 'admin':
        query["user_id"] = user['user_id']
        
    doc = await travels_collection.find_one(query)
    if not doc:
        raise HTTPException(status_code=404, detail="Travel not found")
        
    return {
        "id": str(doc["_id"]),
        "user_id": doc["user_id"],
        "title": doc["title"],
        "description": doc.get("description"),
        "image_url": doc.get("image_url")
    }

@app.delete("/travels/{travel_id}")
async def delete_travel(travel_id: str, user: dict = Depends(get_current_user)):
    from bson import ObjectId
    try:
        oid = ObjectId(travel_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid ID")

    query = {"_id": oid}
    if user.get('role') != 'admin':
        query["user_id"] = user['user_id']
    
    result = await travels_collection.delete_one(query)
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Travel not found")
    
    return {"detail": "Travel deleted"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
