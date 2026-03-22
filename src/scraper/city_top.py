"""Scrape top-performing Airbnb listings for a given city."""

import asyncio
import re

from playwright.async_api import async_playwright

from src.scraper.listing import ListingData
from src.scraper.parser import parse_listing_page
from src.utils.config import SCRAPE_DELAY_SECONDS, MAX_TOP_LISTINGS


async def scrape_top_listings(
    city: str, max_results: int | None = None
) -> list[ListingData]:
    """Scrape the top-rated listings in a specific city.

    Searches Airbnb for the given city, sorts by top-rated,
    then scrapes individual listing pages for full data.
    """
    if max_results is None:
        max_results = MAX_TOP_LISTINGS

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
        )
        page = await context.new_page()

        try:
            # Search Airbnb for the city
            search_url = f"https://www.airbnb.com/s/{city.replace(' ', '-')}/homes"
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(SCRAPE_DELAY_SECONDS * 1000)

            # Collect listing URLs from search results
            listing_urls = await _collect_listing_urls(page, max_results)

            # Scrape each listing individually
            listings: list[ListingData] = []
            for url in listing_urls:
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(SCRAPE_DELAY_SECONDS * 1000)

                    listing = await parse_listing_page(page)
                    listing.url = url
                    listing.city = city
                    listings.append(listing)
                except Exception as e:
                    print(f"Failed to scrape {url}: {e}")
                    continue

            return listings
        finally:
            await browser.close()


async def _collect_listing_urls(page, max_results: int) -> list[str]:
    """Extract listing URLs from the Airbnb search results page."""
    urls: list[str] = []

    # Airbnb search results use links with /rooms/ in the href
    links = page.locator("a[href*='/rooms/']")
    count = await links.count()

    seen: set[str] = set()
    for i in range(count):
        href = await links.nth(i).get_attribute("href") or ""
        if "/rooms/" in href:
            # Clean the URL - keep just the base listing URL
            match = re.search(r"/rooms/(\d+)", href)
            if match:
                clean_url = f"https://www.airbnb.com/rooms/{match.group(1)}"
                if clean_url not in seen:
                    seen.add(clean_url)
                    urls.append(clean_url)
                    if len(urls) >= max_results:
                        break

    return urls
