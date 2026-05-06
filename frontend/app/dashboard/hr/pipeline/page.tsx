'use client'

import React, { useState, useMemo } from 'react'
import useSWR from 'swr'
import { fetcher } from '@/app/dashboard/lib/swr-fetcher'
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Briefcase, ArrowRight, Layers, Users, UserCheck, Search } from 'lucide-react'
import { PageHeader } from '@/components/page-header'
import Link from 'next/link'
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table"
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import { ChevronLeft, ChevronRight } from 'lucide-react'

interface Job {
    id: number
    job_id: string
    title: string
    status: string
    created_at: string
    application_count?: number
}

export default function PipelineIndexPage() {
    const { data: jobs, isLoading } = useSWR<Job[]>('/api/jobs?limit=500', fetcher)
    const [currentPage, setCurrentPage] = useState(1)
    const [pageSize, setPageSize] = useState(10)

    const paginatedJobs = useMemo(() => {
        if (!jobs) return []
        const start = (currentPage - 1) * pageSize
        return jobs.slice(start, start + pageSize)
    }, [jobs, currentPage, pageSize])

    const totalPages = Math.ceil((jobs?.length || 0) / pageSize)

    if (isLoading) return (
        <div className="p-8 flex justify-center items-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
    )

    return (
        <div className="p-6 space-y-8 animate-in fade-in duration-500">
            <PageHeader
                title="Hiring Pipelines"
                description="Manage candidate flow for each active position"
                icon={UserCheck}
            >
                <div className="flex items-center gap-2 bg-primary/10 dark:bg-white/5 px-6 py-4 rounded-2xl border border-primary/20 dark:border-white/10 shadow-sm">
                    <Layers className="h-5 w-5 text-primary dark:text-slate-200" />
                    <span className="text-l font-black text-primary dark:text-white tabular-nums">{jobs?.length || 0} Active Roles</span>
                </div>
            </PageHeader>

            <Card className="border-border/50 shadow-sm overflow-hidden">
                <Table>
                    <TableHeader>
                        <TableRow className="bg-muted/20 hover:bg-muted/20">
                            <TableHead className="font-bold py-4">Job Title & ID</TableHead>
                            <TableHead className="font-bold text-center">Status</TableHead>
                            <TableHead className="font-bold text-center">Pipeline</TableHead>
                            <TableHead className="font-bold text-right pr-6">Action</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {paginatedJobs.map((job) => (
                            <TableRow key={job.id} className="hover:bg-primary/5 transition-colors group">
                                <TableCell className="py-4">
                                    <div className="flex items-center gap-3">
                                        <div className="h-10 w-10 rounded-xl bg-primary/10 flex items-center justify-center shrink-0 group-hover:bg-primary group-hover:text-white transition-colors">
                                            <Briefcase className="h-5 w-5" />
                                        </div>
                                        <div className="flex flex-col">
                                            <span className="font-bold text-foreground uppercase tracking-tight">{job.title}</span>
                                            <span className="text-[10px] font-mono text-muted-foreground opacity-60">#{job.job_id}</span>
                                        </div>
                                    </div>
                                </TableCell>
                                <TableCell className="text-center">
                                    <Badge variant={job.status === 'open' ? 'default' : 'secondary'} className="text-[10px] uppercase font-black px-2 py-0">
                                        {job.status}
                                    </Badge>
                                </TableCell>
                                <TableCell className="text-center">
                                    <div className="flex flex-col items-center gap-1">
                                        <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-medium">
                                            <Users className="h-3.5 w-3.5" />
                                            <span>Full Pipeline</span>
                                        </div>
                                    </div>
                                </TableCell>
                                <TableCell className="text-right pr-6">
                                    <Link href={`/dashboard/hr/pipelines/${job.id}`}>
                                        <Button variant="ghost" className="h-9 gap-2 font-bold text-primary group-hover:translate-x-1 transition-transform">
                                            Open Pipeline
                                            <ArrowRight className="h-4 w-4" />
                                        </Button>
                                    </Link>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>



                {jobs?.length === 0 && (
                    <div className="text-center py-20">
                        <Briefcase className="h-12 w-12 mx-auto text-slate-300 mb-4" />
                        <h3 className="text-xl font-bold text-slate-900 dark:text-white">No active jobs found</h3>
                        <p className="text-muted-foreground mt-2">Create a job posting to start building your pipeline</p>
                        <Link href="/dashboard/hr/jobs/create" className="mt-6 inline-block">
                            <Button className="rounded-xl px-8 font-bold">Create Your First Job</Button>
                        </Link>
                    </div>
                )}
            </Card>

            {totalPages > 1 && (
                <div className="sticky bottom-6 bg-background/80 backdrop-blur-xl border-t border-border p-4 -mx-6 z-30 shadow-[0_-4px_12px_-4px_rgba(0,0,0,0.1)] mt-8">
                    <div className="flex flex-col sm:flex-row items-center justify-between gap-4 max-w-[1600px] mx-auto px-6">
                        <div className="text-sm font-bold text-muted-foreground uppercase tracking-widest">
                            Showing {((currentPage - 1) * pageSize) + 1} - {Math.min(currentPage * pageSize, jobs?.length || 0)} of {jobs?.length || 0}
                        </div>
                        <div className="flex items-center gap-3">
                            <Button
                                variant="outline"
                                size="lg"
                                onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                                disabled={currentPage === 1}
                                className="h-11 px-6 rounded-xl font-bold bg-background dark:bg-muted hover:bg-accent border-border transition-all shadow-sm active:scale-95 disabled:opacity-50"
                            >
                                <ChevronLeft className="mr-2 h-5 w-5" /> Previous
                            </Button>
                            <div className="px-4 py-2 bg-slate-100 dark:bg-slate-800 rounded-lg text-sm font-bold text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700">
                                Page {currentPage} of {totalPages}
                            </div>
                            <Button
                                variant="outline"
                                size="lg"
                                onClick={() => setCurrentPage(prev => prev + 1)}
                                disabled={currentPage >= totalPages}
                                className="h-11 px-6 rounded-xl font-bold bg-background dark:bg-muted hover:bg-accent border-border transition-all shadow-sm active:scale-95 disabled:opacity-50"
                            >
                                Next <ChevronRight className="ml-2 h-5 w-5" />
                            </Button>
                        </div>

                        <div className="flex items-center gap-2">
                            <span className="text-sm font-bold text-muted-foreground">Show</span>
                            <Select
                                value={String(pageSize)}
                                onValueChange={(val) => {
                                    setPageSize(Number(val));
                                    setCurrentPage(1);
                                }}
                            >
                                <SelectTrigger className="h-10 w-[85px] rounded-xl border-border bg-background font-bold shadow-none focus:ring-0">
                                    <SelectValue placeholder="10" />
                                </SelectTrigger>
                                <SelectContent className="min-w-[70px]">
                                    {[5, 10, 20, 50, 100].map((size) => (
                                        <SelectItem key={size} value={String(size)} className="font-bold">
                                            {size}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            <span className="text-sm font-bold text-muted-foreground">per page</span>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
