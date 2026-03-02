"""Geocoding service with cache-first strategy and Nominatim fallback."""
import time
import logging
from typing import Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

from app.models.models import GeocodeCache, Job
from app.services.location_parser import normalize_location, parse_location

logger = logging.getLogger(__name__)

# Nominatim requires a user-agent
_geocoder = Nominatim(user_agent="jobmap-mvp/0.1", timeout=10)

# Rate limit for Nominatim: max 1 request/second
_last_request_time = 0.0


def _rate_limit():
    """Ensure at least 1 second between geocoding requests (Nominatim policy)."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < 1.1:
        time.sleep(1.1 - elapsed)
    _last_request_time = time.time()


def geocode_location(query: str, db: Session) -> Optional[Dict[str, Any]]:
    """
    Geocode a location string. Checks cache first, then calls Nominatim.

    Returns dict with: city, region, country, lat, lng — or None if not found.
    """
    normalized = normalize_location(query)
    if not normalized:
        return None

    # Check cache
    cached = db.query(GeocodeCache).filter(GeocodeCache.query == normalized).first()
    if cached:
        logger.debug(f"Geocode cache hit: {normalized}")
        return {
            "city": cached.city,
            "region": cached.region,
            "country": cached.country,
            "lat": cached.lat,
            "lng": cached.lng,
        }

    # Call geocoder
    try:
        _rate_limit()
        location = _geocoder.geocode(query, addressdetails=True, language="en")
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        logger.warning(f"Geocoder error for '{query}': {e}")
        return None

    if not location:
        logger.info(f"No geocode result for: {query}")
        # Cache the miss
        cache_entry = GeocodeCache(query=normalized, raw_response={"status": "not_found"})
        db.add(cache_entry)
        db.commit()
        return None

    address = location.raw.get("address", {})
    city = address.get("city") or address.get("town") or address.get("village")
    region = address.get("state") or address.get("county")
    country = address.get("country")
    lat = location.latitude
    lng = location.longitude

    # Store in cache
    from geoalchemy2.elements import WKTElement
    geo_wkt = f"POINT({lng} {lat})" if lat and lng else None

    cache_entry = GeocodeCache(
        query=normalized,
        city=city,
        region=region,
        country=country,
        lat=lat,
        lng=lng,
        geo=geo_wkt,
        raw_response=location.raw,
    )
    db.add(cache_entry)
    db.commit()

    logger.info(f"Geocoded '{query}' -> {city}, {region}, {country} ({lat}, {lng})")
    return {
        "city": city,
        "region": region,
        "country": country,
        "lat": lat,
        "lng": lng,
    }


def geocode_job(job: Job, db: Session) -> None:
    """Parse location and geocode a job, updating its fields in place."""
    parsed = parse_location(job.location_text or "")
    job.remote_type = parsed["remote_type"]

    if parsed["geocode_query"]:
        result = geocode_location(parsed["geocode_query"], db)
        if result:
            job.city = result["city"]
            job.region = result["region"]
            job.country = result["country"]
            if result["lat"] and result["lng"]:
                job.geo = f"POINT({result['lng']} {result['lat']})"
    elif parsed["country_hint"]:
        # Remote with country hint — store country but no geo point
        job.country = parsed["country_hint"]
