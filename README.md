# Property Management — AI Listing Audit Tool

An AI-powered lead generation tool for property managers who manage luxury Airbnb villas. The tool scrapes a lead's Airbnb listing, compares it against the **Top 1% performers** in that city, and generates a professional **PDF report** with specific improvement recommendations for photos, copy, and pricing.

## How It Works

```
Lead's Airbnb URL
       │
       ▼
   PLAYWRIGHT ──────► Scrapes listing data + photos
       │                Also scrapes top 1% listings in same city
       ▼
   CLAUDE API ──────► Compares lead vs. top performers
       │                Analyzes photos (vision) + descriptions (text)
       │                Generates specific recommendations
       ▼
     FPDF2 ─────────► Packages everything into a professional PDF report
       │
       ▼
   Final Report: "Change these 3 photos, update this headline,
                   your revenue could jump by 15%"
```

## Example Output

The generated PDF report includes:

- **Listing Overview** — rating, reviews, price, photo count, amenities
- **Photo Analysis** — AI identifies weak photos with inline images, provides specific reshoot recommendations
- **Copy Analysis** — title and description scoring (1-10), suggested rewrites, missing SEO keywords
- **Action Summary** — prioritized list of changes (HIGH / MEDIUM / LOW impact)

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Language | Python 3.11+ | Core application |
| AI Provider | Claude API (Anthropic) | Multimodal photo + copy analysis |
| Scraping | Playwright | Headless browser for dynamic Airbnb pages |
| PDF Generation | FPDF2 | Professional report output |
| Image Processing | Pillow | Photo handling for PDF embedding |
| HTTP Client | httpx | Photo downloads |

## Project Structure

```
property-management/
├── src/
│   ├── scraper/           # Airbnb listing scraper (Playwright)
│   │   ├── listing.py     # ListingData model + single listing scraper
│   │   ├── parser.py      # Page parsing, modal handling, photo extraction
│   │   └── city_top.py    # Scrape top listings per city
│   ├── benchmark/         # Top 1% data collection & ranking
│   │   ├── collector.py   # Scrape + cache benchmarks per city
│   │   └── ranker.py      # Composite scoring algorithm (0-100)
│   ├── analysis/          # AI comparison engine (Claude API)
│   │   ├── photos.py      # Vision-based photo comparison
│   │   └── copy.py        # Text-based title & description comparison
│   ├── reports/           # PDF report generation
│   │   ├── pdf_builder.py # FPDF2-based report builder
│   │   └── fonts/         # Unicode fonts (DejaVu Sans)
│   ├── pipeline/          # Lead management & workflow orchestration
│   │   ├── leads.py       # Lead model & tracking
│   │   └── runner.py      # Full pipeline orchestrator
│   └── utils/
│       └── config.py      # Settings, env vars, paths
├── tests/                 # Test scripts for each module
├── data/                  # Cached benchmark data per city (auto-generated)
└── output/                # Generated PDF reports (auto-generated)
```

## Getting Started

### Prerequisites

- Python 3.11 or higher
- An [Anthropic API key](https://console.anthropic.com/)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/JimKonstantinopoulos/property-management.git
   cd property-management
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Playwright browsers**
   ```bash
   python -m playwright install
   ```

4. **Set up your API key**
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` and add your Anthropic API key.

### Usage

**Run the full pipeline** (scrape → analyze → generate PDF):
```bash
python tests/test_report.py
```
Paste an Airbnb listing URL when prompted. The PDF report will be saved to the `output/` directory.

**Test individual modules:**
```bash
python tests/test_scraper.py      # Test the scraper
python tests/test_benchmark.py    # Test benchmark collection & ranking
python tests/test_analysis.py     # Test AI photo + copy analysis
```

## Scoring Algorithm

Listings are ranked on a **0-100 composite score**:

| Factor | Weight | Why |
|--------|--------|-----|
| Rating | 40% | Guest satisfaction is the strongest quality signal |
| Review Count | 30% | Booking volume and social proof |
| Photo Count | 15% | Investment in presentation |
| Amenities | 15% | Offering completeness |

## Features

- **Headless browser scraping** — handles JavaScript-rendered Airbnb pages
- **Full photo gallery extraction** — opens the photo modal, scrolls to load all images, organizes by section (Bedroom, Bathroom, etc.)
- **Smart caching** — benchmark data is cached per city for 7 days to avoid redundant scraping
- **Multimodal AI analysis** — Claude vision compares listing photos against top performers
- **Unicode support** — handles international listings (Greek, Cyrillic, etc.)
- **Inline photo recommendations** — PDF shows the actual weak photos alongside improvement suggestions

## Configuration

Environment variables (set in `.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | Your Anthropic API key (required) |
| `CLAUDE_MODEL` | `claude-sonnet-4-6` | Claude model to use |
| `SCRAPE_DELAY_SECONDS` | `2` | Delay between page loads |
| `MAX_TOP_LISTINGS` | `20` | Max benchmark listings to scrape per city |

## License

This project is for educational and portfolio purposes.
