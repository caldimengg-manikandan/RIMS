'use client'

import React, { useMemo } from 'react'
import { useParams } from 'next/navigation'
import useSWR from 'swr'
import { fetcher } from '@/app/dashboard/lib/swr-fetcher'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { API_BASE_URL } from '@/lib/config'
import { 
    Users, Search, Brain, Code, UserCheck, 
    CheckCircle2, XCircle, Clock 
} from 'lucide-react'

interface Candidate {
    id: number
    candidate_name: string
    status: string
    composite_score: number
    recommendation: string
    candidate_photo_path?: string
}

const STAGES = [
    { name: 'Application Submitted', key: 'submitted', icon: Users },
    { name: 'Resume Screening', key: 'resume_screening', icon: Search },
    { name: 'Aptitude Round', key: 'aptitude_round', icon: Clock },
    { name: 'Automated AI Interview', key: 'ai_interview', icon: Brain },
    { name: 'Technical Interview', key: 'technical_interview', icon: Code },
    { name: 'HR Interview', key: 'hr_interview', icon: UserCheck },
    { name: 'Final Decision', key: 'final_decision', icon: CheckCircle2 }
]

import { PipelineBoard } from '@/components/pipeline-board'

export default function PipelinePage() {
    const params = useParams()
    const jobId = params.id as string

    return (
        <div className="flex flex-col h-[calc(100vh-80px)] space-y-6">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 shrink-0 px-4 pt-4">
                <div>
                    <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white uppercase leading-none">
                        Job Specific Pipeline
                    </h1>
                    <p className="text-sm font-bold text-muted-foreground mt-2 uppercase tracking-widest opacity-60">
                        Managing candidates for JOB #{jobId}
                    </p>
                </div>
                <div className="flex items-center gap-2 bg-primary/10 px-4 py-2 rounded-2xl border border-primary/20 shrink-0">
                    <Users className="h-5 w-5 text-primary" />
                    <span className="text-sm font-black text-primary">LIVE PIPELINE</span>
                </div>
            </div>

            <div className="flex-1 min-h-0 w-full overflow-hidden bg-slate-50/50 dark:bg-slate-900/50 p-2 px-4 shadow-inner border-y border-slate-200/50 dark:border-slate-800/50">
                <PipelineBoard jobId={jobId} />
            </div>
        </div>
    )
}
