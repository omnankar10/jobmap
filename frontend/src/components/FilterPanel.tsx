"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { JobFilters } from "@/lib/types";

interface CompanyOption {
    id: string;
    name: string;
    job_count: number;
}

interface CountryOption {
    country: string;
    job_count: number;
}

interface FilterPanelProps {
    filters: JobFilters;
    onFilterChange: (filters: JobFilters) => void;
    onCountrySelect: (country: string | null) => void;
    totalCount: number;
    isCollapsed: boolean;
    onToggleCollapse: () => void;
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

const REMOTE_OPTIONS = [
    { value: "", label: "All", icon: "🌍" },
    { value: "onsite", label: "On-site", icon: "🏢" },
    { value: "hybrid", label: "Hybrid", icon: "🔀" },
    { value: "remote", label: "Remote", icon: "🌐" },
];

const RECENCY_OPTIONS = [
    { value: "", label: "Any" },
    { value: "24h", label: "24h" },
    { value: "7d", label: "7d" },
    { value: "30d", label: "30d" },
];

const POPULAR_TAGS = [
    "python", "javascript", "typescript", "react", "golang",
    "aws", "docker", "kubernetes", "machine-learning", "sql",
    "data-engineering", "full-stack", "frontend", "backend",
    "rust", "java", "security", "devops",
];

export default function FilterPanel({
    filters,
    onFilterChange,
    onCountrySelect,
    totalCount,
    isCollapsed,
    onToggleCollapse,
}: FilterPanelProps) {
    const [search, setSearch] = useState(filters.q || "");
    const debounceRef = useRef<NodeJS.Timeout | null>(null);

    // Fetch companies for dropdown
    const { data: companies } = useQuery<CompanyOption[]>({
        queryKey: ["companies"],
        queryFn: async () => {
            const res = await fetch(`${API_BASE}/api/companies`);
            if (!res.ok) return [];
            return res.json();
        },
        staleTime: 5 * 60 * 1000,
    });

    // Fetch countries for dropdown
    const { data: countries } = useQuery<CountryOption[]>({
        queryKey: ["countries"],
        queryFn: async () => {
            const res = await fetch(`${API_BASE}/api/countries`);
            if (!res.ok) return [];
            return res.json();
        },
        staleTime: 5 * 60 * 1000,
    });

    // Debounced search
    useEffect(() => {
        if (debounceRef.current) clearTimeout(debounceRef.current);
        debounceRef.current = setTimeout(() => {
            onFilterChange({ ...filters, q: search || undefined });
        }, 300);
        return () => {
            if (debounceRef.current) clearTimeout(debounceRef.current);
        };
    }, [search]);

    const selectedTags = filters.tags ? filters.tags.split(",") : [];

    const toggleTag = useCallback(
        (tag: string) => {
            const current = new Set(selectedTags);
            if (current.has(tag)) {
                current.delete(tag);
            } else {
                current.add(tag);
            }
            const tagStr = Array.from(current).join(",");
            onFilterChange({ ...filters, tags: tagStr || undefined });
        },
        [filters, selectedTags, onFilterChange]
    );

    const handleCountryChange = useCallback(
        (country: string) => {
            onFilterChange({ ...filters, country: country || undefined });
            onCountrySelect(country || null);
        },
        [filters, onFilterChange, onCountrySelect]
    );

    return (
        <div className={`filter-panel ${isCollapsed ? "collapsed" : ""}`}>
            {/* Header */}
            <div className="filter-header">
                <div className="filter-title-row">
                    <div className="logo-area">
                        <span className="logo-icon">🌍</span>
                        <h2>JobMap</h2>
                    </div>
                    <button
                        className="collapse-btn"
                        onClick={onToggleCollapse}
                        aria-label={isCollapsed ? "Expand filters" : "Collapse filters"}
                    >
                        {isCollapsed ? "▶" : "◀"}
                    </button>
                </div>
                <div className="result-count">
                    <span className="count-number">{totalCount.toLocaleString()}</span>
                    <span className="count-label"> jobs worldwide</span>
                </div>
            </div>

            {!isCollapsed && (
                <div className="filter-body">
                    {/* Search */}
                    <div className="filter-group">
                        <label htmlFor="search-input">
                            <svg className="label-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="14" height="14">
                                <circle cx="11" cy="11" r="8" />
                                <path d="m21 21-4.3-4.3" />
                            </svg>
                            Search
                        </label>
                        <div className="search-input-wrapper">
                            <svg className="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <circle cx="11" cy="11" r="8" />
                                <path d="m21 21-4.3-4.3" />
                            </svg>
                            <input
                                id="search-input"
                                type="text"
                                placeholder="Job title, company, skills..."
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                            />
                            {search && (
                                <button className="clear-search" onClick={() => setSearch("")}>
                                    ✕
                                </button>
                            )}
                        </div>
                    </div>

                    {/* Country Filter */}
                    <div className="filter-group">
                        <label htmlFor="country-select">
                            <span className="label-emoji">📍</span>
                            Country
                        </label>
                        <select
                            id="country-select"
                            className="filter-select"
                            value={filters.country || ""}
                            onChange={(e) => handleCountryChange(e.target.value)}
                        >
                            <option value="">All Countries</option>
                            {countries?.map((c) => (
                                <option key={c.country} value={c.country}>
                                    {c.country} ({c.job_count})
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Company Filter */}
                    <div className="filter-group">
                        <label htmlFor="company-select">
                            <span className="label-emoji">🏛️</span>
                            Company
                        </label>
                        <select
                            id="company-select"
                            className="filter-select"
                            value={filters.company_id || ""}
                            onChange={(e) =>
                                onFilterChange({
                                    ...filters,
                                    company_id: e.target.value || undefined,
                                })
                            }
                        >
                            <option value="">All Companies</option>
                            {companies?.map((c) => (
                                <option key={c.id} value={c.id}>
                                    {c.name} ({c.job_count})
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Work Type */}
                    <div className="filter-group">
                        <label>
                            <span className="label-emoji">💼</span>
                            Work Type
                        </label>
                        <div className="radio-group">
                            {REMOTE_OPTIONS.map((opt) => (
                                <button
                                    key={opt.value}
                                    className={`radio-pill ${(filters.remote_type || "") === opt.value ? "active" : ""}`}
                                    onClick={() =>
                                        onFilterChange({
                                            ...filters,
                                            remote_type: opt.value || undefined,
                                        })
                                    }
                                >
                                    <span className="pill-icon">{opt.icon}</span>
                                    {opt.label}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Recency */}
                    <div className="filter-group">
                        <label>
                            <span className="label-emoji">🕐</span>
                            Posted
                        </label>
                        <div className="radio-group recency-group">
                            {RECENCY_OPTIONS.map((opt) => (
                                <button
                                    key={opt.value}
                                    className={`radio-pill recency-pill ${(filters.posted_since || "") === opt.value ? "active" : ""}`}
                                    onClick={() =>
                                        onFilterChange({
                                            ...filters,
                                            posted_since: opt.value || undefined,
                                        })
                                    }
                                >
                                    {opt.label}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Tags */}
                    <div className="filter-group">
                        <label>
                            <span className="label-emoji">🏷️</span>
                            Skills & Tags
                        </label>
                        <div className="tag-grid">
                            {POPULAR_TAGS.map((tag) => (
                                <button
                                    key={tag}
                                    className={`tag-chip ${selectedTags.includes(tag) ? "active" : ""}`}
                                    onClick={() => toggleTag(tag)}
                                >
                                    {tag}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Divider + Reset */}
                    <div className="filter-footer">
                        <button
                            className="reset-btn"
                            onClick={() => {
                                setSearch("");
                                onFilterChange({});
                                onCountrySelect(null);
                            }}
                        >
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="14" height="14">
                                <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" />
                                <path d="M21 3v5h-5" />
                                <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" />
                                <path d="M8 16H3v5" />
                            </svg>
                            Reset All Filters
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
