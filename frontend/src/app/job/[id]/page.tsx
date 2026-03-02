import type { Metadata } from "next";
import { fetchJobDetail } from "@/lib/api";

interface Props {
    params: Promise<{ id: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
    try {
        const { id } = await params;
        const job = await fetchJobDetail(id);
        return {
            title: `${job.title} at ${job.company?.name || "Unknown"} — JobMap`,
            description: job.description_text?.slice(0, 160) || `Apply for ${job.title}`,
            openGraph: {
                title: `${job.title} at ${job.company?.name || "Unknown"}`,
                description: job.description_text?.slice(0, 160) || "",
                type: "article",
            },
        };
    } catch {
        return { title: "Job Details — JobMap" };
    }
}

export default async function JobPage({ params }: Props) {
    const { id } = await params;

    let job;
    try {
        job = await fetchJobDetail(id);
    } catch {
        return (
            <div style={{ padding: 40, textAlign: "center", color: "#94a3b8" }}>
                <h1>Job not found</h1>
                <p>This job may have been removed or the link is incorrect.</p>
                <a href="/" style={{ color: "#6366f1" }}>← Back to Globe</a>
            </div>
        );
    }

    return (
        <div className="seo-job-page">
            <header className="seo-header">
                <a href="/" className="back-link">← Back to Globe</a>
            </header>
            <article className="seo-job-content">
                <h1>{job.title}</h1>
                {job.company && <p className="job-company">{job.company.name}</p>}
                <div className="badge-row">
                    <span className={`badge badge-${job.remote_type}`}>
                        {job.remote_type === "remote" ? "🌐 Remote" : job.remote_type === "hybrid" ? "🔀 Hybrid" : "🏢 On-site"}
                    </span>
                    {job.location_text && <span className="badge badge-location">📍 {job.location_text}</span>}
                </div>
                {job.description_html ? (
                    <div dangerouslySetInnerHTML={{ __html: job.description_html }} />
                ) : (
                    <p>{job.description_text}</p>
                )}
                <a href={job.apply_url} target="_blank" rel="noopener noreferrer" className="apply-btn">
                    Apply Now →
                </a>
            </article>
        </div>
    );
}
