"""Generate the final PDF audit report using FPDF2."""

import io
import re
import tempfile
from datetime import datetime
from pathlib import Path

import httpx
from fpdf import FPDF
from PIL import Image

from src.analysis.copy import CopyAnalysis
from src.analysis.photos import PhotoAnalysis
from src.scraper.listing import ListingData


# Colors (RGB)
COLOR_PRIMARY = (41, 98, 255)     # Blue
COLOR_DARK = (30, 30, 30)         # Near black
COLOR_GREY = (100, 100, 100)      # Body text
COLOR_LIGHT_BG = (245, 247, 250)  # Light background
COLOR_GREEN = (16, 185, 129)      # Good / positive
COLOR_RED = (239, 68, 68)         # Needs improvement
COLOR_ORANGE = (245, 158, 11)     # Warning

# Font
FONT_DIR = Path(__file__).resolve().parent / "fonts"
FONT_NAME = "DejaVu"


class AuditReport(FPDF):
    """Custom FPDF subclass for the listing audit report."""

    def __init__(self):
        super().__init__()
        self.add_font(FONT_NAME, "", str(FONT_DIR / "DejaVuSans.ttf"))
        self.add_font(FONT_NAME, "B", str(FONT_DIR / "DejaVuSans-Bold.ttf"))
        self.add_font(FONT_NAME, "I", str(FONT_DIR / "DejaVuSans-Oblique.ttf"))

    def header(self):
        self.set_font(FONT_NAME, "B", 10)
        self.set_text_color(*COLOR_PRIMARY)
        self.cell(0, 8, "AIRBNB LISTING AUDIT REPORT", align="L")
        self.set_text_color(*COLOR_GREY)
        self.cell(0, 8, datetime.now().strftime("%B %d, %Y"), align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*COLOR_PRIMARY)
        self.set_line_width(0.5)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font(FONT_NAME, "I", 8)
        self.set_text_color(*COLOR_GREY)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


def generate_report(
    lead: ListingData,
    photo_analysis: PhotoAnalysis,
    copy_analysis: CopyAnalysis,
    output_path: Path,
) -> Path:
    """Generate a PDF report with listing audit results."""
    pdf = AuditReport()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # Only download photos that are referenced as weak/needing improvement
    print("  Downloading referenced photos for PDF...")
    photo_cache = _download_weak_photos(lead.photo_urls, photo_analysis)

    # --- Title Page Section ---
    _add_title_section(pdf, lead)

    # --- Listing Overview ---
    _add_listing_overview(pdf, lead)

    # --- Photo Analysis with inline photos ---
    _add_photo_analysis(pdf, photo_analysis, photo_cache)

    # --- Copy Analysis ---
    _add_copy_analysis(pdf, copy_analysis)

    # --- Action Summary ---
    _add_action_summary(pdf, photo_analysis, copy_analysis)

    # Save the PDF
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_path))

    # Clean up temp files
    for tmp_path in photo_cache.values():
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass

    return output_path


def _download_weak_photos(
    photo_urls: list[str],
    analysis: PhotoAnalysis,
) -> dict[int, Path]:
    """Download only the photos referenced in the analysis."""
    # Collect all photo numbers mentioned in weak_photos and suggestions
    needed: set[int] = set(analysis.weak_photos)
    for suggestion in analysis.suggestions:
        for match in re.findall(r"#(\d+)", suggestion):
            needed.add(int(match))

    cache: dict[int, Path] = {}
    tmp_dir = Path(tempfile.mkdtemp(prefix="airbnb_photos_"))

    with httpx.Client(timeout=15.0) as client:
        for num in sorted(needed):
            idx = num - 1  # Photo numbers are 1-based
            if idx < 0 or idx >= len(photo_urls):
                continue
            try:
                resp = client.get(photo_urls[idx])
                if resp.status_code != 200:
                    continue

                tmp_path = tmp_dir / f"photo_{num}.jpg"
                img = Image.open(io.BytesIO(resp.content))
                img = img.convert("RGB")
                img.save(str(tmp_path), "JPEG", quality=85)
                cache[num] = tmp_path
            except Exception:
                continue

    return cache


