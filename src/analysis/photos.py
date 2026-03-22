"""AI-powered photo comparison using Claude's vision capabilities."""

import base64
import json
from dataclasses import dataclass, field

import httpx
from anthropic import AsyncAnthropic

from src.utils.config import ANTHROPIC_API_KEY, CLAUDE_MODEL


@dataclass
class PhotoAnalysis:
    """Results of comparing a lead's photos against top performers."""

    weak_photos: list[int] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    section_feedback: dict[str, str] = field(default_factory=dict)
    estimated_impact: str = ""


# Max photos to send to Claude (API has token limits for images)
MAX_LEAD_PHOTOS = 10
MAX_TOP_PHOTOS = 6


async def compare_photos(
    lead_photo_urls: list[str],
    top_performer_photo_urls: list[str],
    lead_sections: dict[str, list[str]] | None = None,
) -> PhotoAnalysis:
    """Compare a lead's listing photos against top performers using Claude.

    Sends both sets of photos to Claude's vision model and asks for
    a detailed comparison with specific improvement recommendations.
    """
    client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    # Download and encode photos as base64 for the API
    lead_images = await _download_photos(lead_photo_urls[:MAX_LEAD_PHOTOS])
    top_images = await _download_photos(top_performer_photo_urls[:MAX_TOP_PHOTOS])

    if not lead_images:
        return PhotoAnalysis(
            suggestions=["Could not download lead's photos for analysis."],
            estimated_impact="Unable to estimate",
        )

    # Build the message with images
    content = _build_photo_prompt(lead_images, top_images, lead_sections)

    response = await client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": content}],
    )

    # Parse Claude's response into structured data
    return _parse_photo_response(response.content[0].text)


async def _download_photos(urls: list[str]) -> list[dict]:
    """Download photos and return them as base64-encoded dicts."""
    images = []
    async with httpx.AsyncClient(timeout=15.0) as client:
        for url in urls:
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    content_type = resp.headers.get("content-type", "image/jpeg")
                    # Normalize content type
                    if "jpeg" in content_type or "jpg" in content_type:
                        media_type = "image/jpeg"
                    elif "png" in content_type:
                        media_type = "image/png"
                    elif "webp" in content_type:
                        media_type = "image/webp"
                    else:
                        media_type = "image/jpeg"

                    b64 = base64.b64encode(resp.content).decode("utf-8")
                    images.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": b64,
                        },
                    })
            except Exception:
                continue
    return images


def _build_photo_prompt(
    lead_images: list[dict],
    top_images: list[dict],
    lead_sections: dict[str, list[str]] | None,
) -> list[dict]:
    """Build the multimodal prompt with lead and top performer photos."""
    content: list[dict] = []

    # Instructions
    content.append({
        "type": "text",
        "text": (
            "You are an expert Airbnb listing consultant. I'm going to show you "
            "two sets of photos:\n\n"
            "SET A: A lead's current listing photos (the ones that need improvement)\n"
            "SET B: Top-performing listings in the same city (the benchmark)\n\n"
            "Compare them and provide a detailed analysis."
        ),
    })

    # Lead's photos
    content.append({"type": "text", "text": "\n--- SET A: LEAD'S LISTING PHOTOS ---"})
    for i, img in enumerate(lead_images):
        content.append({"type": "text", "text": f"Lead photo #{i + 1}:"})
        content.append(img)

    # Top performer photos
    if top_images:
        content.append({
            "type": "text",
            "text": "\n--- SET B: TOP PERFORMER PHOTOS (benchmark) ---",
        })
        for i, img in enumerate(top_images):
            content.append({"type": "text", "text": f"Top performer photo #{i + 1}:"})
            content.append(img)

    # Analysis request
    section_context = ""
    if lead_sections:
        section_names = ", ".join(lead_sections.keys())
        section_context = f"\nThe lead's photos are organized in these sections: {section_names}."

    content.append({
        "type": "text",
        "text": (
            f"\n\nAnalyze the lead's photos compared to the top performers.{section_context}"
            "\n\nRespond in this exact JSON format:\n"
            "{\n"
            '  "weak_photos": [list of photo numbers (1-based) that need improvement],\n'
            '  "suggestions": [\n'
            '    "specific actionable suggestion 1",\n'
            '    "specific actionable suggestion 2",\n'
            '    "...up to 5 suggestions"\n'
            "  ],\n"
            '  "section_feedback": {\n'
            '    "section name": "feedback for that section",\n'
            '    "..."\n'
            "  },\n"
            '  "estimated_impact": "estimated impact on bookings (e.g., Could increase bookings by 10-20%)"\n'
            "}\n\n"
            "Focus on: lighting, staging, angles, resolution, professional quality, "
            "hero shot strength, room coverage, and emotional appeal. "
            "Be specific — don't say 'improve lighting', say 'Photo #3 bedroom shot "
            "is underexposed — reshoot with natural daylight from the window, "
            "similar to top performer #2'."
        ),
    })

    return content


def _parse_photo_response(response_text: str) -> PhotoAnalysis:
    """Parse Claude's JSON response into a PhotoAnalysis object."""
    try:
        # Extract JSON from response (Claude may wrap it in markdown)
        text = response_text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        data = json.loads(text)
        return PhotoAnalysis(
            weak_photos=data.get("weak_photos", []),
            suggestions=data.get("suggestions", []),
            section_feedback=data.get("section_feedback", {}),
            estimated_impact=data.get("estimated_impact", ""),
        )
    except (json.JSONDecodeError, KeyError):
        # If parsing fails, return the raw text as a single suggestion
        return PhotoAnalysis(
            suggestions=[response_text],
            estimated_impact="See suggestions for details",
        )
