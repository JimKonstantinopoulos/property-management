"""Test the full pipeline: scrape -> analyze -> generate PDF report."""

import asyncio
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.scraper.listing import scrape_listing
from src.benchmark.collector import collect_benchmarks
from src.benchmark.ranker import rank_listings, get_top_percent
from src.analysis.photos import compare_photos
from src.analysis.copy import compare_copy
from src.reports.pdf_builder import generate_report
from src.utils.config import OUTPUT_DIR


async def main():
    url = input("Paste the lead's Airbnb listing URL: ").strip()
    if not url:
        print("No URL provided. Exiting.")
        return

    # Step 1: Scrape
    print(f"\n[1/5] Scraping lead's listing...")
    lead = await scrape_listing(url)
    print(f"  -> {lead.title} ({lead.city})")

    # Step 2: Benchmarks
    city = lead.city or "Athens"
    print(f"\n[2/5] Loading benchmarks for {city}...")
    benchmarks = await collect_benchmarks(city, max_results=5)
    ranked = rank_listings(benchmarks)
    top = get_top_percent(ranked, percent=50)
    print(f"  -> {len(top)} top performers selected")

    # Step 3: Photo analysis
    print(f"\n[3/5] AI photo analysis...")
    top_photos = []
    for r in top[:3]:
        top_photos.extend(r.listing.photo_urls[:3])
    photo_result = await compare_photos(
        lead.photo_urls, top_photos, lead.photo_sections
    )
    print(f"  -> {len(photo_result.suggestions)} suggestions")

    # Step 4: Copy analysis
    print(f"\n[4/5] AI copy analysis...")
    copy_result = await compare_copy(
        lead.title, lead.description,
        [r.listing.title for r in top],
        [r.listing.description for r in top],
    )
    print(f"  -> Title: {copy_result.title_score}/10, Description: {copy_result.description_score}/10")

    # Step 5: Generate PDF
    print(f"\n[5/5] Generating PDF report...")
    safe_title = "".join(c for c in lead.title[:30] if c.isalnum() or c in " -_") or "listing"
    output_path = OUTPUT_DIR / f"audit_{safe_title.strip()}.pdf"

    result_path = generate_report(lead, photo_result, copy_result, output_path)
    print(f"\n  PDF saved to: {result_path}")
    print(f"  Open it to review the report!")


if __name__ == "__main__":
    asyncio.run(main())
