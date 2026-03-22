"""Parse raw HTML/page data into clean ListingData models."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from playwright.async_api import Page

if TYPE_CHECKING:
    from src.scraper.listing import ListingData


async def parse_listing_page(page: Page) -> "ListingData":
    """Extract listing data from a fully loaded Airbnb Playwright page."""
    from src.scraper.listing import ListingData

    # Dismiss any blocking modals (cookie consent, translation, etc.)
    await _dismiss_modals(page)

    listing = ListingData()

    # --- Title ---
    listing.title = await _extract_title(page)

    # --- Description ---
    listing.description = await _extract_description(page)

    # --- City / Location ---
    listing.city = await _extract_city(page)

    # --- Price ---
    listing.price_per_night = await _extract_price(page)

    # --- Rating ---
    listing.rating = await _extract_rating(page)

    # --- Review count ---
    listing.review_count = await _extract_review_count(page)

    # --- Photo URLs (opens gallery for full extraction) ---
    listing.photo_urls, listing.photo_sections = await _extract_photo_urls(page)

    # --- Amenities ---
    listing.amenities = await _extract_amenities(page)

    return listing


async def _dismiss_modals(page: Page) -> None:
    """Dismiss cookie consent, translation, or other blocking modals."""
    modal_selectors = [
        "button[aria-label='Close']",
        "button[aria-label='Κλείσιμο']",
        "[data-testid='modal-container'] button",
        "button:has-text('Accept')",
        "button:has-text('Αποδοχή')",
        "button:has-text('OK')",
        "button:has-text('Got it')",
    ]
    for sel in modal_selectors:
        btns = page.locator(sel)
        count = await btns.count()
        for i in range(count):
            try:
                await btns.nth(i).click(timeout=2000)
                await page.wait_for_timeout(300)
            except Exception:
                pass
    await page.wait_for_timeout(500)


async def _extract_title(page: Page) -> str:
    """Extract the listing title."""
    selectors = ["h1", "[data-section-id='TITLE'] h1", "h1.hpipapi"]
    for selector in selectors:
        element = page.locator(selector).first
        if await element.count() > 0:
            text = await element.inner_text()
            if text.strip():
                return text.strip()
    return ""


async def _extract_description(page: Page) -> str:
    """Extract the listing description text."""
    # Try the "About this space" or description section
    selectors = [
        "[data-section-id='DESCRIPTION_DEFAULT'] div",
        "[data-section-id='DESCRIPTION_DEFAULT']",
        "div[data-plugin-in-point-id='DESCRIPTION_DEFAULT']",
    ]
    for selector in selectors:
        element = page.locator(selector).first
        if await element.count() > 0:
            text = await element.inner_text()
            if text.strip() and len(text.strip()) > 20:
                return text.strip()
    return ""


async def _extract_city(page: Page) -> str:
    """Extract the city/location from the listing."""
    content = await page.content()

    # Best source: JSON embedded in the page (works across all locales)
    json_patterns = [
        r'"city":"([^"]+)"',
        r'"localizedCityName":"([^"]+)"',
        r'"marketName":"([^"]+)"',
        r'"locationTitle":"([^"]+)"',
    ]
    for pattern in json_patterns:
        match = re.search(pattern, content)
        if match:
            return match.group(1)

    # Fallback: extract from the page title
    # Works for both English ("in Athens") and Greek ("στην/στο Αθήνα")
    page_title = await page.title()
    for separator in [" in ", " στην/στο ", " στην ", " στο "]:
        if separator in page_title:
            city = page_title.split(separator)[-1].split(" -")[0].split(",")[0].strip()
            if city:
                return city
    return ""


async def _extract_price(page: Page) -> float:
    """Extract the price per night."""
    # Try the booking sidebar — look for visible price with currency symbols
    # Matches patterns like "€ 173", "$150", "€85", "£120"
    book_section = page.locator(
        "[data-testid='book-it-default'], "
        "[data-plugin-in-point-id='BOOK_IT_SIDEBAR']"
    )
    if await book_section.count() > 0:
        text = await book_section.first.inner_text()
        # Look for currency + number patterns (handles "€ 173", "$150", "€85")
        price_match = re.search(r"[€$£]\s*([\d,.]+)", text)
        if price_match:
            return float(price_match.group(1).replace(",", "").replace(".", "")
                         if "," in price_match.group(1) and "." in price_match.group(1)
                         else price_match.group(1).replace(",", ""))

    # Fallback: scan for price pattern anywhere visible on page
    all_text = await page.locator("body").inner_text()
    # Match "€ 85 / night" or "$150 night" patterns
    night_price = re.search(r"[€$£]\s*([\d,.]+)\s*/?\s*(?:night|νύχτα|βραδ)", all_text)
    if night_price:
        raw = night_price.group(1).replace(",", "")
        return float(raw)

    # Last fallback: JSON in page source
    content = await page.content()
    for pattern in [r'"priceString":"[^"]*?([\d,]+)', r'"price":(\d+)', r'"basePrice":(\d+)']:
        match = re.search(pattern, content)
        if match:
            return float(match.group(1).replace(",", ""))
    return 0.0


async def _extract_rating(page: Page) -> float:
    """Extract the listing rating (e.g., 4.92)."""
    # Try structured data in the page
    content = await page.content()
    rating_match = re.search(r'"ratingValue":\s*([\d.]+)', content)
    if rating_match:
        return float(rating_match.group(1))

    # Try visible rating element
    selectors = [
        "span[aria-label*='rating']",
        "span._17p6nbba",
    ]
    for selector in selectors:
        element = page.locator(selector).first
        if await element.count() > 0:
            text = await element.inner_text()
            numbers = re.findall(r"[\d.]+", text)
            if numbers:
                return float(numbers[0])
    return 0.0


async def _extract_review_count(page: Page) -> int:
    """Extract the number of reviews."""
    content = await page.content()
    review_match = re.search(r'"reviewCount":\s*(\d+)', content)
    if review_match:
        return int(review_match.group(1))

    # Try visible review count
    selectors = [
        "a[href*='reviews'] span",
        "button[aria-label*='review']",
    ]
    for selector in selectors:
        element = page.locator(selector).first
        if await element.count() > 0:
            text = await element.inner_text()
            numbers = re.findall(r"\d+", text)
            if numbers:
                return int(numbers[0])
    return 0


async def _extract_photo_urls(page: Page) -> tuple[list[str], dict[str, list[str]]]:
    """Extract all listing photo URLs organized by section.

    Opens the photo gallery modal to get every photo, then groups
    them by section (Bedroom, Bathroom, Rooftop, etc.).

    Returns:
        A tuple of (flat list of all photo URLs, dict of section -> URLs).
    """
    # Open the photo gallery by clicking "Show all photos"
    gallery_opened = await _open_photo_gallery(page)

    if gallery_opened:
        # Extract photos grouped by section from the gallery
        sections = await _extract_gallery_sections(page)

        # Build the flat list from non-overview sections only.
        # Overview photos are highlights the owner picked from other sections,
        # so they're duplicates and shouldn't be counted in the total.
        all_photos: list[str] = []
        seen: set[str] = set()
        for section_name, urls in sections.items():
            if section_name == "overview":
                continue
            for url in urls:
                if url not in seen:
                    seen.add(url)
                    all_photos.append(url)

        # Close the gallery modal
        close_btn = page.locator("button[aria-label='Close'], button[aria-label='Κλείσιμο']")
        if await close_btn.count() > 0:
            try:
                await close_btn.first.click(timeout=2000)
            except Exception:
                pass

        if all_photos:
            return all_photos, sections

    # Fallback: extract from main page source if gallery didn't open
    content = await page.content()
    photos = _extract_photos_from_source(content)
    return photos, {"all": photos}


async def _open_photo_gallery(page: Page) -> bool:
    """Click the 'Show all photos' button and scroll to load all images."""
    btn_selectors = [
        "button:has-text('φωτογραφ')",
        "button:has-text('photo')",
        "button:has-text('Show all')",
    ]
    for sel in btn_selectors:
        btn = page.locator(sel)
        count = await btn.count()
        for i in range(count):
            try:
                text = await btn.nth(i).inner_text()
                if "φωτογραφ" in text.lower() or "photo" in text.lower():
                    await btn.nth(i).click(timeout=5000)
                    await page.wait_for_timeout(2000)
                    # Scroll through the gallery to trigger lazy loading
                    await _scroll_gallery(page)
                    return True
            except Exception:
                try:
                    await btn.nth(i).click(force=True, timeout=3000)
                    await page.wait_for_timeout(2000)
                    await _scroll_gallery(page)
                    return True
                except Exception:
                    continue
    return False


async def _scroll_gallery(page: Page) -> None:
    """Scroll through the photo gallery modal to load all lazy images."""
    # Find the scrollable container inside the modal and scroll it fully
    await page.evaluate("""
    async () => {
        // Find the scrollable div (the one whose scrollHeight > clientHeight)
        const all = document.querySelectorAll('div');
        let scrollable = null;
        for (const el of all) {
            const style = getComputedStyle(el);
            if ((style.overflowY === 'auto' || style.overflowY === 'scroll')
                && el.scrollHeight > el.clientHeight + 100) {
                scrollable = el;
            }
        }
        if (!scrollable) return;

        // Scroll to bottom in steps
        for (let i = 0; i < 30; i++) {
            scrollable.scrollBy(0, 600);
            await new Promise(r => setTimeout(r, 200));
        }
    }
    """)
    await page.wait_for_timeout(1000)


async def _extract_gallery_sections(page: Page) -> dict[str, list[str]]:
    """Extract photos grouped by section headers from the gallery modal.

    Uses JavaScript to walk the DOM in order, tracking which header
    each image falls under (headers and images are siblings in the gallery).
    """
    items = await page.evaluate("""
    () => {
        const gallery = document.querySelector('[data-testid="modal-container"]') || document.body;
        const elements = gallery.querySelectorAll('h2, h3, img[src*="muscache"]');
        const result = [];
        for (const el of elements) {
            if (el.tagName === 'H2' || el.tagName === 'H3') {
                const text = el.textContent.trim();
                if (text) result.push({type: 'header', text: text});
            } else if (el.tagName === 'IMG') {
                const src = el.getAttribute('src') || '';
                if (src.includes('muscache')
                    && !src.includes('platform-assets')
                    && !src.includes('PlatformAssets')
                    && !src.includes('/user/')
                    && !src.includes('Favicon')) {
                    result.push({type: 'img', src: src});
                }
            }
        }
        return result;
    }
    """)

    sections: dict[str, list[str]] = {}
    current_section = "overview"

    for item in items:
        if item["type"] == "header":
            current_section = item["text"]
        else:
            url = re.sub(r"\?.*", "", item["src"])
            # Deduplicate within each section only (not across sections,
            # because overview photos are highlights duplicated from other sections)
            section_list = sections.setdefault(current_section, [])
            if url not in section_list:
                section_list.append(url)

    return sections


def _extract_photos_from_source(content: str) -> list[str]:
    """Fallback: extract listing photos from raw page source."""
    all_urls = re.findall(r'https://a0\.muscache\.com/im/pictures/[^"\\]+', content)
    photos: list[str] = []
    seen: set[str] = set()
    for url in all_urls:
        clean = re.sub(r"\?.*", "", url)
        if not _is_platform_asset(clean) and clean not in seen:
            seen.add(clean)
            photos.append(clean)
    return photos


def _is_platform_asset(url: str) -> bool:
    """Check if a URL is an Airbnb UI asset rather than a listing photo."""
    skip_patterns = [
        "airbnb-platform-assets",   # UI icons (search bar, nav, etc.)
        "AirbnbPlatformAssets",     # Review AI synthesis icons, misc UI
        "Favicons",                 # Site favicons
        "/user/",                   # User profile photos (host avatars)
    ]
    return any(pattern in url for pattern in skip_patterns)


async def _extract_amenities(page: Page) -> list[str]:
    """Extract the list of amenities."""
    amenities: list[str] = []

    # Try clicking "Show all amenities" button if it exists
    show_all = page.locator("button:has-text('Show all'), button:has-text('amenities')")
    if await show_all.count() > 0:
        try:
            await show_all.first.click()
            await page.wait_for_timeout(1000)
        except Exception:
            pass

    # Extract amenity items from the modal or the page
    selectors = [
        "[data-section-id='AMENITIES_DEFAULT'] div._19xnuo97",
        "[data-testid='amenity-row']",
        "div[data-section-id='AMENITIES_DEFAULT'] li",
    ]
    for selector in selectors:
        items = page.locator(selector)
        count = await items.count()
        if count > 0:
            for i in range(count):
                text = await items.nth(i).inner_text()
                cleaned = text.strip().split("\n")[0]
                if cleaned and cleaned not in amenities:
                    amenities.append(cleaned)
            break

    # Close modal if opened
    close_btn = page.locator("button[aria-label='Close']")
    if await close_btn.count() > 0:
        try:
            await close_btn.first.click()
        except Exception:
            pass

    return amenities
