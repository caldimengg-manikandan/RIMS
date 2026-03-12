'use client'

import React from 'react'
import useSWR from 'swr'
import { fetcher } from '@/app/dashboard/lib/swr-fetcher'
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Briefcase, ArrowRight, Layers, Users } from 'lucide-react'
import Link from 'next/link'

interface Job {
    id: number
    job_id: string
    title: string
    status: string
    created_at: string
    application_count?: number
}

export default function PipelineIndexPage() {
    const { data: jobs, isLoading } = useSWR<Job[]>('/api/jobs', fetcher)

    if (isLoading) return (
        <div className="p-8 flex justify-center items-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
    )

    return (
        <div className="p-6 space-y-8 animate-in fade-in duration-500">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
                        Hiring Pipelines
                    </h1>
                    <p className="text-muted-foreground mt-1">Manage candidate flow for each active position</p>
                </div>
                <div className="flex items-center gap-2 bg-primary/5 px-4 py-2 rounded-2xl border border-primary/10">
                    <Layers className="h-5 w-5 text-primary" />
                    <span className="text-sm font-bold text-primary">{jobs?.length || 0} Active Roles</span>
                </div>
            </div>

            <div className="grid gap-4">
                {jobs?.map((job) => (
                    <Link key={job.id} href={`/dashboard/hr/pipelines/${job.id}`}>
                        <Card className="group hover:border-primary/50 hover:shadow-md transition-all duration-300 border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-2xl overflow-hidden cursor-pointer">
                            <CardContent className="p-0">
                                <div className="flex flex-col md:flex-row md:items-center justify-between p-5 gap-4">
                                    <div className="flex items-center gap-4">
                                        <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center shrink-0 group-hover:bg-primary group-hover:text-white transition-colors">
                                            <Briefcase className="h-6 w-6" />
                                        </div>
                                        <div>
                                            <div className="flex items-center gap-2">
                                                <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100 uppercase tracking-tight">
                                                    {job.title}
                                                </h3>
                                                <Badge variant={job.status === 'open' ? 'default' : 'secondary'} className="text-[10px] uppercase font-black px-2 py-0">
                                                    {job.status}
                                                </Badge>
                                            </div>
                                            <div className="flex items-center gap-3 mt-1 text-sm text-muted-foreground font-medium">
                                                <span className="font-mono text-xs opacity-60">#{job.job_id}</span>
                                                <span className="h-1 w-1 rounded-full bg-slate-300" />
                                                <div className="flex items-center gap-1.5">
                                                    <Users className="h-3.5 w-3.5" />
                                                    <span>View Full Pipeline</span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                    
                                    <div className="flex items-center gap-4 md:border-l border-slate-100 dark:border-slate-800 md:pl-8">
                                        <Button variant="ghost" className="hidden md:flex items-center gap-2 font-bold text-primary group-hover:translate-x-1 transition-transform">
                                            Open Pipeline
                                            <ArrowRight className="h-4 w-4" />
                                        </Button>
                                        <div className="md:hidden flex justify-end">
                                             <ArrowRight className="h-5 w-5 text-primary" />
                                        </div>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    </Link>
                ))}

                {jobs?.length === 0 && (
                    <div className="text-center py-20 bg-slate-50 dark:bg-slate-800/20 rounded-3xl border-2 border-dashed border-slate-200 dark:border-slate-800">
                        <Briefcase className="h-12 w-12 mx-auto text-slate-300 mb-4" />
                        <h3 className="text-xl font-bold text-slate-900 dark:text-white">No active jobs found</h3>
                        <p className="text-muted-foreground mt-2">Create a job posting to start building your pipeline</p>
                        <Link href="/dashboard/hr/jobs/create" className="mt-6 inline-block">
                            <Button>Create Your First Job</Button>
                        </Link>
                    </div>
                )}
            </div>
        </div>
    )
}
