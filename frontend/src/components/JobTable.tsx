"use client";

import { JobListItem } from "@/lib/types";

interface JobTableProps {
    jobs: JobListItem[];
    onJobClick: (job: JobListItem) => void;
    isLoading: boolean;
}

function formatDate(dateStr: string | null): string {
    if (!dateStr) return "—";
    const date = new Date(dateStr);
    const now = new Date();
    const diff = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));
    if (diff === 0) return "Today";
    if (diff === 1) return "Yesterday";
    if (diff < 7) return `${diff}d ago`;
    if (diff < 30) return `${Math.floor(diff / 7)}w ago`;
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

const REMOTE_LABELS: Record<string, { label: string; className: string }> = {
    remote: { label: "Remote", className: "type-remote" },
    hybrid: { label: "Hybrid", className: "type-hybrid" },
    onsite: { label: "On-site", className: "type-onsite" },
};

export default function JobTable({ jobs, onJobClick, isLoading }: JobTableProps) {
    if (isLoading) {
        return (
            <div className="table-wrapper">
                <div className="table-loading">
                    <div className="loading-spinner" />
                    <p>Loading jobs...</p>
                </div>
            </div>
        );
    }

    if (jobs.length === 0) {
        return (
            <div className="table-wrapper">
                <div className="table-empty">
                    <h3>No jobs found</h3>
                    <p>Try adjusting your filters</p>
                </div>
            </div>
        );
    }

    return (
        <div className="table-wrapper">
            <table className="job-table">
                <thead>
                    <tr>
                        <th>Title</th>
                        <th>Company</th>
                        <th>Country</th>
                        <th>Type</th>
                        <th>Posted</th>
                        <th>Tags</th>
                        <th>Apply</th>
                    </tr>
                </thead>
                <tbody>
                    {jobs.map((job) => {
                        const typeInfo = REMOTE_LABELS[job.remote_type] || REMOTE_LABELS.onsite;
                        return (
                            <tr key={job.id} onClick={() => onJobClick(job)}>
                                <td className="col-title">
                                    <span className="title-text">{job.title}</span>
                                </td>
                                <td className="col-company">
                                    {job.company?.name || "—"}
                                </td>
                                <td className="col-country">
                                    {job.location_text || "—"}
                                </td>
                                <td className="col-type">
                                    <span className={`type-badge ${typeInfo.className}`}>
                                        {typeInfo.label}
                                    </span>
                                </td>
                                <td className="col-date">
                                    {formatDate(job.posted_at)}
                                </td>
                                <td className="col-tags">
                                    {job.tags?.slice(0, 3).map((tag) => (
                                        <span key={tag} className="table-tag">{tag}</span>
                                    ))}
                                    {job.tags && job.tags.length > 3 && (
                                        <span className="table-tag more">+{job.tags.length - 3}</span>
                                    )}
                                </td>
                                <td className="col-apply">
                                    <button
                                        className="apply-link"
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            onJobClick(job);
                                        }}
                                    >
                                        View →
                                    </button>
                                </td>
                            </tr>
                        );
                    })}
                </tbody>
            </table>
        </div>
    );
}
