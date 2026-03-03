import os
import time
import json
import requests
import psycopg2
from psycopg2.extras import RealDictCursor

MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

if not MAPBOX_TOKEN:
    raise SystemExit("MAPBOX_TOKEN is missing")
if not DATABASE_URL:
    raise SystemExit("DATABASE_URL is missing")

MAPBOX_URL = "https://api.mapbox.com/geocoding/v5/mapbox.places/{query}.json"

def geocode_mapbox(query: str):
    url = MAPBOX_URL.format(query=requests.utils.quote(query))
    params = {
        "access_token": MAPBOX_TOKEN,
        "limit": 1,
    }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    feats = data.get("features") or []
    if not feats:
        return None

    f = feats[0]
    # Mapbox returns [lng, lat]
    lng, lat = f["center"][0], f["center"][1]

    # Try to extract city/region/country from context
    city = region = country = None
    for c in f.get("context", []):
        if c.get("id", "").startswith("place."):
            city = c.get("text")
        elif c.get("id", "").startswith("region."):
            region = c.get("text")
        elif c.get("id", "").startswith("country."):
            country = c.get("text")

    return {
        "lat": lat,
        "lng": lng,
        "city": city,
        "region": region,
        "country": country,
        "raw": data,
    }

def main(batch_limit=5000, sleep_s=0.15):
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    conn.autocommit = False

    with conn.cursor() as cur:
        # Get distinct locations that haven't been cached
        cur.execute(
            """
            SELECT DISTINCT j.location_text AS query
            FROM jobs j
            LEFT JOIN geocode_cache g ON g.query = j.location_text
            WHERE j.geo IS NULL
              AND j.location_text IS NOT NULL
              AND j.location_text <> ''
              AND j.location_text <> 'N/A'
              AND g.id IS NULL
            LIMIT %s
            """,
            (batch_limit,),
        )
        rows = cur.fetchall()

    print(f"Found {len(rows)} unique uncached locations to geocode")

    ok = 0
    fail = 0

    for i, row in enumerate(rows, start=1):
        q = row["query"]

        try:
            result = geocode_mapbox(q)
            with conn.cursor() as cur:
                if result is None:
                    # Cache negative result to avoid repeated lookups
                    cur.execute(
                        """
                        INSERT INTO geocode_cache (query, raw_response)
                        VALUES (%s, %s)
                        ON CONFLICT (query) DO NOTHING
                        """,
                        (q, json.dumps({"features": []})),
                    )
                    conn.commit()
                    fail += 1
                else:
                    # Insert cache
                    cur.execute(
                        """
                        INSERT INTO geocode_cache (query, city, region, country, lat, lng, geo, raw_response)
                        VALUES (
                          %s, %s, %s, %s, %s, %s,
                          ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                          %s
                        )
                        ON CONFLICT (query) DO UPDATE SET
                          city=EXCLUDED.city,
                          region=EXCLUDED.region,
                          country=EXCLUDED.country,
                          lat=EXCLUDED.lat,
                          lng=EXCLUDED.lng,
                          geo=EXCLUDED.geo,
                          raw_response=EXCLUDED.raw_response
                        """,
                        (
                            q,
                            result["city"],
                            result["region"],
                            result["country"],
                            result["lat"],
                            result["lng"],
                            result["lng"],
                            result["lat"],
                            json.dumps(result["raw"]),
                        ),
                    )

                    # Backfill jobs with this location_text
                    cur.execute(
                        """
                        UPDATE jobs
                        SET
                          lat = %s,
                          lng = %s,
                          geo = ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                          city = COALESCE(city, %s),
                          region = COALESCE(region, %s),
                          country = COALESCE(country, %s)
                        WHERE geo IS NULL
                          AND location_text = %s
                        """,
                        (
                            result["lat"],
                            result["lng"],
                            result["lng"],
                            result["lat"],
                            result["city"],
                            result["region"],
                            result["country"],
                            q,
                        ),
                    )

                    conn.commit()
                    ok += 1

        except Exception as e:
            conn.rollback()
            print(f"[{i}/{len(rows)}] FAIL: {q} -> {e}")
            fail += 1

        if i % 25 == 0:
            print(f"Progress: {i}/{len(rows)} | ok={ok} fail={fail}")

        time.sleep(sleep_s)

    conn.close()
    print(f"Done. ok={ok} fail={fail}")

if __name__ == "__main__":
    main()
