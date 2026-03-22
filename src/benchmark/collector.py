"""Collect and cache top 1% benchmark data per city."""

import json
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path

from src.scraper.city_top import scrape_top_listings
from src.scraper.listing import ListingData
from src.utils.config import DATA_DIR, MAX_TOP_LISTINGS

# Cache expires after 7 days — top listings don't change that fast
CACHE_EXPIRY_DAYS = 7


async def collect_benchmarks(
    city: str,
    cache_dir: Path | None = None,
    max_results: int | None = None,
    force_refresh: bool = False,
) -> list[ListingData]:
    """Collect top listings for a city, using cache if available.

    Checks if we already have recent benchmark data for the city.
    If yes, loads from cache. If no (or expired), scrapes fresh data
    and saves it to cache for next time.
    """
    if cache_dir is None:
        cache_dir = DATA_DIR
    if max_results is None:
        max_results = MAX_TOP_LISTINGS

    cache_file = _get_cache_path(city, cache_dir)

    # Try loading from cache first
    if not force_refresh and cache_file.exists():
        cached = _load_cache(cache_file)
        if cached is not None:
            print(f"Loaded {len(cached)} cached benchmarks for {city}")
            return cached

    # No valid cache — scrape fresh data
    print(f"Scraping top listings for {city}...")
    listings = await scrape_top_listings(city, max_results=max_results)

    if listings:
        _save_cache(listings, cache_file)
        print(f"Cached {len(listings)} benchmarks for {city}")

    return listings


def _get_cache_path(city: str, cache_dir: Path) -> Path:
    """Generate the cache file path for a given city."""
    safe_name = city.lower().replace(" ", "_").replace("/", "_")
    return cache_dir / f"benchmarks_{safe_name}.json"


def _load_cache(cache_file: Path) -> list[ListingData] | None:
    """Load benchmark data from cache if it exists and isn't expired."""
    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))

        # Check if cache has expired
        cached_at = datetime.fromisoformat(data["cached_at"])
        if datetime.now() - cached_at > timedelta(days=CACHE_EXPIRY_DAYS):
            print(f"Cache expired (older than {CACHE_EXPIRY_DAYS} days)")
            return None

        # Rebuild ListingData objects from cached dicts
        listings = [ListingData(**entry) for entry in data["listings"]]
        return listings

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"Cache file corrupted, will re-scrape: {e}")
        return None


def _save_cache(listings: list[ListingData], cache_file: Path) -> None:
    """Save benchmark data to a JSON cache file."""
    cache_file.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "cached_at": datetime.now().isoformat(),
        "city": listings[0].city if listings else "",
        "count": len(listings),
        "listings": [asdict(listing) for listing in listings],
    }

    cache_file.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
