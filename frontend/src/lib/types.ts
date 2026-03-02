export interface CompanyData {
    id: string;
    name: string;
    website?: string | null;
    logo_url?: string | null;
}

export interface JobListItem {
    id: string;
    title: string;
    company: CompanyData | null;
    remote_type: "remote" | "hybrid" | "onsite";
    location_text: string | null;
    posted_at: string | null;
    lat: number | null;
    lng: number | null;
    salary_min: number | null;
    salary_max: number | null;
    tags: string[] | null;
}

export interface JobDetail extends JobListItem {
    source: string;
    city: string | null;
    region: string | null;
    country: string | null;
    salary_currency: string | null;
    description_html: string | null;
    description_text: string | null;
    apply_url: string;
    employment_type: string | null;
    is_active: boolean;
}

export interface JobsResponse {
    items: JobListItem[];
    meta: { total: number };
}

export interface ClusterItem {
    lat: number;
    lng: number;
    count: number;
    bbox: number[] | null;
}

export interface ClustersResponse {
    clusters: ClusterItem[];
    points: JobListItem[];
}

export interface JobFilters {
    q?: string;
    remote_type?: string;
    posted_since?: string;
    salary_min?: number;
    salary_max?: number;
    tags?: string;
    country?: string;
    region?: string;
    city?: string;
    company_id?: string;
    bbox?: string;
    zoom?: number;
    limit?: number;
    offset?: number;
}
