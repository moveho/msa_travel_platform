from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import List, Optional
import os
import requests

# Configuration
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user-service:8000")
SECRET_KEY = os.getenv("JWT_SECRET", "secret")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()

# Helpers
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Routes
@app.post("/signup")
def signup(user: dict):
    # Proxy to user-service
    try:
        response = requests.post(f"{USER_SERVICE_URL}/signup", json=user)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.json().get('detail'))
        return response.json()
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=500, detail="User service unavailable")

@app.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # Validate against user-service
    print(f"DEBUG: Login attempt for {form_data.username}")
    try:
        payload = {
            "username": form_data.username,
            "password": form_data.password
        }
        print(f"DEBUG: Sending to user-service: {payload}")
        response = requests.post(f"{USER_SERVICE_URL}/validate", json=payload)
        print(f"DEBUG: User-service response: {response.status_code} - {response.text}")
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = response.json()
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=500, detail="User service unavailable")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user['username'], "user_id": user['id'], "role": user['role']}, 
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/verify")
def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: str = payload.get("user_id")
        role: str = payload.get("role", "user")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"username": username, "user_id": user_id, "role": role}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Admin Proxy Routes
@app.get("/users")
def get_all_users(token: str = Depends(oauth2_scheme)):
    payload = verify_token(token)
    if payload['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    response = requests.get(f"{USER_SERVICE_URL}/users")
    return response.json()

@app.delete("/users/{user_id}")
def delete_user(user_id: str, token: str = Depends(oauth2_scheme)):
    payload = verify_token(token)
    if payload['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    response = requests.delete(f"{USER_SERVICE_URL}/users/{user_id}")
    return response.json()

@app.get("/health")
def health_check():
    return {"status": "ok"}
