"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchJobDetail } from "@/lib/api";
import { JobListItem } from "@/lib/types";
import { useMemo } from "react";

interface JobDrawerProps {
    job: JobListItem | null;
    isOpen: boolean;
    onClose: () => void;
}

function formatSalary(min: number | null, max: number | null, currency?: string | null): string {
    const fmt = (n: number) =>
        new Intl.NumberFormat("en-US", {
            style: "currency",
            currency: currency || "USD",
            maximumFractionDigits: 0,
        }).format(n);

    if (min && max) return `${fmt(min)} – ${fmt(max)}`;
    if (min) return `From ${fmt(min)}`;
    if (max) return `Up to ${fmt(max)}`;
    return "Not specified";
}

function formatDate(dateStr: string | null): string {
    if (!dateStr) return "Unknown";
    const date = new Date(dateStr);
    const now = new Date();
    const diff = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));
    if (diff === 0) return "Today";
    if (diff === 1) return "Yesterday";
    if (diff < 7) return `${diff} days ago`;
    if (diff < 30) return `${Math.floor(diff / 7)} weeks ago`;
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

/**
 * Sanitize and clean up HTML description for display.
 * Removes script tags, on* attributes, and fixes common formatting issues.
 */
function sanitizeHtml(html: string): string {
    if (!html) return "";
    let cleaned = html
        // Remove script tags
        .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, "")
        // Remove on* event handlers
        .replace(/\son\w+="[^"]*"/gi, "")
        .replace(/\son\w+='[^']*'/gi, "")
        // Remove style attributes (they often break the layout)
        .replace(/\sstyle="[^"]*"/gi, "")
        // Remove class attributes from source HTML 
        .replace(/\sclass="[^"]*"/gi, "");
    return cleaned;
}

const REMOTE_BADGE: Record<string, { label: string; class: string }> = {
    remote: { label: "🌐 Remote", class: "badge-remote" },
    hybrid: { label: "🔀 Hybrid", class: "badge-hybrid" },
    onsite: { label: "🏢 On-site", class: "badge-onsite" },
};

export default function JobDrawer({ job, isOpen, onClose }: JobDrawerProps) {
    const { data: detail, isLoading } = useQuery({
        queryKey: ["job-detail", job?.id],
        queryFn: () => fetchJobDetail(job!.id),
        enabled: !!job?.id && isOpen,
        staleTime: 60 * 1000,
    });

    const cleanDescription = useMemo(() => {
        // Try description_html first
        if (detail?.description_html) {
            return sanitizeHtml(detail.description_html);
        }
        // Fallback: if description_text contains HTML tags, render as HTML
        if (detail?.description_text && /<[a-z][\s\S]*>/i.test(detail.description_text)) {
            return sanitizeHtml(detail.description_text);
        }
        return null;
    }, [detail?.description_html, detail?.description_text]);

    if (!isOpen || !job) return null;

    const badge = REMOTE_BADGE[job.remote_type] || REMOTE_BADGE.onsite;

    return (
        <div className={`job-drawer ${isOpen ? "open" : ""}`}>
            <div className="drawer-header">
                <button className="drawer-close" onClick={onClose} aria-label="Close">
                    ✕
                </button>
            </div>

            <div className="drawer-content">
                {/* Title & Company */}
                <h2 className="job-title">{job.title}</h2>
                {job.company && (
                    <p className="job-company">{job.company.name}</p>
                )}

                {/* Badges Row */}
                <div className="badge-row">
                    <span className={`badge ${badge.class}`}>{badge.label}</span>
                    {job.location_text && (
                        <span className="badge badge-location">📍 {job.location_text}</span>
                    )}
                </div>

                {/* Meta */}
                <div className="job-meta">
                    <div className="meta-item">
                        <span className="meta-label">Posted</span>
                        <span className="meta-value">{formatDate(job.posted_at)}</span>
                    </div>
                    <div className="meta-item">
                        <span className="meta-label">Salary</span>
                        <span className="meta-value">
                            {formatSalary(job.salary_min, job.salary_max)}
                        </span>
                    </div>
                    {detail?.employment_type && (
                        <div className="meta-item">
                            <span className="meta-label">Type</span>
                            <span className="meta-value">{detail.employment_type}</span>
                        </div>
                    )}
                </div>

                {/* Tags */}
                {job.tags && job.tags.length > 0 && (
                    <div className="job-tags">
                        {job.tags.map((tag) => (
                            <span key={tag} className="job-tag">
                                {tag}
                            </span>
                        ))}
                    </div>
                )}

                {/* Description */}
                {isLoading ? (
                    <div className="loading-skeleton">
                        <div className="skeleton-line" />
                        <div className="skeleton-line short" />
                        <div className="skeleton-line" />
                        <div className="skeleton-line short" />
                    </div>
                ) : cleanDescription ? (
                    <div className="job-description">
                        <h3>Description</h3>
                        <div
                            className="description-content"
                            dangerouslySetInnerHTML={{ __html: cleanDescription }}
                        />
                    </div>
                ) : detail?.description_text ? (
                    <div className="job-description">
                        <h3>Description</h3>
                        <p>{detail.description_text}</p>
                    </div>
                ) : null}

                {/* Apply Button */}
                <a
                    href={detail?.apply_url || "#"}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="apply-btn"
                >
                    Apply Now →
                </a>
            </div>
        </div>
    );
}
