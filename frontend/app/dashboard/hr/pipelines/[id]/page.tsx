'use client'

import React from 'react'
import { useParams, useRouter } from 'next/navigation'
import { Button } from "@/components/ui/button"
import { ArrowLeft, Users } from 'lucide-react'
import { PipelineBoard } from '@/components/pipeline-board'
import useSWR from 'swr'
import { fetcher } from '@/app/dashboard/lib/swr-fetcher'

export default function PipelinePage() {
    const router = useRouter()
    const params = useParams()
    const jobId = params.id as string

    // Fetch job details to get the job name
    const { data: job } = useSWR<any>(jobId ? `/api/jobs/${jobId}` : null, fetcher)

    return (
        <div className="flex flex-col h-[calc(100vh-80px)] space-y-6">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 shrink-0 px-4 pt-4">
                <div className="space-y-4">
                    <Button
                        variant="ghost"
                        onClick={() => router.push('/dashboard/hr/pipeline')} 
                        className="gap-2 text-muted-foreground hover:text-foreground h-auto p-0 flex items-center transition-colors group"
                    >
                        <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-1" />
                        <span className="text-sm font-bold">Back to Pipeline</span>
                    </Button>
                    <div>
                        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white uppercase leading-none">
                            Job Specific Pipeline for {job?.title || `JOB #${jobId}`}
                        </h1>

                    </div>
                </div>
                <div className="flex items-center gap-2 bg-primary/10 dark:bg-primary/20 px-4 py-2 rounded-2xl border border-primary/20 shrink-0">
                    <Users className="h-5 w-5 text-primary dark:text-blue-200" />
                    <span className="text-sm font-black text-primary dark:text-blue-50">LIVE PIPELINE</span>
                </div>
            </div>

            <div className="flex-1 min-h-0 w-full overflow-hidden bg-slate-50/50 dark:bg-slate-900/50 p-2 px-4 shadow-inner border-y border-slate-200/50 dark:border-slate-800/50">
                <PipelineBoard jobId={jobId} />
            </div>
        </div>
    )
}
