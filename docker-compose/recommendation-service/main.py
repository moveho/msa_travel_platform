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
                # Save external data to 'destinations' for recommendation engine
                # Check for duplicates based on country (not title)
                existing = await db["destinations"].find_one({"country": data["country"], "source": "External Crawler"})
                if not existing:
                    # MATCH IMAGE FROM CACHE
                    country = data.get("country", "")
                    normalized_key = country.lower().replace(" ", "")
                    
                    # Check Aliases first
                    # Remove brackets if any (e.g. "Country [1]") - though crawler does this too
                    
                    # Aliases for file matching
                    # Files: Turkey.jfif, usa.jfif, UAE.jfif, United Kingdom.jfif
                    ALIASES = {
                        "unitedstates": "usa",
                        "america": "usa",
                        "unitedarabemirates": "uae",
                        "uk": "unitedkingdom",
                        "britain": "unitedkingdom",
                        "korea": "southkorea",
                        # Turkey is "turkey" in file, so no alias needed if crawler sends "Turkey"
                    }
                    
                    mapped_key = ALIASES.get(normalized_key, normalized_key)
                    
                    if mapped_key in IMAGE_CACHE:
                        data["image_data"] = IMAGE_CACHE[mapped_key]
                        print(f"Matched image cache for new crawl: {country} -> {mapped_key}")
                    else:
                        # Use DEFAULT image fallback
                        if "default" in IMAGE_CACHE:
                            data["image_data"] = IMAGE_CACHE["default"]
                            print(f"Using default image for: {country} (key: {mapped_key})")
                        else:
                            print(f"WARNING: No image found in cache for: {country} (key: {mapped_key})")

                    await db["destinations"].insert_one(data)
                    print(f"Crawled & Saved: {data['title']}")
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
    # Seed Images from Volume
    try:
        import glob
        image_files = glob.glob("/app/images/*.jfif")
        print(f"Server Startup: Found {len(image_files)} images to seed.")
        
        # 1. Load all images into a dictionary keyed by normalized name
        global IMAGE_CACHE
        IMAGE_CACHE = {} 
        original_names = {}
        
        for file_path in image_files:
            filename = os.path.basename(file_path).replace(".jfif", "")
            # Normalize: lower + remove spaces
            normalized_key = filename.lower().replace(" ", "")
            
            with open(file_path, "rb") as f:
                data = f.read()
                IMAGE_CACHE[normalized_key] = data
                original_names[normalized_key] = filename

        # 2. Iterate ALL destinations and try to match
        cursor = db["destinations"].find({})
        async for doc in cursor:
            country_name = doc.get("country", "")
            # Normalize DB country
            normalized_key = country_name.lower().replace(" ", "")
            
            # Aliases (Sync with consumer)
            ALIASES = {
                "unitedstates": "usa",
                "america": "usa",
                "unitedarabemirates": "uae",
                "uk": "unitedkingdom",
                "britain": "unitedkingdom",
                "korea": "southkorea"
            }
            mapped_key = ALIASES.get(normalized_key, normalized_key)

            if mapped_key in IMAGE_CACHE:
                # Update DB only if image missing or explicitly re-seeding
                # For robustness, let's update if image_data is missing
                if "image_data" not in doc: 
                    await db["destinations"].update_one(
                        {"_id": doc["_id"]},
                        {"$set": {"image_data": IMAGE_CACHE[mapped_key]}}
                    )
                    print(f"Mapped image for: {country_name} -> {mapped_key}")
        
        # Global Cleanup: Remove legacy 'imageUrl' field from ALL documents
        await db["destinations"].update_many(
            {"imageUrl": {"$exists": True}},
            {"$unset": {"imageUrl": ""}}
        )
        print("Cleaned up legacy imageUrl fields.")
            
    except Exception as e:
        print(f"Image seeding failed: {e}")

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

        # Dynamic Image URL served from DB
        # /api/recommendation is mapped to this service
        image_url = f"/api/recommendation/images/{doc['country']}"

        recs.append({
            "id": str(doc["_id"]),
            "title": doc["title"],
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
