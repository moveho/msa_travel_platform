import asyncio
import json
import os
import random
from aiokafka import AIOKafkaProducer
import requests
from bs4 import BeautifulSoup

import logging
import sys

# Configure Logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("crawler-service")

# Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
TOPIC_NAME = "external-travel-topic"
TARGET_URL = "https://en.wikipedia.org/wiki/List_of_cities_by_international_visitors"

async def get_kafka_producer():
    logger.info(f"Connecting to Kafka at {KAFKA_BOOTSTRAP_SERVERS}...")
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    await producer.start()
    logger.info("Kafka producer connected.")
    return producer

def scrape_travel_data():
    """
    Scrapes travel data from Wikipedia's List of cities by international visitors.
    """
    logger.info(f"Scraping {TARGET_URL}...")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(TARGET_URL, headers=headers)
        if response.status_code != 200:
            logger.error(f"Failed to fetch page: {response.status_code}")
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the first table (usually the main ranking table)
        table = soup.find('table', {'class': 'wikitable'})
        if not table:
            logger.warning("Could not find wikitable")
            return None
            
        rows = table.find_all('tr')[1:] # Skip header
        
        # Pick a random row to process
        if not rows:
            logger.warning("No rows found in table")
            return None
            
        row = random.choice(rows)
        cols = row.find_all('td')
        
        if len(cols) < 2:
            logger.debug("Skipping row with insufficient columns")
            return None
            
        # Extract City and Country (Adjust indices based on actual table structure)
        # Wikipedia tables vary, but usually City is 0 or 1, Country is 1 or 2.
        # Let's assume standard layout: Rank, City, Country, ...
        city_col = cols[1]
        country_col = cols[2]
        
        city_name = city_col.get_text(strip=True)
        country_name = country_col.get_text(strip=True)
        
        # Clean up names (remove references like [1])
        import re
        city_name = re.sub(r'\[.*?\]', '', city_name)
        country_name = re.sub(r'\[.*?\]', '', country_name)
        
        title = f"{city_name}, {country_name}"
        logger.debug(f"Extracted: {title}")
        
        # Generate metadata
        data = {
            "title": title,
            "country": country_name,
            "description": f"A top international destination in {country_name}. Discovered by our global crawler.",
            "tags": ["Popular", "City", "Global"],
            "bestSeason": [random.choice(["Spring", "Summer", "Autumn", "Winter"])],
            "travelStyle": [random.choice(["Solo", "Family", "Friends"])],
            "budgetLevel": random.choice(["High", "Medium", "Low"]),
            "popularity": random.randint(80, 100),
            # Use LoremFlickr for reliable keyword-based images
            "imageUrl": f"https://loremflickr.com/800/600/{city_name.replace(' ', ',')}/travel",
            "source": "External Crawler"
        }
        return data
    except Exception as e:
        logger.exception(f"Scraping failed: {e}")
        return None

async def run_crawler():
    producer = None
    while not producer:
        try:
            producer = await get_kafka_producer()
        except Exception as e:
            logger.error(f"Kafka connection failed: {e}. Retrying in 5s...")
            await asyncio.sleep(5)

    logger.info("Crawler started. Publishing to Kafka...")
    
    try:
        while True:
            data = scrape_travel_data()
            if data:
                message = json.dumps(data).encode("utf-8")
                await producer.send_and_wait(TOPIC_NAME, message)
                logger.info(f"Published: {data['title']}")
            
            # Wait for 30 seconds before next scrape
            await asyncio.sleep(30)
    finally:
        await producer.stop()

if __name__ == "__main__":
    asyncio.run(run_crawler())
