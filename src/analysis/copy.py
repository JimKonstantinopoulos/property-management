"""AI-powered listing copy (title + description) comparison."""

import json
from dataclasses import dataclass, field

from anthropic import AsyncAnthropic

from src.utils.config import ANTHROPIC_API_KEY, CLAUDE_MODEL


@dataclass
class CopyAnalysis:
    """Results of comparing a lead's copy against top performers."""

    title_score: int = 0
    description_score: int = 0
    title_suggestion: str = ""
    description_suggestions: list[str] = field(default_factory=list)
    missing_keywords: list[str] = field(default_factory=list)
    tone_feedback: str = ""
    estimated_impact: str = ""


async def compare_copy(
    lead_title: str,
    lead_description: str,
    top_titles: list[str],
    top_descriptions: list[str],
) -> CopyAnalysis:
    """Compare a lead's listing copy against top performers using Claude."""
    client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    prompt = _build_copy_prompt(
        lead_title, lead_description, top_titles, top_descriptions
    )

    response = await client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    return _parse_copy_response(response.content[0].text)


def _build_copy_prompt(
    lead_title: str,
    lead_description: str,
    top_titles: list[str],
    top_descriptions: list[str],
) -> str:
    """Build the text prompt for copy analysis."""
    # Format top performers for comparison
    top_examples = ""
    for i, (title, desc) in enumerate(zip(top_titles, top_descriptions), 1):
        # Truncate long descriptions to keep prompt manageable
        short_desc = desc[:500] + "..." if len(desc) > 500 else desc
        top_examples += f"\n--- Top Performer #{i} ---\n"
        top_examples += f"Title: {title}\n"
        top_examples += f"Description: {short_desc}\n"

    return f"""You are an expert Airbnb listing copywriter and consultant. Compare the lead's listing copy against the top performers in the same city.

--- LEAD'S LISTING ---
Title: {lead_title}
Description: {lead_description}

--- TOP PERFORMERS (benchmark) ---
{top_examples}

Analyze the lead's title and description compared to the top performers.

Respond in this exact JSON format:
{{
  "title_score": <1-10 rating>,
  "description_score": <1-10 rating>,
  "title_suggestion": "A rewritten, improved title for the lead's listing",
  "description_suggestions": [
    "specific improvement 1",
    "specific improvement 2",
    "...up to 5 suggestions"
  ],
  "missing_keywords": ["keyword1", "keyword2", "...keywords top performers use that the lead doesn't"],
  "tone_feedback": "feedback on the overall tone and style compared to top performers",
  "estimated_impact": "estimated impact on bookings (e.g., Could increase click-through by 15-25%)"
}}

Be specific and actionable. Don't just say "improve the title" — write the actual improved title. Compare the lead's word choices, emotional hooks, amenity highlights, and unique selling points against what the top performers do well. Consider SEO keywords that travelers search for."""


def _parse_copy_response(response_text: str) -> CopyAnalysis:
    """Parse Claude's JSON response into a CopyAnalysis object."""
    try:
        text = response_text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        data = json.loads(text)
        return CopyAnalysis(
            title_score=data.get("title_score", 0),
            description_score=data.get("description_score", 0),
            title_suggestion=data.get("title_suggestion", ""),
            description_suggestions=data.get("description_suggestions", []),
            missing_keywords=data.get("missing_keywords", []),
            tone_feedback=data.get("tone_feedback", ""),
            estimated_impact=data.get("estimated_impact", ""),
        )
    except (json.JSONDecodeError, KeyError):
        return CopyAnalysis(
            description_suggestions=[response_text],
            estimated_impact="See suggestions for details",
        )
