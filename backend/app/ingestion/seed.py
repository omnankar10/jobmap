"""Seed script to load sample jobs for development."""
import uuid
from datetime import datetime, timedelta
import random
from sqlalchemy.orm import Session
from app.models.models import Job, Company
from app.db.database import SessionLocal

SAMPLE_COMPANIES = [
    {"name": "TechCorp", "website": "https://techcorp.example.com"},
    {"name": "DataFlow", "website": "https://dataflow.example.com"},
    {"name": "CloudBase", "website": "https://cloudbase.example.com"},
    {"name": "AILabs", "website": "https://ailabs.example.com"},
    {"name": "DevStack", "website": "https://devstack.example.com"},
]

SAMPLE_JOBS = [
    # On-site jobs with real coordinates
    {"title": "Senior Backend Engineer", "location_text": "San Francisco, CA", "lat": 37.7749, "lng": -122.4194, "remote_type": "onsite", "tags": ["python", "postgresql", "aws"], "salary_min": 150000, "salary_max": 200000},
    {"title": "Data Scientist", "location_text": "New York, NY", "lat": 40.7128, "lng": -74.0060, "remote_type": "onsite", "tags": ["python", "machine-learning", "sql"], "salary_min": 130000, "salary_max": 180000},
    {"title": "Frontend Developer", "location_text": "Austin, TX", "lat": 30.2672, "lng": -97.7431, "remote_type": "onsite", "tags": ["javascript", "react", "typescript"], "salary_min": 120000, "salary_max": 160000},
    {"title": "DevOps Engineer", "location_text": "Seattle, WA", "lat": 47.6062, "lng": -122.3321, "remote_type": "onsite", "tags": ["aws", "docker", "kubernetes", "terraform"], "salary_min": 140000, "salary_max": 190000},
    {"title": "ML Engineer", "location_text": "Boston, MA", "lat": 42.3601, "lng": -71.0589, "remote_type": "onsite", "tags": ["python", "machine-learning", "deep-learning"], "salary_min": 160000, "salary_max": 220000},
    {"title": "Product Designer", "location_text": "Los Angeles, CA", "lat": 34.0522, "lng": -118.2437, "remote_type": "onsite", "tags": ["product-design", "ux-design", "ui-design"], "salary_min": 110000, "salary_max": 150000},
    {"title": "Data Engineer", "location_text": "Chicago, IL", "lat": 41.8781, "lng": -87.6298, "remote_type": "onsite", "tags": ["python", "sql", "apache-spark", "data-engineering"], "salary_min": 130000, "salary_max": 175000},
    {"title": "iOS Developer", "location_text": "Denver, CO", "lat": 39.7392, "lng": -104.9903, "remote_type": "hybrid", "tags": ["swift", "ios", "mobile"], "salary_min": 125000, "salary_max": 165000},
    {"title": "Full Stack Engineer", "location_text": "Portland, OR", "lat": 45.5152, "lng": -122.6784, "remote_type": "hybrid", "tags": ["javascript", "react", "node.js", "full-stack"], "salary_min": 120000, "salary_max": 165000},
    {"title": "Security Engineer", "location_text": "Washington, DC", "lat": 38.9072, "lng": -77.0369, "remote_type": "onsite", "tags": ["security", "aws"], "salary_min": 145000, "salary_max": 195000},
    # International on-site
    {"title": "Backend Developer", "location_text": "London, UK", "lat": 51.5074, "lng": -0.1278, "remote_type": "onsite", "tags": ["python", "golang", "postgresql"], "salary_min": 70000, "salary_max": 95000},
    {"title": "Data Analyst", "location_text": "Berlin, Germany", "lat": 52.5200, "lng": 13.4050, "remote_type": "onsite", "tags": ["python", "sql", "analytics"], "salary_min": 55000, "salary_max": 75000},
    {"title": "Software Engineer", "location_text": "Tokyo, Japan", "lat": 35.6762, "lng": 139.6503, "remote_type": "onsite", "tags": ["java", "react"], "salary_min": 60000, "salary_max": 80000},
    {"title": "Cloud Architect", "location_text": "Sydney, Australia", "lat": -33.8688, "lng": 151.2093, "remote_type": "onsite", "tags": ["aws", "gcp", "docker", "kubernetes"], "salary_min": 120000, "salary_max": 170000},
    {"title": "Frontend Engineer", "location_text": "Toronto, Canada", "lat": 43.6532, "lng": -79.3832, "remote_type": "hybrid", "tags": ["typescript", "react", "frontend"], "salary_min": 100000, "salary_max": 140000},
    {"title": "Machine Learning Researcher", "location_text": "Paris, France", "lat": 48.8566, "lng": 2.3522, "remote_type": "onsite", "tags": ["python", "machine-learning", "deep-learning"], "salary_min": 65000, "salary_max": 90000},
    {"title": "SRE Engineer", "location_text": "Amsterdam, Netherlands", "lat": 52.3676, "lng": 4.9041, "remote_type": "hybrid", "tags": ["kubernetes", "docker", "terraform", "devops"], "salary_min": 60000, "salary_max": 85000},
    {"title": "Android Developer", "location_text": "Bangalore, India", "lat": 12.9716, "lng": 77.5946, "remote_type": "onsite", "tags": ["kotlin", "android", "mobile"], "salary_min": 20000, "salary_max": 35000},
    {"title": "Platform Engineer", "location_text": "Singapore", "lat": 1.3521, "lng": 103.8198, "remote_type": "onsite", "tags": ["golang", "kubernetes", "aws"], "salary_min": 70000, "salary_max": 100000},
    {"title": "QA Engineer", "location_text": "Dublin, Ireland", "lat": 53.3498, "lng": -6.2603, "remote_type": "hybrid", "tags": ["python", "javascript", "security"], "salary_min": 55000, "salary_max": 75000},
    # South America
    {"title": "Full Stack Developer", "location_text": "São Paulo, Brazil", "lat": -23.5505, "lng": -46.6333, "remote_type": "onsite", "tags": ["javascript", "react", "node.js", "full-stack"], "salary_min": 25000, "salary_max": 45000},
    {"title": "Data Scientist", "location_text": "Buenos Aires, Argentina", "lat": -34.6037, "lng": -58.3816, "remote_type": "hybrid", "tags": ["python", "machine-learning", "sql"], "salary_min": 20000, "salary_max": 35000},
    # Africa
    {"title": "Software Engineer", "location_text": "Lagos, Nigeria", "lat": 6.5244, "lng": 3.3792, "remote_type": "onsite", "tags": ["python", "javascript", "react"], "salary_min": 15000, "salary_max": 25000},
    {"title": "DevOps Engineer", "location_text": "Cape Town, South Africa", "lat": -33.9249, "lng": 18.4241, "remote_type": "hybrid", "tags": ["docker", "kubernetes", "aws", "devops"], "salary_min": 25000, "salary_max": 40000},
    # Remote jobs (no coordinates)
    {"title": "Remote Software Engineer", "location_text": "Remote", "lat": None, "lng": None, "remote_type": "remote", "tags": ["python", "golang", "aws"], "salary_min": 130000, "salary_max": 180000},
    {"title": "Remote Data Analyst", "location_text": "Remote - United States", "lat": None, "lng": None, "remote_type": "remote", "tags": ["sql", "python", "analytics"], "salary_min": 90000, "salary_max": 120000},
    {"title": "Remote Frontend Developer", "location_text": "Remote - Europe", "lat": None, "lng": None, "remote_type": "remote", "tags": ["javascript", "typescript", "react", "frontend"], "salary_min": 70000, "salary_max": 100000},
    {"title": "Remote ML Engineer", "location_text": "Remote (Worldwide)", "lat": None, "lng": None, "remote_type": "remote", "tags": ["python", "machine-learning", "deep-learning"], "salary_min": 150000, "salary_max": 210000},
    # Additional variety
    {"title": "Rust Systems Engineer", "location_text": "Munich, Germany", "lat": 48.1351, "lng": 11.5820, "remote_type": "onsite", "tags": ["rust", "backend"], "salary_min": 65000, "salary_max": 90000},
    {"title": "Scala Developer", "location_text": "Zurich, Switzerland", "lat": 47.3769, "lng": 8.5417, "remote_type": "onsite", "tags": ["scala", "apache-spark", "data-engineering"], "salary_min": 100000, "salary_max": 140000},
    # More US cities
    {"title": "Backend Engineer", "location_text": "Miami, FL", "lat": 25.7617, "lng": -80.1918, "remote_type": "onsite", "tags": ["python", "postgresql", "backend"], "salary_min": 120000, "salary_max": 160000},
    {"title": "Cloud Engineer", "location_text": "Atlanta, GA", "lat": 33.7490, "lng": -84.3880, "remote_type": "onsite", "tags": ["aws", "gcp", "terraform"], "salary_min": 125000, "salary_max": 170000},
    {"title": "UX Designer", "location_text": "Nashville, TN", "lat": 36.1627, "lng": -86.7816, "remote_type": "hybrid", "tags": ["ux-design", "product-design"], "salary_min": 95000, "salary_max": 130000},
    {"title": "Ruby on Rails Developer", "location_text": "Minneapolis, MN", "lat": 44.9778, "lng": -93.2650, "remote_type": "onsite", "tags": ["ruby", "ruby-on-rails", "postgresql"], "salary_min": 110000, "salary_max": 150000},
    {"title": "AI Research Scientist", "location_text": "Pittsburgh, PA", "lat": 40.4406, "lng": -79.9959, "remote_type": "onsite", "tags": ["python", "machine-learning", "deep-learning"], "salary_min": 170000, "salary_max": 240000},
    # Asia
    {"title": "Product Manager", "location_text": "Seoul, South Korea", "lat": 37.5665, "lng": 126.9780, "remote_type": "onsite", "tags": ["analytics"], "salary_min": 50000, "salary_max": 70000},
    {"title": "Backend Engineer", "location_text": "Shenzhen, China", "lat": 22.5431, "lng": 114.0579, "remote_type": "onsite", "tags": ["golang", "python", "backend"], "salary_min": 30000, "salary_max": 50000},
    {"title": "Data Platform Engineer", "location_text": "Tel Aviv, Israel", "lat": 32.0853, "lng": 34.7818, "remote_type": "hybrid", "tags": ["python", "apache-spark", "data-engineering", "aws"], "salary_min": 60000, "salary_max": 90000},
    # More remote
    {"title": "Remote Golang Developer", "location_text": "Remote", "lat": None, "lng": None, "remote_type": "remote", "tags": ["golang", "kubernetes", "docker"], "salary_min": 140000, "salary_max": 190000},
    {"title": "Remote Product Designer", "location_text": "Remote - US", "lat": None, "lng": None, "remote_type": "remote", "tags": ["product-design", "ux-design"], "salary_min": 120000, "salary_max": 160000},
]


