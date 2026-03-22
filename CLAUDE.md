# Property Management — AI Listing Audit Tool

## Project Overview

A lead generation tool for property managers who manage luxury Airbnb villas.
The tool scrapes a lead's Airbnb listing, compares it against the Top 1% performers
in that city, and generates a professional PDF report with specific improvement
recommendations (photos, copy, pricing).

## Tech Stack

- **Language:** Python 3.11+
- **AI Provider:** Claude API (Anthropic) — multimodal analysis for photos + copy
- **Scraping:** Playwright (headless browser)
- **PDF Generation:** FPDF2
- **Video Generation:** TBD

## Project Structure

```
Property-Management/
├── CLAUDE.md              # This file — project rules for Claude Code
├── .env.example           # API keys template
├── .gitignore
├── requirements.txt       # Python dependencies
├── pyproject.toml         # Project metadata
├── src/
│   ├── scraper/           # Airbnb listing scraper (Playwright)
│   ├── benchmark/         # Top 1% data collection & ranking
│   ├── analysis/          # AI comparison engine (Claude API)
│   ├── reports/           # PDF report generation (FPDF2)
│   ├── pipeline/          # Lead management & workflow orchestration
│   └── utils/             # Shared helpers, config, constants
├── data/                  # Cached benchmark data per city
├── output/                # Generated PDF reports
└── tests/                 # Test files
```

## Coding Conventions

- Use **snake_case** for variables, functions, and file names
- Use **PascalCase** for class names
- Keep functions focused — one function, one responsibility
- Use type hints on all function signatures
- Use f-strings for string formatting
- Use `pathlib.Path` instead of `os.path` for file paths
- Store all configuration and secrets in `.env` (never hardcode API keys)
- Write docstrings only for public functions and classes

## Key Workflow

1. **Input:** Lead's Airbnb listing URL
2. **Scrape:** Playwright extracts photos, title, description, price, reviews
3. **Benchmark:** Scrape/load top performers in the same city
4. **Analyze:** Claude API compares lead vs. top 1% (photos + copy)
5. **Report:** FPDF2 generates a PDF with specific recommendations
6. **Output:** Saved to `output/` directory

## Important Rules

- Never commit `.env` files or API keys
- Always handle Playwright browser cleanup (use context managers)
- Rate-limit Airbnb scraping to avoid IP blocks
- Cache benchmark data in `data/` to avoid redundant scraping
- All AI calls go through `src/analysis/` — no direct API calls elsewhere
