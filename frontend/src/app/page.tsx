"use client";

import { useState, useCallback, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchJobs } from "@/lib/api";
import { JobFilters, JobListItem } from "@/lib/types";
import FilterPanel from "@/components/FilterPanel";
import JobDrawer from "@/components/JobDrawer";
import JobTable from "@/components/JobTable";
import dynamic from "next/dynamic";
import type { GlobeHandle } from "@/components/Globe";

// Country center coordinates for globe navigation
const COUNTRY_COORDS: Record<string, { lat: number; lng: number }> = {
  "United States": { lat: 39.8, lng: -98.5 },
  "United Kingdom": { lat: 54.0, lng: -2.0 },
  "Canada": { lat: 56.1, lng: -106.3 },
  "Germany": { lat: 51.2, lng: 10.4 },
  "France": { lat: 46.6, lng: 2.2 },
  "India": { lat: 20.6, lng: 78.9 },
  "Australia": { lat: -25.3, lng: 133.8 },
  "Netherlands": { lat: 52.1, lng: 5.3 },
  "Spain": { lat: 40.5, lng: -3.7 },
  "Sweden": { lat: 60.1, lng: 18.6 },
  "Ireland": { lat: 53.1, lng: -7.7 },
  "Switzerland": { lat: 46.8, lng: 8.2 },
  "Brazil": { lat: -14.2, lng: -51.9 },
  "Japan": { lat: 36.2, lng: 138.3 },
  "Singapore": { lat: 1.4, lng: 103.8 },
  "Poland": { lat: 51.9, lng: 19.1 },
  "Italy": { lat: 41.9, lng: 12.6 },
  "Portugal": { lat: 39.4, lng: -8.2 },
  "Finland": { lat: 61.9, lng: 25.7 },
  "Norway": { lat: 60.5, lng: 8.5 },
  "Denmark": { lat: 56.3, lng: 9.5 },
  "Austria": { lat: 47.5, lng: 14.6 },
  "Belgium": { lat: 50.5, lng: 4.5 },
  "Israel": { lat: 31.0, lng: 34.9 },
  "Mexico": { lat: 23.6, lng: -102.6 },
  "South Korea": { lat: 35.9, lng: 127.8 },
  "Argentina": { lat: -38.4, lng: -63.6 },
  "Czech Republic": { lat: 49.8, lng: 15.5 },
  "Romania": { lat: 45.9, lng: 24.97 },
  "Colombia": { lat: 4.6, lng: -74.1 },
  "China": { lat: 35.9, lng: 104.2 },
  "Taiwan": { lat: 23.7, lng: 121.0 },
  "New Zealand": { lat: -40.9, lng: 174.9 },
  "South Africa": { lat: -30.6, lng: 22.9 },
  "United Arab Emirates": { lat: 23.4, lng: 53.8 },
  "Remote": { lat: 20.0, lng: 0.0 },
};

// Dynamic import for Globe (SSR incompatible — uses WebGL + window)
const Globe = dynamic(() => import("@/components/Globe"), {
  ssr: false,
  loading: () => (
    <div className="globe-loading">
      <div className="loading-spinner" />
      <p>Loading globe...</p>
    </div>
  ),
});

type ViewMode = "globe" | "table";

