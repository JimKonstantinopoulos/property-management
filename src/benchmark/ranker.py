"""Score and rank listings to identify the top 1% performers."""

from dataclasses import dataclass

from src.scraper.listing import ListingData


@dataclass
class RankedListing:
    """A listing with its computed benchmark score."""

    listing: ListingData
    score: float = 0.0
    rank: int = 0


def rank_listings(listings: list[ListingData]) -> list[RankedListing]:
    """Rank listings by a composite score and return the top performers.

    Scoring formula (each component normalized 0-100):
        - Rating:       40% weight (most important — guest satisfaction)
        - Review count: 30% weight (social proof + booking volume)
        - Photo count:  15% weight (effort in presentation)
        - Amenities:    15% weight (offering completeness)
    """
    if not listings:
        return []

    # Calculate raw values for normalization
    ratings = [l.rating for l in listings]
    review_counts = [l.review_count for l in listings]
    photo_counts = [len(l.photo_urls) for l in listings]
    amenity_counts = [len(l.amenities) for l in listings]

    scored: list[RankedListing] = []
    for listing in listings:
        rating_score = _normalize(listing.rating, ratings) * 0.40
        review_score = _normalize(listing.review_count, review_counts) * 0.30
        photo_score = _normalize(len(listing.photo_urls), photo_counts) * 0.15
        amenity_score = _normalize(len(listing.amenities), amenity_counts) * 0.15

        total = rating_score + review_score + photo_score + amenity_score
        scored.append(RankedListing(listing=listing, score=round(total, 2)))

    # Sort by score descending
    scored.sort(key=lambda r: r.score, reverse=True)

    # Assign ranks
    for i, ranked in enumerate(scored):
        ranked.rank = i + 1

    return scored


def get_top_percent(
    ranked: list[RankedListing], percent: float = 1.0
) -> list[RankedListing]:
    """Return the top N% of ranked listings.

    Args:
        ranked: Pre-ranked list from rank_listings().
        percent: Top percentage to return (default 1.0 = top 1%).
    """
    if not ranked:
        return []

    count = max(1, int(len(ranked) * percent / 100))
    return ranked[:count]


def _normalize(value: float, all_values: list[float]) -> float:
    """Normalize a value to 0-100 scale based on min/max of all values."""
    min_val = min(all_values)
    max_val = max(all_values)

    if max_val == min_val:
        return 50.0  # All values are the same — give a neutral score

    return ((value - min_val) / (max_val - min_val)) * 100
