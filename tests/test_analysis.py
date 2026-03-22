"""Test the analysis module: compare a lead's listing against top performers."""

import asyncio
import sys
import io
import json
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.scraper.listing import scrape_listing
from src.benchmark.collector import collect_benchmarks
from src.benchmark.ranker import rank_listings, get_top_percent
from src.analysis.photos import compare_photos
from src.analysis.copy import compare_copy


async def main():
    url = input("Paste the lead's Airbnb listing URL: ").strip()
    if not url:
        print("No URL provided. Exiting.")
        return

    # Step 1: Scrape the lead's listing
    print(f"\n[1/4] Scraping lead's listing...")
    lead = await scrape_listing(url)
    print(f"  Title: {lead.title}")
    print(f"  City: {lead.city}")
    print(f"  Photos: {len(lead.photo_urls)}")

    # Step 2: Get benchmarks for the same city
    city = lead.city or "Athens"
    print(f"\n[2/4] Loading benchmarks for {city}...")
    benchmarks = await collect_benchmarks(city, max_results=5)
    ranked = rank_listings(benchmarks)
    top = get_top_percent(ranked, percent=50)
    print(f"  Found {len(benchmarks)} benchmarks, top {len(top)} selected")

    # Step 3: Run photo analysis
    print(f"\n[3/4] Running AI photo analysis...")
    top_photos = []
    for r in top[:3]:
        top_photos.extend(r.listing.photo_urls[:3])

    photo_result = await compare_photos(
        lead_photo_urls=lead.photo_urls,
        top_performer_photo_urls=top_photos,
        lead_sections=lead.photo_sections,
    )

    print(f"\n{'='*60}")
    print("PHOTO ANALYSIS RESULTS")
    print(f"{'='*60}")
    print(f"  Weak photos: {photo_result.weak_photos}")
    print(f"  Estimated impact: {photo_result.estimated_impact}")
    print(f"\n  Suggestions:")
    for i, s in enumerate(photo_result.suggestions, 1):
        print(f"    {i}. {s}")
    if photo_result.section_feedback:
        print(f"\n  Section feedback:")
        for section, feedback in photo_result.section_feedback.items():
            print(f"    [{section}]: {feedback}")

    # Step 4: Run copy analysis
    print(f"\n[4/4] Running AI copy analysis...")
    top_titles = [r.listing.title for r in top]
    top_descriptions = [r.listing.description for r in top]

    copy_result = await compare_copy(
        lead_title=lead.title,
        lead_description=lead.description,
        top_titles=top_titles,
        top_descriptions=top_descriptions,
    )

    print(f"\n{'='*60}")
    print("COPY ANALYSIS RESULTS")
    print(f"{'='*60}")
    print(f"  Title score: {copy_result.title_score}/10")
    print(f"  Description score: {copy_result.description_score}/10")
    print(f"  Suggested title: {copy_result.title_suggestion}")
    print(f"  Tone feedback: {copy_result.tone_feedback}")
    print(f"  Estimated impact: {copy_result.estimated_impact}")
    print(f"\n  Missing keywords: {', '.join(copy_result.missing_keywords)}")
    print(f"\n  Description suggestions:")
    for i, s in enumerate(copy_result.description_suggestions, 1):
        print(f"    {i}. {s}")


if __name__ == "__main__":
    asyncio.run(main())
