"use client"

import dynamic from 'next/dynamic'

// Lazy-load PipelineBoard — heavy component with its own data fetching
const PipelineBoard = dynamic(
    () => import("@/components/pipeline-board").then(mod => ({ default: mod.PipelineBoard })),
    {
        ssr: false,
        loading: () => (
            <div className="flex justify-center items-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            </div>
        )
    }
)

export default function HRPipelinePage() {
    return (
        <div className="h-[calc(100vh-4rem)] md:h-[calc(100vh-5rem)] lg:h-[calc(100vh-7rem)] 2xl:h-[calc(100vh-10rem)] flex flex-col pt-1">
            <div className="flex items-center justify-between mb-4 shrink-0">
                <h1 className="text-3xl font-black text-foreground tracking-tight ml-2 leading-none">Hiring Pipeline</h1>
            </div>
            <div className="flex-1 min-h-0">
                <PipelineBoard />
            </div>
        </div>
    )
}