def _add_title_section(pdf: AuditReport, lead: ListingData) -> None:
    """Add the main title and listing name."""
    pdf.ln(10)
    pdf.set_font(FONT_NAME, "B", 24)
    pdf.set_text_color(*COLOR_DARK)
    pdf.cell(0, 12, "Listing Audit Report", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(3)
    pdf.set_font(FONT_NAME, "", 12)
    pdf.set_text_color(*COLOR_GREY)
    title = lead.title if lead.title else "Untitled Listing"
    pdf.cell(0, 8, f"Property: {title}", new_x="LMARGIN", new_y="NEXT")

    if lead.city:
        pdf.cell(0, 8, f"Location: {lead.city}", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(8)


def _add_listing_overview(pdf: AuditReport, lead: ListingData) -> None:
    """Add the listing stats overview."""
    _section_header(pdf, "LISTING OVERVIEW")

    stats = [
        ("Rating", f"{lead.rating}/5.0" if lead.rating else "N/A"),
        ("Reviews", str(lead.review_count) if lead.review_count else "0"),
        ("Price/Night", f"${lead.price_per_night:.0f}" if lead.price_per_night else "N/A"),
        ("Total Photos", str(len(lead.photo_urls))),
        ("Amenities", str(len(lead.amenities))),
    ]

    pdf.set_font(FONT_NAME, "", 10)
    col_width = 38
    for label, value in stats:
        pdf.set_text_color(*COLOR_GREY)
        pdf.cell(col_width, 7, label, align="L")

    pdf.ln()
    pdf.set_font(FONT_NAME, "B", 12)
    for label, value in stats:
        pdf.set_text_color(*COLOR_DARK)
        pdf.cell(col_width, 8, value, align="L")

    pdf.ln(12)

    if lead.photo_sections:
        pdf.set_font(FONT_NAME, "B", 10)
        pdf.set_text_color(*COLOR_DARK)
        pdf.cell(0, 7, "Photo Sections:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font(FONT_NAME, "", 10)
        pdf.set_text_color(*COLOR_GREY)
        for section, urls in lead.photo_sections.items():
            pdf.cell(0, 6, f"  {section}: {len(urls)} photos", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)


def _add_photo_analysis(
    pdf: AuditReport,
    analysis: PhotoAnalysis,
    photo_cache: dict[int, Path],
) -> None:
    """Add the photo analysis section with inline photos."""
    pdf.add_page()
    _section_header(pdf, "PHOTO ANALYSIS")

    # Impact estimate
    if analysis.estimated_impact:
        _highlight_box(pdf, "Estimated Impact", analysis.estimated_impact, COLOR_GREEN)

    # Suggestions — each one shows the referenced photo above the text
    if analysis.suggestions:
        pdf.set_font(FONT_NAME, "B", 11)
        pdf.set_text_color(*COLOR_DARK)
        pdf.cell(0, 8, "Recommendations:", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        for i, suggestion in enumerate(analysis.suggestions, 1):
            # Find all photo numbers referenced in this suggestion
            referenced = [int(m) for m in re.findall(r"#(\d+)", suggestion)]
            # Filter to ones we have downloaded
            available = [n for n in referenced if n in photo_cache]

            if available:
                _photo_recommendation(pdf, i, suggestion, photo_cache, available)
            else:
                _numbered_item(pdf, i, suggestion)

    # Section feedback
    if analysis.section_feedback:
        pdf.ln(5)
        pdf.set_font(FONT_NAME, "B", 11)
        pdf.set_text_color(*COLOR_DARK)
        pdf.cell(0, 8, "Section-by-Section Feedback:", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        for section, feedback in analysis.section_feedback.items():
            _check_page_space(pdf, 40)
            pdf.set_font(FONT_NAME, "B", 10)
            pdf.set_text_color(*COLOR_PRIMARY)
            pdf.cell(0, 7, section, new_x="LMARGIN", new_y="NEXT")

            pdf.set_font(FONT_NAME, "", 9)
            pdf.set_text_color(*COLOR_GREY)
            pdf.multi_cell(0, 5, feedback)
            pdf.ln(4)


def _photo_recommendation(
    pdf: AuditReport,
    number: int,
    text: str,
    photo_cache: dict[int, Path],
    photo_nums: list[int],
) -> None:
    """Draw a recommendation with the referenced photos shown above it.

    Layout:
        [Photo #1]  [Photo #4]  [Photo #5]     <- photos in a row
        1. The recommendation text goes here    <- text below
           spanning the full width...
    """
    # Calculate space needed: photo row + text
    photo_h = 40
    _check_page_space(pdf, photo_h + 30)

    # Draw photos in a row (max 4 per row, centered)
    photo_w = 45
    spacing = 4
    photos_to_show = photo_nums[:4]
    total_w = len(photos_to_show) * photo_w + (len(photos_to_show) - 1) * spacing
    x_start = 10

    y_photo = pdf.get_y()
    for j, num in enumerate(photos_to_show):
        x = x_start + j * (photo_w + spacing)
        # Red border
        pdf.set_draw_color(*COLOR_RED)
        pdf.set_line_width(0.8)
        pdf.rect(x - 0.5, y_photo - 0.5, photo_w + 1, photo_h + 1, "D")
        try:
            pdf.image(str(photo_cache[num]), x=x, y=y_photo, w=photo_w, h=photo_h)
        except Exception:
            pass
        # Label below photo
        pdf.set_font(FONT_NAME, "B", 7)
        pdf.set_text_color(*COLOR_RED)
        pdf.set_xy(x, y_photo + photo_h + 1)
        pdf.cell(photo_w, 4, f"Photo #{num}", align="C")

    # Reset drawing
    pdf.set_draw_color(*COLOR_PRIMARY)
    pdf.set_line_width(0.3)

    # Move below the photos
    pdf.set_y(y_photo + photo_h + 7)

    # Recommendation number + text
    pdf.set_font(FONT_NAME, "B", 10)
    pdf.set_text_color(*COLOR_PRIMARY)
    pdf.cell(8, 6, f"{number}.")

    pdf.set_font(FONT_NAME, "", 9)
    pdf.set_text_color(*COLOR_DARK)
    pdf.multi_cell(182, 5, text)
    pdf.ln(5)


def _add_copy_analysis(pdf: AuditReport, analysis: CopyAnalysis) -> None:
    """Add the copy/text analysis section."""
    pdf.add_page()
    _section_header(pdf, "COPY ANALYSIS (TITLE & DESCRIPTION)")

    pdf.set_font(FONT_NAME, "", 10)
    pdf.set_text_color(*COLOR_GREY)
    pdf.cell(50, 8, "Title Score:")
    _score_badge(pdf, analysis.title_score)
    pdf.ln()
    pdf.cell(50, 8, "Description Score:")
    _score_badge(pdf, analysis.description_score)
    pdf.ln(8)

    if analysis.estimated_impact:
        _highlight_box(pdf, "Estimated Impact", analysis.estimated_impact, COLOR_GREEN)

    if analysis.title_suggestion:
        pdf.set_font(FONT_NAME, "B", 10)
        pdf.set_text_color(*COLOR_DARK)
        pdf.cell(0, 8, "Suggested New Title:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font(FONT_NAME, "I", 10)
        pdf.set_text_color(*COLOR_PRIMARY)
        pdf.multi_cell(0, 6, f'"{analysis.title_suggestion}"')
        pdf.ln(5)

    if analysis.tone_feedback:
        pdf.set_font(FONT_NAME, "B", 10)
        pdf.set_text_color(*COLOR_DARK)
        pdf.cell(0, 8, "Tone & Style Feedback:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font(FONT_NAME, "", 9)
        pdf.set_text_color(*COLOR_GREY)
        pdf.multi_cell(0, 5, analysis.tone_feedback)
        pdf.ln(5)

    if analysis.missing_keywords:
        pdf.set_font(FONT_NAME, "B", 10)
        pdf.set_text_color(*COLOR_DARK)
        pdf.cell(0, 8, "Missing Keywords:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font(FONT_NAME, "", 9)
        pdf.set_text_color(*COLOR_ORANGE)
        keywords_str = ", ".join(analysis.missing_keywords)
        pdf.multi_cell(0, 5, keywords_str)
        pdf.ln(5)

    if analysis.description_suggestions:
        pdf.set_font(FONT_NAME, "B", 11)
        pdf.set_text_color(*COLOR_DARK)
        pdf.cell(0, 8, "Description Improvements:", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        for i, suggestion in enumerate(analysis.description_suggestions, 1):
            _numbered_item(pdf, i, suggestion)


def _add_action_summary(pdf: AuditReport, photo: PhotoAnalysis, copy: CopyAnalysis) -> None:
    """Add a final action summary page."""
    pdf.add_page()
    _section_header(pdf, "ACTION SUMMARY")

    pdf.set_font(FONT_NAME, "", 10)
    pdf.set_text_color(*COLOR_DARK)
    pdf.multi_cell(0, 6, (
        "Below is a prioritized list of changes that will have the highest "
        "impact on your listing's performance. Focus on the top items first."
    ))
    pdf.ln(5)

    actions: list[tuple[str, str]] = []

    if photo.weak_photos:
        weak_str = ", ".join(f"#{p}" for p in photo.weak_photos)
        actions.append(("HIGH", f"Reshoot or replace photos {weak_str}"))

    if copy.title_suggestion:
        actions.append(("HIGH", f'Update title to: "{copy.title_suggestion}"'))

    for s in photo.suggestions[:2]:
        actions.append(("MEDIUM", s))

    for s in copy.description_suggestions[:2]:
        actions.append(("MEDIUM", s))

    if copy.missing_keywords:
        top_kw = ", ".join(copy.missing_keywords[:5])
        actions.append(("LOW", f"Add these keywords to your description: {top_kw}"))

    for i, (priority, action) in enumerate(actions, 1):
        _check_page_space(pdf, 25)

        if priority == "HIGH":
            color = COLOR_RED
        elif priority == "MEDIUM":
            color = COLOR_ORANGE
        else:
            color = COLOR_GREEN

        pdf.set_font(FONT_NAME, "B", 9)
        pdf.set_fill_color(*color)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(18, 6, f" {priority}", fill=True)
        pdf.cell(3, 6, "")

        pdf.set_font(FONT_NAME, "", 9)
        pdf.set_text_color(*COLOR_DARK)
        pdf.multi_cell(190 - 21, 5, action)
        pdf.ln(3)

    pdf.ln(10)
    pdf.set_draw_color(*COLOR_PRIMARY)
    pdf.set_line_width(0.3)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    pdf.set_font(FONT_NAME, "I", 9)
    pdf.set_text_color(*COLOR_GREY)
    pdf.multi_cell(0, 5, (
        "This report was generated by an AI-powered listing audit tool. "
        "Estimated impacts are based on comparison with top-performing listings "
        "in the same city and general industry benchmarks. Actual results may vary."
    ))


# --- Helper functions ---

def _section_header(pdf: AuditReport, title: str) -> None:
    """Draw a styled section header."""
    _check_page_space(pdf, 20)
    pdf.set_font(FONT_NAME, "B", 14)
    pdf.set_text_color(*COLOR_PRIMARY)
    pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*COLOR_PRIMARY)
    pdf.set_line_width(0.3)
    pdf.line(10, pdf.get_y(), 80, pdf.get_y())
    pdf.ln(5)


def _highlight_box(pdf: AuditReport, label: str, text: str, color: tuple) -> None:
    """Draw a highlighted box with a label and text."""
    _check_page_space(pdf, 25)
    y_start = pdf.get_y()

    pdf.set_font(FONT_NAME, "B", 9)
    pdf.set_text_color(*color)
    pdf.cell(0, 6, label, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font(FONT_NAME, "", 9)
    pdf.set_text_color(*COLOR_DARK)
    pdf.multi_cell(0, 5, text)

    y_end = pdf.get_y()
    pdf.set_fill_color(*COLOR_LIGHT_BG)
    pdf.rect(10, y_start - 2, 190, y_end - y_start + 4, "F")

    pdf.set_y(y_start)
    pdf.set_font(FONT_NAME, "B", 9)
    pdf.set_text_color(*color)
    pdf.cell(0, 6, label, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT_NAME, "", 9)
    pdf.set_text_color(*COLOR_DARK)
    pdf.multi_cell(0, 5, text)
    pdf.ln(5)


def _score_badge(pdf: AuditReport, score: int) -> None:
    """Draw a score badge with color coding."""
    if score >= 7:
        color = COLOR_GREEN
    elif score >= 4:
        color = COLOR_ORANGE
    else:
        color = COLOR_RED

    pdf.set_font(FONT_NAME, "B", 12)
    pdf.set_text_color(*color)
    pdf.cell(20, 8, f"{score}/10")


def _numbered_item(pdf: AuditReport, number: int, text: str) -> None:
    """Draw a numbered recommendation item."""
    _check_page_space(pdf, 20)
    pdf.set_font(FONT_NAME, "B", 10)
    pdf.set_text_color(*COLOR_PRIMARY)
    pdf.cell(8, 6, f"{number}.")

    pdf.set_font(FONT_NAME, "", 9)
    pdf.set_text_color(*COLOR_DARK)
    pdf.multi_cell(182, 5, text)
    pdf.ln(3)


def _check_page_space(pdf: AuditReport, needed: float) -> None:
    """Add a new page if there isn't enough space left."""
    if pdf.get_y() + needed > pdf.h - 20:
        pdf.add_page()
