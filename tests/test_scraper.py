"""Quick test script to verify the scraper works on a real Airbnb listing."""

import asyncio
import sys
import io
from pathlib import Path

# Fix Windows console encoding for non-Latin characters (Greek, etc.)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.scraper.listing import scrape_listing


async def main():
    # Replace this with any real Airbnb listing URL to test
    url = input("Paste an Airbnb listing URL: ").strip()

    if not url:
        print("No URL provided. Exiting.")
        return

    print(f"\nScraping: {url}")
    print("This may take a few seconds (loading browser + page)...\n")

    listing = await scrape_listing(url)

    print("=" * 60)
    print(f"Title:          {listing.title}")
    print(f"City:           {listing.city}")
    print(f"Price/night:    ${listing.price_per_night}")
    print(f"Rating:         {listing.rating}")
    print(f"Reviews:        {listing.review_count}")
    print(f"Total photos:   {len(listing.photo_urls)}")
    print(f"Photo sections: {len(listing.photo_sections)}")
    print(f"Amenities:      {len(listing.amenities)}")
    print("=" * 60)

    if listing.photo_sections:
        print(f"\nPhotos by section:")
        for section, urls in listing.photo_sections.items():
            print(f"  {section}: {len(urls)} photos")

    if listing.amenities:
        print(f"\nFirst 10 amenities:")
        for amenity in listing.amenities[:10]:
            print(f"  - {amenity}")

    if listing.description:
        print(f"\nDescription (first 200 chars):")
        print(f"  {listing.description[:200]}...")


if __name__ == "__main__":
    asyncio.run(main())
