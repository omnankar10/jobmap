"use client";

import { useEffect, useRef, useImperativeHandle, forwardRef, memo } from "react";
import { JobListItem } from "@/lib/types";

export interface GlobeHandle {
    flyTo: (lat: number, lng: number, altitude?: number) => void;
}

interface GlobeProps {
    jobs: JobListItem[];
    onJobClick: (job: JobListItem) => void;
    onJobHover: (job: JobListItem | null) => void;
    selectedJobId: string | null;
}

const GlobeComponent = forwardRef<GlobeHandle, GlobeProps>(
    function GlobeComponent({ jobs, onJobClick, onJobHover, selectedJobId }, ref) {
        const containerRef = useRef<HTMLDivElement>(null);
        const globeRef = useRef<any>(null);

        // Expose flyTo to parent
        useImperativeHandle(ref, () => ({
            flyTo: (lat: number, lng: number, altitude: number = 1.8) => {
                if (globeRef.current) {
                    globeRef.current.pointOfView(
                        { lat, lng, altitude },
                        1200 // animation duration ms
                    );
                }
            },
        }));

        useEffect(() => {
            if (!containerRef.current || typeof window === "undefined") return;

            let isMounted = true;

            import("globe.gl").then((GlobeModule) => {
                if (!isMounted || !containerRef.current) return;

                const Globe = GlobeModule.default;
                const globe = new Globe(containerRef.current)
                    .globeImageUrl("//unpkg.com/three-globe/example/img/earth-blue-marble.jpg")
                    .bumpImageUrl("//unpkg.com/three-globe/example/img/earth-topology.png")
                    .backgroundImageUrl("//unpkg.com/three-globe/example/img/night-sky.png")
                    .showAtmosphere(true)
                    .atmosphereColor("#4da6ff")
                    .atmosphereAltitude(0.2)
                    .width(containerRef.current.clientWidth)
                    .height(containerRef.current.clientHeight);

                // Configure points
                globe
                    .pointsData([])
                    .pointLat("lat")
                    .pointLng("lng")
                    .pointAltitude(0.01)
                    .pointRadius((d: any) => {
                        if (d.remote_type === "remote") return 0.3;
                        return 0.4;
                    })
                    .pointColor((d: any) => {
                        if (d.id === selectedJobId) return "#FFD700";
                        if (d.remote_type === "remote") return "rgba(147, 130, 255, 0.8)";
                        if (d.remote_type === "hybrid") return "rgba(0, 210, 190, 0.85)";
                        return "rgba(255, 100, 80, 0.9)";
                    })
                    .pointsMerge(false)
                    .onPointClick((point: any) => {
                        onJobClick(point as JobListItem);
                    })
                    .onPointHover((point: any) => {
                        if (containerRef.current) {
                            containerRef.current.style.cursor = point ? "pointer" : "default";
                        }
                        onJobHover(point as JobListItem | null);
                    });

                // Auto-rotate controls
                const controls = globe.controls();
                controls.autoRotate = true;
                controls.autoRotateSpeed = 0.4;
                controls.enableDamping = true;
                controls.dampingFactor = 0.1;

                // Stop auto-rotate when user interacts, resume after 5s idle
                let idleTimer: ReturnType<typeof setTimeout> | null = null;
                const stopRotate = () => {
                    controls.autoRotate = false;
                    if (idleTimer) clearTimeout(idleTimer);
                    idleTimer = setTimeout(() => {
                        controls.autoRotate = true;
                    }, 5000);
                };

                const el = containerRef.current;
                el.addEventListener("mousedown", stopRotate);
                el.addEventListener("touchstart", stopRotate);
                el.addEventListener("wheel", stopRotate);

                globeRef.current = globe;

                // Handle resize
                const resizeObserver = new ResizeObserver(() => {
                    if (containerRef.current && globeRef.current) {
                        globeRef.current
                            .width(containerRef.current.clientWidth)
                            .height(containerRef.current.clientHeight);
                    }
                });
                resizeObserver.observe(containerRef.current);

                return () => {
                    resizeObserver.disconnect();
                    el.removeEventListener("mousedown", stopRotate);
                    el.removeEventListener("touchstart", stopRotate);
                    el.removeEventListener("wheel", stopRotate);
                    if (idleTimer) clearTimeout(idleTimer);
                };
            });

            return () => {
                isMounted = false;
                if (globeRef.current && globeRef.current._destructor) {
                    globeRef.current._destructor();
                }
            };
        }, []);

        // Update points when jobs change
        useEffect(() => {
            if (!globeRef.current) return;
            const geoJobs = jobs.filter((j) => j.lat !== null && j.lng !== null);
            globeRef.current.pointsData(geoJobs);
        }, [jobs]);

        // Update colors when selection changes
        useEffect(() => {
            if (!globeRef.current) return;
            globeRef.current.pointColor((d: any) => {
                if (d.id === selectedJobId) return "#FFD700";
                if (d.remote_type === "remote") return "rgba(147, 130, 255, 0.8)";
                if (d.remote_type === "hybrid") return "rgba(0, 210, 190, 0.85)";
                return "rgba(255, 100, 80, 0.9)";
            });
        }, [selectedJobId]);

        return (
            <div ref={containerRef} className="globe-container" />
        );
    }
);

export default memo(GlobeComponent);
