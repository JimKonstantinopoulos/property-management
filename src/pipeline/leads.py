"""Lead intake and tracking."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Lead:
    """A property management lead."""

    listing_url: str
    contact_name: str = ""
    contact_email: str = ""
    city: str = ""
    status: str = "new"  # new, processing, completed, sent
    created_at: datetime = field(default_factory=datetime.now)
    report_path: str = ""
