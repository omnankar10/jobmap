"use client";

import { JobListItem } from "@/lib/types";

interface TooltipProps {
    job: JobListItem | null;
    position: { x: number; y: number } | null;
}

export default function Tooltip({ job, position }: TooltipProps) {
    if (!job || !position) return null;

    return (
        <div
            className="globe-tooltip"
            style={{
                left: position.x + 15,
                top: position.y - 10,
            }}
        >
            <div className="tooltip-title">{job.title}</div>
            {job.company && (
                <div className="tooltip-company">{job.company.name}</div>
            )}
            {job.location_text && (
                <div className="tooltip-location">{job.location_text}</div>
            )}
        </div>
    );
}
