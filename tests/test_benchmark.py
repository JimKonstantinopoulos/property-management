"""Test the benchmark module: collect top listings and rank them."""

import asyncio
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.benchmark.collector import collect_benchmarks
from src.benchmark.ranker import rank_listings, get_top_percent


async def main():
    city = input("Enter a city name (e.g., Athens): ").strip()
    if not city:
        print("No city provided. Exiting.")
        return

    max_results = input("How many listings to scrape? (default 5): ").strip()
    max_results = int(max_results) if max_results else 5

    print(f"\nCollecting top listings for {city} (max {max_results})...")
    print("This will take a while — scraping multiple listings...\n")

    listings = await collect_benchmarks(city, max_results=max_results)

    if not listings:
        print("No listings found. Try a different city name.")
        return

    print(f"\nScraped {len(listings)} listings. Ranking them...\n")

    ranked = rank_listings(listings)
    top = get_top_percent(ranked, percent=50)  # Top 50% for small samples

    print("=" * 70)
    print(f"{'Rank':<6} {'Score':<8} {'Rating':<8} {'Reviews':<9} {'Photos':<8} {'Title'}")
    print("=" * 70)
    for r in ranked:
        title = r.listing.title[:40] if r.listing.title else "(no title)"
        marker = " <-- TOP" if r in top else ""
        print(
            f"#{r.rank:<5} {r.score:<8} {r.listing.rating:<8} "
            f"{r.listing.review_count:<9} {len(r.listing.photo_urls):<8} "
            f"{title}{marker}"
        )
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
