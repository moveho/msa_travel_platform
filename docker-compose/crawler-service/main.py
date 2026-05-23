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

WIKIPEDIA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

async def get_kafka_producer():
    logger.info(f"Connecting to Kafka at {KAFKA_BOOTSTRAP_SERVERS}...")
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    await producer.start()
    logger.info("Kafka producer connected.")
    return producer

def get_wikipedia_thumbnail(city_name, country_name):
    """Fetch thumbnail URL from Wikipedia page summary API. Try city first, then country."""
    for title in [city_name, country_name]:
        if not title:
            continue
        try:
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title.replace(' ', '_')}"
            resp = requests.get(url, headers=WIKIPEDIA_HEADERS, timeout=5)
            if resp.status_code == 200:
                thumbnail = resp.json().get("thumbnail", {}).get("source")
                if thumbnail:
                    logger.debug(f"Thumbnail found for '{title}': {thumbnail}")
                    return thumbnail
        except Exception as e:
            logger.debug(f"Thumbnail fetch failed for '{title}': {e}")
    logger.debug(f"No thumbnail found for city='{city_name}', country='{country_name}'")
    return None

def scrape_travel_data():
    """
    Scrapes travel data from Wikipedia's List of cities by international visitors.
    Supports multiple tables (2016, 2018, latest rankings) and batch processing.
    Also fetches Wikipedia thumbnail URLs for each city/country.
    """
    logger.info(f"Scraping {TARGET_URL}...")
    try:
        response = requests.get(TARGET_URL, headers=WIKIPEDIA_HEADERS)
        if response.status_code != 200:
            logger.error(f"Failed to fetch page: {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')

        # Find ALL wikitables (includes 2016, 2018, latest rankings)
        tables = soup.find_all('table', {'class': 'wikitable'})
        if not tables:
            logger.warning("Could not find any wikitables")
            return []

        logger.info(f"Found {len(tables)} wikitables on page")

        # Randomly select one table to diversify data
        table = random.choice(tables)
        rows = table.find_all('tr')[1:]  # Skip header

        if not rows:
            logger.warning("No rows found in selected table")
            return []

        # Batch process: randomly select 5-10 rows instead of 1
        num_rows = min(random.randint(5, 10), len(rows))
        selected_rows = random.sample(rows, num_rows)
        logger.info(f"Processing {num_rows} rows from selected table")

        import re
        results = []
        for row in selected_rows:
            cols = row.find_all('td')

            # Find cells that contain Wikipedia article links — reliably identifies city/country
            # regardless of how many rank/trend columns precede them in the table
            linked_cols = [c for c in cols if c.find('a', href=lambda h: h and h.startswith('/wiki/'))]

            if len(linked_cols) < 2:
                logger.debug("Skipping row with insufficient linked columns")
                continue

            city_col = linked_cols[0]
            country_col = linked_cols[1]

            city_name = re.sub(r'\[.*?\]', '', city_col.get_text(strip=True)).strip()
            country_name = re.sub(r'\[.*?\]', '', country_col.get_text(strip=True)).strip()

            logger.debug(f"Extracted: {country_name} (city: {city_name})")

            # Fetch Wikipedia thumbnail (city preferred over country)
            image_url = get_wikipedia_thumbnail(city_name, country_name)

            data = {
                "title": city_name,
                "city": city_name,
                "country": country_name,
                "description": f"Visit {city_name} and explore the beauty of {country_name}. A top international destination discovered by our global crawler.",
                "image_url": image_url,
                "tags": ["Popular", "City", "Global"],
                "bestSeason": [random.choice(["Spring", "Summer", "Autumn", "Winter"])],
                "travelStyle": [random.choice(["Solo", "Family", "Friends"])],
                "budgetLevel": random.choice(["High", "Medium", "Low"]),
                "popularity": random.randint(80, 100),
                "source": "External Crawler"
            }
            results.append(data)

        return results
    except Exception as e:
        logger.exception(f"Scraping failed: {e}")
        return []

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
            results = scrape_travel_data()
            if results:
                for data in results:
                    message = json.dumps(data).encode("utf-8")
                    await producer.send_and_wait(TOPIC_NAME, message)
                    logger.info(f"Published: {data['title']} (image: {'yes' if data.get('image_url') else 'none'})")
            else:
                logger.warning("No data scraped in this cycle")

            # Wait for 30 seconds before next scrape
            await asyncio.sleep(30)
    finally:
        await producer.stop()

if __name__ == "__main__":
    asyncio.run(run_crawler())