def run_seed(db: Session = None):
    """Insert sample companies and jobs for development."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        # Check if already seeded
        existing = db.query(Job).filter(Job.source == "seed").count()
        if existing > 0:
            print(f"Already seeded ({existing} seed jobs exist). Skipping.")
            return

        # Create companies
        companies = []
        for c_data in SAMPLE_COMPANIES:
            company = Company(name=c_data["name"], website=c_data["website"])
            db.add(company)
            companies.append(company)
        db.flush()

        # Create jobs
        for i, j_data in enumerate(SAMPLE_JOBS):
            company = companies[i % len(companies)]
            geo_wkt = f"POINT({j_data['lng']} {j_data['lat']})" if j_data.get("lat") else None

            job = Job(
                source="seed",
                source_job_id=f"seed-{i+1}",
                company_id=company.id,
                title=j_data["title"],
                description_html=f"<p>This is a sample job posting for {j_data['title']} at {company.name}.</p>",
                description_text=f"This is a sample job posting for {j_data['title']} at {company.name}.",
                apply_url=f"https://example.com/apply/{i+1}",
                remote_type=j_data["remote_type"],
                salary_min=j_data.get("salary_min"),
                salary_max=j_data.get("salary_max"),
                salary_currency="USD",
                posted_at=datetime.utcnow() - timedelta(days=random.randint(0, 30)),
                location_text=j_data["location_text"],
                city=j_data["location_text"].split(",")[0] if "," in j_data["location_text"] else None,
                country="US" if j_data["location_text"].endswith(tuple(["CA", "TX", "NY", "WA", "MA", "CO", "OR", "DC", "IL", "FL", "GA", "TN", "MN", "PA"])) else None,
                geo=geo_wkt,
                tags=j_data.get("tags", []),
                is_active=True,
            )
            db.add(job)

        db.commit()
        print(f"Seeded {len(SAMPLE_JOBS)} jobs across {len(SAMPLE_COMPANIES)} companies.")

    except Exception as e:
        db.rollback()
        print(f"Seed error: {e}")
        raise
    finally:
        if close_db:
            db.close()


if __name__ == "__main__":
    run_seed()
