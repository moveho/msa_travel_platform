from fastapi import FastAPI, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr
from passlib.context import CryptContext
from typing import Optional
import os

# Config
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = "travel_db"

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI()

# DB Connection
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]
users_collection = db["users"]

# Helpers
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

# Models
class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    role: str

# Routes
@app.post("/signup", response_model=UserResponse)
async def signup(user: UserCreate):
    if not user.username or not user.password:
        raise HTTPException(status_code=400, detail="Username and password required")
        
    existing_user = await users_collection.find_one({"username": user.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    role = "admin" if user.username == "admin" else "user"
    hashed_password = get_password_hash(user.password)
    
    new_user = {
        "username": user.username,
        "password": hashed_password,
        "role": role
    }
    
    result = await users_collection.insert_one(new_user)
    
    return UserResponse(id=str(result.inserted_id), username=user.username, role=role)

@app.post("/validate")
async def validate_user(user_login: UserLogin):
    print(f"DEBUG: Validate request for {user_login.username}")
    try:
        user = await users_collection.find_one({"username": user_login.username})
    except Exception as e:
        print(f"DEBUG: DB Error: {e}")
        raise HTTPException(status_code=500, detail="Database error")
        
    if user:
        print(f"DEBUG: User found: {user['username']}")
        is_valid = verify_password(user_login.password, user['password'])
        print(f"DEBUG: Password valid: {is_valid}")
    else:
        print("DEBUG: User not found")

    if not user or not verify_password(user_login.password, user['password']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return {
        "id": str(user["_id"]),
        "username": user["username"],
        "role": user["role"]
    }

@app.get("/users/{username}")
async def get_user(username: str):
    user = await users_collection.find_one({"username": username})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": str(user["_id"]),
        "username": user["username"],
        "role": user["role"]
    }

# Admin: Get All Users
@app.get("/users")
async def get_all_users():
    users = []
    cursor = users_collection.find({})
    async for document in cursor:
        users.append({
            "id": str(document["_id"]),
            "username": document["username"],
            "role": document["role"]
        })
    return users

@app.delete("/users/{user_id}")
async def delete_user(user_id: str):
    from bson import ObjectId
    try:
        result = await users_collection.delete_one({"_id": ObjectId(user_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        return {"detail": "User deleted"}
    except:
         raise HTTPException(status_code=400, detail="Invalid ID format")

@app.get("/health")
def health_check():
    return {"status": "ok"}
