import { JobsResponse, JobDetail, ClustersResponse, JobFilters } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

function buildParams(filters: JobFilters): URLSearchParams {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== "") {
            params.set(key, String(value));
        }
    });
    return params;
}

export async function fetchJobs(filters: JobFilters = {}): Promise<JobsResponse> {
    const params = buildParams(filters);
    const res = await fetch(`${API_BASE}/api/jobs?${params.toString()}`);
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
}

export async function fetchJobDetail(id: string): Promise<JobDetail> {
    const res = await fetch(`${API_BASE}/api/jobs/${id}`);
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
}

export async function fetchClusters(
    bbox: string,
    zoom: number,
    filters: JobFilters = {}
): Promise<ClustersResponse> {
    const params = buildParams({ ...filters, bbox, zoom });
    const res = await fetch(`${API_BASE}/api/jobs/clusters?${params.toString()}`);
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
}