export default function HomePage() {
  const [filters, setFilters] = useState<JobFilters>({});
  const [selectedJob, setSelectedJob] = useState<JobListItem | null>(null);
  const [hoveredJob, setHoveredJob] = useState<JobListItem | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [isFilterCollapsed, setIsFilterCollapsed] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>("globe");
  const globeRef = useRef<GlobeHandle>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["jobs", filters],
    queryFn: () => fetchJobs({ ...filters, limit: 500 }),
  });

  const jobs = data?.items || [];
  const totalCount = data?.meta?.total || 0;

  const handleJobClick = useCallback((job: JobListItem) => {
    setSelectedJob(job);
    setIsDrawerOpen(true);
  }, []);

  const handleJobHover = useCallback((job: JobListItem | null) => {
    setHoveredJob(job);
  }, []);

  const handleCloseDrawer = useCallback(() => {
    setIsDrawerOpen(false);
    setTimeout(() => setSelectedJob(null), 300);
  }, []);

  const handleFilterChange = useCallback((newFilters: JobFilters) => {
    setFilters(newFilters);
  }, []);

  const handleCountrySelect = useCallback((country: string | null) => {
    if (country && globeRef.current) {
      const coords = COUNTRY_COORDS[country];
      if (coords) {
        globeRef.current.flyTo(coords.lat, coords.lng, 1.8);
      }
    }
    if (!country && globeRef.current) {
      globeRef.current.flyTo(20, 0, 2.5);
    }
  }, []);

  return (
    <main className="app-layout">
      {/* Filter Panel */}
      <FilterPanel
        filters={filters}
        onFilterChange={handleFilterChange}
        onCountrySelect={handleCountrySelect}
        totalCount={totalCount}
        isCollapsed={isFilterCollapsed}
        onToggleCollapse={() => setIsFilterCollapsed(!isFilterCollapsed)}
      />

      {/* Main Content */}
      <div className="globe-wrapper">
        {/* View Toggle */}
        <div className="view-toggle">
          <button
            className={`toggle-btn ${viewMode === "globe" ? "active" : ""}`}
            onClick={() => setViewMode("globe")}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
              <circle cx="12" cy="12" r="10" />
              <path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
            </svg>
            Globe
          </button>
          <button
            className={`toggle-btn ${viewMode === "table" ? "active" : ""}`}
            onClick={() => setViewMode("table")}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <path d="M3 9h18M3 15h18M9 3v18" />
            </svg>
            Table
          </button>
        </div>

        {viewMode === "globe" ? (
          <>
            {error ? (
              <div className="error-state">
                <h3>Unable to load jobs</h3>
                <p>Check that the backend is running at {process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"}</p>
              </div>
            ) : (
              <Globe
                ref={globeRef}
                jobs={jobs}
                onJobClick={handleJobClick}
                onJobHover={handleJobHover}
                selectedJobId={selectedJob?.id || null}
              />
            )}

            {/* Hover Tooltip */}
            {hoveredJob && (
              <div className="globe-tooltip">
                <div className="tooltip-title">{hoveredJob.title}</div>
                {hoveredJob.company && (
                  <div className="tooltip-company">{hoveredJob.company.name}</div>
                )}
                {hoveredJob.location_text && (
                  <div className="tooltip-location">{hoveredJob.location_text}</div>
                )}
              </div>
            )}

            {/* Loading overlay */}
            {isLoading && (
              <div className="loading-overlay">
                <div className="loading-spinner" />
              </div>
            )}

            {/* Legend */}
            <div className="globe-legend">
              <div className="legend-item">
                <span className="legend-dot onsite" />
                On-site
              </div>
              <div className="legend-item">
                <span className="legend-dot hybrid" />
                Hybrid
              </div>
              <div className="legend-item">
                <span className="legend-dot remote" />
                Remote
              </div>
            </div>

            {/* No results */}
            {!isLoading && jobs.length === 0 && (
              <div className="no-results">
                <h3>No jobs found</h3>
                <p>Try adjusting your filters</p>
              </div>
            )}
          </>
        ) : (
          <JobTable
            jobs={jobs}
            onJobClick={handleJobClick}
            isLoading={isLoading}
          />
        )}
      </div>

      {/* Job Detail Drawer */}
      <JobDrawer
        job={selectedJob}
        isOpen={isDrawerOpen}
        onClose={handleCloseDrawer}
      />

      {/* Backdrop */}
      {isDrawerOpen && <div className="drawer-backdrop" onClick={handleCloseDrawer} />}
    </main>
  );
}
