'use client'

import React, { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/app/dashboard/lib/auth-context'
import { APIClient } from '@/app/dashboard/lib/api-client'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Edit2, ChevronRight, Activity, FileText } from 'lucide-react'
import useSWR from 'swr'
import { fetcher } from '@/app/dashboard/lib/swr-fetcher'
import { performMutation } from '@/app/dashboard/lib/swr-utils'

interface Job {
    id: number
    job_id: string
    title: string
    description: string
    experience_level: string
    status: string
    created_at: string
    closed_at?: string | null
    duration_minutes?: number
}

export default function HRJobsPage() {
    const { user } = useAuth()
    const router = useRouter()
    const { data: jobs = [], error: fetchError, isLoading, mutate } = useSWR<Job[]>(
        '/api/jobs?limit=500',
        fetcher,
    )
    const [error, setError] = useState('')

    const handleClose = async (jobId: number) => {
        if (!confirm('Are you sure you want to close this job? Applications will be retained.')) return

        await performMutation<Job[]>(
            '/api/jobs',
            mutate,
            () => APIClient.put(`/api/jobs/${jobId}`, { status: 'closed' }),
            {
                lockKey: `job-${jobId}`,
                optimisticData: (current) => (current || []).map(job =>
                    job.id === jobId ? { ...job, status: 'closed' } : job
                ),
                successMessage: 'Job closed successfully',
                invalidateKeys: ['/api/analytics/dashboard']
            }
        )
    }

    const handleDelete = async (jobId: number) => {
        if (!confirm('Are you sure you want to DELETE this job? All applications will be permanently removed.')) return

        await performMutation<Job[]>(
            '/api/jobs',
            mutate,
            () => APIClient.delete(`/api/jobs/${jobId}`),
            {
                lockKey: `job-${jobId}`,
                optimisticData: (current) => (current || []).filter(job => job.id !== jobId),
                successMessage: 'Job deleted successfully',
                invalidateKeys: ['/api/analytics/dashboard']
            }
        )
    }

    // Filter Logic
    const [searchTerm, setSearchTerm] = useState('')
    const [statusFilter, setStatusFilter] = useState('all') // 'all', 'open', 'closed'
    const [sortBy, setSortBy] = useState('newest')
    
    // Pagination state
    const [currentPage, setCurrentPage] = useState(1)
    const JOBS_PER_PAGE = 10

    const filteredJobs = jobs.filter(job => {
        const matchesSearch =
            job.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
            job.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
            (job.job_id && job.job_id.toLowerCase().includes(searchTerm.toLowerCase()))
        const matchesStatus = statusFilter === 'all' || job.status === statusFilter
        return matchesSearch && matchesStatus
    }).sort((a, b) => {
        if (sortBy === 'newest') return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        if (sortBy === 'oldest') return new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
        if (sortBy === 'job_id_asc') return (a.job_id || "").localeCompare(b.job_id || "")
        if (sortBy === 'job_id_desc') return (b.job_id || "").localeCompare(a.job_id || "")
        return 0
    })

    const totalPages = Math.ceil(filteredJobs.length / JOBS_PER_PAGE)
    const paginatedJobs = filteredJobs.slice(
        (currentPage - 1) * JOBS_PER_PAGE,
        currentPage * JOBS_PER_PAGE
    )

    return (
        <div className="space-y-8 overflow-x-hidden">
            {/* Header */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8">
                <div>
                    <h1 className="text-2xl sm:text-3xl font-bold text-foreground">Job Postings</h1>
                    <p className="text-muted-foreground mt-2">Manage your active job listings</p>
                </div>
                <Link href="/dashboard/hr/jobs/create">
                    <Button className="bg-primary hover:bg-primary/90 text-primary-foreground w-full sm:w-auto">Create New Job</Button>
                </Link>
            </div>

            {/* Filter Toolbar */}
            <div className="bg-card/50 p-3 sm:p-4 rounded-lg border border-border shadow-sm mb-6 flex flex-col sm:flex-row gap-3 sm:gap-4 items-stretch sm:items-center justify-between animate-in fade-in slide-in-from-top-4 duration-700 ease-out">
                <div className="flex-1 min-w-0">
                    <div className="relative">
                        <svg className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                        <input
                            type="text"
                            placeholder="Search by title or Job ID..."
                            className="w-full pl-10 pr-4 py-2 border border-input rounded-md focus:ring-2 focus:ring-primary focus:border-primary outline-none text-sm bg-background text-foreground"
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                        />
                    </div>
                </div>

                <div className="flex gap-2 sm:gap-4 w-full sm:w-auto">
                    <select
                        className="px-3 py-2 border border-input rounded-md text-sm focus:ring-2 focus:ring-primary outline-none bg-background text-foreground"
                        value={statusFilter}
                        onChange={(e) => setStatusFilter(e.target.value)}
                    >
                        <option value="all">All Statuses</option>
                        <option value="open">Open</option>
                        <option value="closed">Closed</option>
                    </select>

                    <select
                        className="px-3 py-2 border border-input rounded-md text-sm focus:ring-2 focus:ring-primary outline-none bg-background text-foreground"
                        value={sortBy}
                        onChange={(e) => setSortBy(e.target.value)}
                    >
                        <option value="newest">Newest First</option>
                        <option value="oldest">Oldest First</option>
                        <option value="job_id_asc">Job ID (A-Z)</option>
                        <option value="job_id_desc">Job ID (Z-A)</option>
                    </select>
                </div>
            </div>

            {error && (
                <div className="bg-destructive/10 text-destructive p-4 rounded-lg mb-6 border border-destructive/20 ">
                    {error}
                </div>
            )}

            {isLoading ? (
                <div className="text-center py-12">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
                </div>
            ) : filteredJobs.length === 0 ? (
                <div className="text-center py-16 bg-card/50 rounded-xl border border-border shadow-sm">
                    <div className="mb-4 text-muted-foreground">
                        <svg className="w-12 h-12 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                        </svg>
                    </div>
                    <h3 className="text-lg font-medium text-foreground mb-2">No jobs match your filters</h3>
                    <p className="text-muted-foreground mb-6 max-w-md mx-auto">Try adjusting your search criteria or create a new job.</p>
                    <Link href="/dashboard/hr/jobs/create">
                        <Button variant="outline">Create Job</Button>
                    </Link>
                </div>
            ) : (
                <div className="space-y-6">
                    <div className="grid gap-6">
                        {paginatedJobs.map((job, index) => (
                            <Card
                            key={job.id}
                            style={{ animationDelay: `${index * 150}ms` }}
                            onClick={() => router.push(`/dashboard/hr/jobs/${job.id}/edit`)}
                            className="hover:shadow-lg transition-all duration-300 bg-card border-border group hover:-translate-y-1 animate-in fade-in slide-in-from-bottom-8 duration-700 ease-out fill-mode-both cursor-pointer block relative"
                        >
                            <CardHeader className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-2">
                                <div>
                                    <CardTitle className="text-xl font-bold text-foreground group-hover:text-primary transition-colors">
                                        <div className="flex items-center gap-3">
                                            {job.job_id && (
                                                <span className="text-xs font-mono text-muted-foreground bg-muted px-2 py-0.5 rounded border border-border">
                                                    {job.job_id}
                                                </span>
                                            )}
                                            <Link href={`/jobs/${job.job_id || job.id}`} target="_blank" rel="noopener noreferrer" className="hover:underline">
                                                {job.title}
                                            </Link>
                                        </div>
                                    </CardTitle>
                                    <div className="flex flex-col mt-1">
                                        <CardDescription className="flex items-center gap-2 text-muted-foreground">
                                            <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${job.status === 'open' ? 'bg-primary/10 text-primary border-primary/20 shadow-sm' : job.status === 'closed' ? 'bg-red-100 text-red-600 border-red-200 shadow-sm' : 'bg-muted text-muted-foreground border-border'
                                                }`}>
                                                {job.status.toUpperCase()}
                                            </span>
                                            <span className="text-muted-foreground/30">•</span>
                                            <span>{job.experience_level.replace('_', ' ')}</span>
                                            <span className="text-muted-foreground/30">•</span>
                                            <span>Posted {new Date(job.created_at).toLocaleDateString()}</span>
                                            {job.duration_minutes && (
                                                <>
                                                    <span className="text-muted-foreground/30">•</span>
                                                    <span className="flex items-center gap-1">
                                                        <Activity className="w-3 h-3" />
                                                        {job.duration_minutes} mins
                                                    </span>
                                                </>
                                            )}
                                        </CardDescription>
                                        {job.status === 'closed' && job.closed_at && (
                                            <span className="text-xs text-muted-foreground mt-1 ml-1">
                                                Closed on {new Date(job.closed_at).toLocaleDateString()}
                                            </span>
                                        )}
                                    </div>
                                </div>
                                <div className="flex flex-wrap items-center gap-1 sm:gap-2 w-full sm:w-auto mt-2 sm:mt-0">
                                    {job.status === 'open' && (
                                        <>
                                            <Link href={`/dashboard/hr/pipelines/${job.id}`} onClick={(e) => e.stopPropagation()}>
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    className="text-primary hover:text-primary/90 hover:bg-primary/10 h-8 px-2"
                                                >
                                                    <Activity className="w-4 h-4 mr-1" /> Pipeline
                                                </Button>
                                            </Link>
                                            <Link href={`/dashboard/hr/ranking/${job.id}`} onClick={(e) => e.stopPropagation()}>
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    className="text-primary hover:text-primary/90 hover:bg-primary/10 h-8 px-2"
                                                >
                                                    <FileText className="w-4 h-4 mr-1" /> Leaderboard
                                                </Button>
                                            </Link>
                                            <Link href={`/dashboard/hr/jobs/${job.id}/edit`} onClick={(e) => e.stopPropagation()}>
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    className="text-primary hover:text-primary/90 hover:bg-primary/10 h-8 px-2"
                                                >
                                                    <Edit2 className="w-4 h-4 mr-1" /> Edit
                                                </Button>
                                            </Link>
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                className="text-muted-foreground hover:text-foreground hover:bg-secondary border-border h-8 pl-2 pr-2"
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    handleClose(job.id);
                                                }}
                                            >
                                                Close
                                            </Button>
                                        </>
                                    )}
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className="text-destructive hover:text-destructive hover:bg-destructive/10 h-8"
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            handleDelete(job.id);
                                        }}
                                    >
                                        Delete
                                    </Button>
                                </div>
                            </CardHeader>
                            <CardContent>
                                <div className="space-y-4 relative pr-10">
                                    <div>
                                        <h4 className="text-sm font-semibold text-muted-foreground mb-1 uppercase tracking-wide">Description</h4>
                                        <p className="text-muted-foreground text-sm line-clamp-2 leading-relaxed">{job.description}</p>
                                    </div>
                                    {/* Clickable Indicator */}
                                    <div className="absolute top-1/2 -translate-y-1/2 right-0 opacity-0 -translate-x-4 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-300 text-muted-foreground">
                                        <ChevronRight className="w-6 h-6" />
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                    </div>

                    {/* Pagination Controls */}
                    {totalPages > 1 && (
                        <div className="flex items-center justify-between pt-4 border-t border-border">
                            <span className="text-sm text-muted-foreground">
                                Showing {((currentPage - 1) * JOBS_PER_PAGE) + 1} to {Math.min(currentPage * JOBS_PER_PAGE, filteredJobs.length)} of {filteredJobs.length} jobs
                            </span>
                            <div className="flex gap-2">
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                                    disabled={currentPage === 1}
                                >
                                    Previous
                                </Button>
                                <div className="flex items-center gap-1">
                                    {Array.from({ length: totalPages }).map((_, i) => (
                                        <Button
                                            key={i}
                                            variant={currentPage === i + 1 ? "default" : "ghost"}
                                            size="sm"
                                            className="w-8 h-8 p-0"
                                            onClick={() => setCurrentPage(i + 1)}
                                        >
                                            {i + 1}
                                        </Button>
                                    ))}
                                </div>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                                    disabled={currentPage === totalPages}
                                >
                                    Next
                                </Button>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}
