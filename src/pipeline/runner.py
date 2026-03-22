"""Orchestrate the full audit pipeline: scrape -> analyze -> report."""

from pathlib import Path

from src.pipeline.leads import Lead


async def run_audit(lead: Lead, output_dir: Path) -> Path:
    """Run the full audit pipeline for a single lead.

    Steps:
        1. Scrape the lead's listing
        2. Collect top performers in the same city
        3. Run AI photo comparison
        4. Run AI copy comparison
        5. Generate PDF report
        6. Return the path to the generated report
    """
    # TODO: Wire together all modules
    raise NotImplementedError
