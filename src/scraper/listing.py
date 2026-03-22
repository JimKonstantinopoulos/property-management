"""Scrape a single Airbnb listing page."""

import asyncio
from dataclasses import dataclass, field

from playwright.async_api import async_playwright

from src.scraper.parser import parse_listing_page
from src.utils.config import SCRAPE_DELAY_SECONDS


@dataclass
class ListingData:
    """Data extracted from a single Airbnb listing."""

    url: str = ""
    title: str = ""
    description: str = ""
    city: str = ""
    price_per_night: float = 0.0
    rating: float = 0.0
    review_count: int = 0
    photo_urls: list[str] = field(default_factory=list)
    photo_sections: dict[str, list[str]] = field(default_factory=dict)
    amenities: list[str] = field(default_factory=list)


async def scrape_listing(url: str) -> ListingData:
    """Scrape a single Airbnb listing and return structured data.

    Launches a headless browser, navigates to the listing URL,
    waits for content to load, then extracts all listing data.
    """
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
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            # Wait for the main content to appear
            await page.wait_for_timeout(SCRAPE_DELAY_SECONDS * 1000)

            listing = await parse_listing_page(page)
            listing.url = url

            return listing
        finally:
            await browser.close()
