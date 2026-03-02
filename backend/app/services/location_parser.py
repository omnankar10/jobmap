"""Location parsing and remote detection utilities."""
import re
from typing import Tuple, Optional

# Patterns that indicate a remote position
REMOTE_PATTERNS = [
    r"\bremote\b",
    r"\bwork\s+from\s+home\b",
    r"\bwfh\b",
    r"\btelecommute\b",
    r"\bdistributed\b",
]

REMOTE_RE = re.compile("|".join(REMOTE_PATTERNS), re.IGNORECASE)

# Patterns like "Remote - US", "Remote (United States)", "United States (Remote)"
REMOTE_WITH_LOCATION_RE = re.compile(
    r"remote\s*[-–—]\s*(.+)|(.+)\s*\(remote\)|remote\s*\((.+)\)",
    re.IGNORECASE,
)

# US state abbreviations for normalization
US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC",
}


def normalize_location(text: str) -> str:
    """Normalize location string for geocoding cache lookup."""
    if not text:
        return ""
    result = text.lower().strip()
    result = re.sub(r"[^\w\s,.-]", "", result)
    result = re.sub(r"\s+", " ", result)
    return result


def parse_location(location_text: str) -> dict:
    """
    Parse a location string and return structured data.

    Returns dict with:
        remote_type: 'remote' | 'hybrid' | 'onsite'
        geocode_query: str | None  (the part to geocode, if any)
        country_hint: str | None
    """
    if not location_text:
        return {"remote_type": "onsite", "geocode_query": None, "country_hint": None}

    text = location_text.strip()
    is_remote = bool(REMOTE_RE.search(text))

    # Check for remote with a specific location
    remote_loc_match = REMOTE_WITH_LOCATION_RE.search(text)
    if remote_loc_match:
        # Extract the location portion
        loc_part = remote_loc_match.group(1) or remote_loc_match.group(2) or remote_loc_match.group(3)
        if loc_part:
            loc_part = loc_part.strip()
            # If it's just a country/region name, note it as a hint
            # but don't geocode (no specific city)
            words = loc_part.split()
            if len(words) <= 2 and "," not in loc_part:
                return {
                    "remote_type": "remote",
                    "geocode_query": None,
                    "country_hint": loc_part,
                }
            else:
                # Has a specific enough location to geocode
                return {
                    "remote_type": "remote",
                    "geocode_query": loc_part,
                    "country_hint": None,
                }

    if is_remote:
        # Pure remote, no specific location
        return {"remote_type": "remote", "geocode_query": None, "country_hint": None}

    # Check for hybrid keywords
    if re.search(r"\bhybrid\b", text, re.IGNORECASE):
        # Remove the "hybrid" keyword and geocode the rest
        clean = re.sub(r"\bhybrid\b", "", text, flags=re.IGNORECASE).strip(" -–—,/")
        return {"remote_type": "hybrid", "geocode_query": clean or None, "country_hint": None}

    # On-site — geocode the full string
    return {"remote_type": "onsite", "geocode_query": text, "country_hint": None}
