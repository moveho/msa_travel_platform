from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from aiokafka import AIOKafkaConsumer
from pydantic import BaseModel
from typing import List, Optional
import os
import json
import asyncio

# Config
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
DB_NAME = "travel_db"

app = FastAPI()

# DB
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]
recommendations_collection = db["recommendations"]

# Kafka Consumer
consumer = None

# Global Image Cache
IMAGE_CACHE = {}

async def consume_travels():
    global consumer
    consumer = AIOKafkaConsumer(
        "travel-topic", "external-travel-topic",
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="recommendation-group"
    )
    # Retry connection
    for _ in range(5):
        try:
            await consumer.start()
            break
        except Exception as e:
            print(f"Kafka connection failed: {e}. Retrying...")
            await asyncio.sleep(2)
            
    try:
        async for msg in consumer:
            data = json.loads(msg.value.decode("utf-8"))
            
            if msg.topic == "external-travel-topic":
                # Check for duplicates based on city + country
                existing = await db["destinations"].find_one({
                    "city": data.get("city", data.get("title")),
                    "source": "External Crawler"
                })
                if not existing:
                    await db["destinations"].insert_one(data)
                    print(f"Crawled & Saved: {data['title']} (image: {'yes' if data.get('image_url') else 'none'})")
                elif not existing.get("image_url") and data.get("image_url"):
                    # Backfill image_url for existing records that were saved without one
                    await db["destinations"].update_one(
                        {"_id": existing["_id"]},
                        {"$set": {"image_url": data["image_url"]}}
                    )
                    print(f"Updated image for: {data['title']}")
                else:
                    print(f"Skipped duplicate: {data['title']}")
            
            elif msg.topic == "travel-topic":
                # Save user travels to 'recommendations' (or 'destinations' if we want them recommended too)
                # For now, keeping original logic for user travels
                rec_item = {
                    "original_id": data["id"],
                    "title": data["title"],
                    "description": data.get("description"),
                    "author": data.get("username", "Unknown"),
                    "recommended_at": asyncio.get_event_loop().time()
                }
                await recommendations_collection.insert_one(rec_item)
                print(f"User Travel Saved: {data['title']}")
    finally:
        await consumer.stop()

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(consume_travels())
    # Load local fallback images into cache (for /images/{country} endpoint)
    try:
        import glob
        image_files = glob.glob("/app/images/*.jfif")
        print(f"Server Startup: Found {len(image_files)} local fallback images.")

        global IMAGE_CACHE
        IMAGE_CACHE = {}
        for file_path in image_files:
            filename = os.path.basename(file_path).replace(".jfif", "")
            normalized_key = filename.lower().replace(" ", "")
            with open(file_path, "rb") as f:
                IMAGE_CACHE[normalized_key] = f.read()

        print(f"Image cache loaded: {list(IMAGE_CACHE.keys())}")
    except Exception as e:
        print(f"Image cache load failed: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    if consumer:
        await consumer.stop()

@app.get("/images/{country}")
async def get_image(country: str):
    from fastapi.responses import Response

    # Find destination with this country and image_data
    doc = await db["destinations"].find_one(
        {"country": {"$regex": f"^{country}$", "$options": "i"}, "image_data": {"$exists": True}},
        {"image_data": 1}
    )
    
    if doc:
        return Response(content=doc["image_data"], media_type="image/jpeg")
    
    # Fallback to 'default' image from IMAGE_CACHE
    if "default" in IMAGE_CACHE:
        return Response(content=IMAGE_CACHE["default"], media_type="image/jpeg")

    return Response(status_code=404)

@app.get("/recommendations", response_model=List[dict])
async def get_recommendations(
    tags: Optional[List[str]] = None,
    season: Optional[str] = None,
    style: Optional[str] = None,
    budget: Optional[str] = None
):
    # Default preferences if not provided
    user_prefs = {
        "tags": tags or ["City", "Nature"],
        "season": season or "Spring",
        "style": style or "Solo",
        "budget": budget or "Medium"
    }

    pipeline = [
        {
            "$addFields": {
                "tagScore": {
                    "$multiply": [
                        { "$size": { "$setIntersection": ["$tags", user_prefs["tags"]] } },
                        10
                    ]
                },
                "seasonScore": {
                    "$cond": {
                        "if": { "$in": [user_prefs["season"], "$bestSeason"] },
                        "then": 20,
                        "else": 0
                    }
                },
                "styleScore": {
                    "$cond": {
                        "if": { "$in": [user_prefs["style"], "$travelStyle"] },
                        "then": 15,
                        "else": 0
                    }
                },
                "budgetScore": {
                    "$cond": {
                        "if": { "$eq": [user_prefs["budget"], "$budgetLevel"] },
                        "then": 10,
                        "else": 0
                    }
                },
                "popScore": { "$multiply": ["$popularity", 0.1] }
            }
        },
        {
            "$addFields": {
                "totalScore": {
                    "$add": ["$tagScore", "$seasonScore", "$styleScore", "$budgetScore", "$popScore"]
                },
                "matchedTags": { "$setIntersection": ["$tags", user_prefs["tags"]] },
                "isSeasonMatch": { "$in": [user_prefs["season"], "$bestSeason"] }
            }
        },
        # Randomly select 6 recommendations
        { "$sample": { "size": 6 } }
    ]

    recs = []
    # Query 'destinations' collection
    # EXCLUDE image_data from result to keep it light
    cursor = db["destinations"].aggregate(pipeline)
    
    async for doc in cursor:
        # Generate Reason
        reason_parts = []
        if doc["styleScore"] > 0 and doc["seasonScore"] > 0:
            reason_parts.append(f"Perfect for your {user_prefs['style']} trip in {user_prefs['season']}")
        if doc["tagScore"] > 0:
            matched = ", ".join(doc["matchedTags"])
            reason_parts.append(f"Matches your interest in {matched}")
        
        reason = ". ".join(reason_parts) if reason_parts else "A highly popular destination."

        # Prefer Wikipedia image URL; fall back to local image proxy
        image_url = doc.get("image_url") or f"/api/recommendation/images/{doc['country']}"

        recs.append({
            "id": str(doc["_id"]),
            "title": doc.get("city") or doc["title"],
            "country": doc["country"],
            "description": doc["description"],
            "imageUrl": image_url,
            "totalScore": doc["totalScore"],
            "reason": reason,
            "author": "System"
        })
    print(f"DEBUG: Found {len(recs)} recommendations")
    return recs

@app.get("/health")
def health_check():
    return {"status": "ok"}
