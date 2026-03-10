'use client'

import React, { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { APIClient } from '@/app/dashboard/lib/api-client'
import { RejectDialog } from '@/components/reject-dialog'
import useSWR, { useSWRConfig } from 'swr'
import { fetcher } from '@/app/dashboard/lib/swr-fetcher'
import { useRouter } from 'next/navigation'

interface Application {
    id: number
    status: string
    applied_at: string
    candidate_name: string
    candidate_email: string
    job: {
        id: number
        job_id: string | null
        title: string
    }
    interview: {
        id: number
        test_id: string | null
        report: {
            aptitude_score: number | null
            technical_skills_score: number | null
            behavioral_score: number | null
        } | null
    } | null
    resume_extraction: {
        resume_score: number
        skill_match_percentage: number
    } | null
}

export default function HRApplicationsPage() {
    const router = useRouter()
    const { data: applications = [], error, isLoading, mutate } = useSWR<Application[]>(
        '/api/applications',
        (url: string) => fetcher<Application[]>(url),
        { keepPreviousData: true }
    )
    const { mutate: globalMutate } = useSWRConfig()

    const handleDecision = async (applicationId: number, decision: 'hired' | 'rejected', reason?: string, notes?: string) => {
        // Optimistic update
        const updatedApps = applications.map(app =>
            app.id === applicationId ? { ...app, status: decision === 'hired' ? 'hired' : 'rejected_post_interview' } : app
        )

        try {
            // Update local cache immediately
            mutate(updatedApps, false)

            let userComments = `Candidate ${decision} via quick action in applications list.`
            if (decision === 'rejected') {
                userComments = `Reason: ${reason}${notes ? `\nNotes: ${notes}` : ''}`
            }

            await APIClient.put(`/api/decisions/applications/${applicationId}/decide`, {
                decision,
                decision_comments: userComments
            })

            // Revalidate
            mutate()
            // Also update dashboard stats if they are cached
            globalMutate('/api/analytics/dashboard')
        } catch (err) {
            // Rollback on error
            mutate()
            console.error("Failed to make decision:", err)
            const errorMsg = (err as any)?.response?.data?.detail || "Failed to make decision. Ensure the candidate has completed the interview Round."
            alert(errorMsg)
            throw err;
        }
    }

    const handleStatusUpdate = async (applicationId: number, status: string, reason?: string, notes?: string) => {
        // Optimistic update
        const updatedApps = applications.map(app =>
            app.id === applicationId ? { ...app, status } : app
        )

        try {
            mutate(updatedApps, false)

            let userNotes = `Status updated to ${status} via quick action.`
            if (status === 'rejected') {
                userNotes = `Reason: ${reason}${notes ? `\nNotes: ${notes}` : ''}`
            }

            await APIClient.put(`/api/applications/${applicationId}/status`, {
                status,
                hr_notes: userNotes
            })

            mutate()
            globalMutate('/api/analytics/dashboard')
        } catch (err) {
            mutate()
            console.error("Failed to update status:", err)
            const errorMsg = (err as any)?.response?.data?.detail || "Failed to update status."
            alert(errorMsg)
            throw err;
        }
    }

    const [searchTerm, setSearchTerm] = useState('')
    const [statusFilter, setStatusFilter] = useState('all')
    const [sortBy, setSortBy] = useState('newest')
    const [jobTitleFilter, setJobTitleFilter] = useState('all')
    const [dateFilter, setDateFilter] = useState('')
    const [jobIdFilter, setJobIdFilter] = useState('')
    const [candidateIdFilter, setCandidateIdFilter] = useState('')

    // Get unique job titles for the filter dropdown
    const jobTitles = Array.from(new Set(applications.map(app => app.job.title))).sort()

    const filteredApplications = applications.filter(app => {
        // Global search (candidate name or job title)
        const matchesSearch =
            (app.candidate_name || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
            app.job.title.toLowerCase().includes(searchTerm.toLowerCase())

        // Status filter
        let matchesStatus = statusFilter === 'all' || app.status === statusFilter
        if (statusFilter === 'rejected') {
            matchesStatus = app.status === 'rejected' || app.status === 'rejected_post_interview'
        }

        // Job Title filter
        const matchesJobTitle = jobTitleFilter === 'all' || app.job.title === jobTitleFilter

        // Date filter (matching YYYY-MM-DD)
        const appDate = new Date(app.applied_at).toISOString().split('T')[0]
        const matchesDate = !dateFilter || appDate === dateFilter

        // Job ID filter (matches custom ID or DB ID)
        const matchesJobId = !jobIdFilter ||
            (app.job.job_id || "").toLowerCase().includes(jobIdFilter.toLowerCase()) ||
            app.job.id.toString().includes(jobIdFilter)

        // Candidate ID filter (matches DB ID)
        const matchesCandidateId = !candidateIdFilter ||
            app.id.toString().includes(candidateIdFilter)

        return matchesSearch && matchesStatus && matchesJobTitle && matchesDate && matchesJobId && matchesCandidateId
    }).sort((a, b) => {
        // Define statuses that should be pushed to the bottom
        const bottomStatuses = ['review_later', 'hired', 'rejected', 'rejected_post_interview']
        const aIsBottom = bottomStatuses.includes(a.status)
        const bIsBottom = bottomStatuses.includes(b.status)

        // If one is a "bottom" status and the other isn't, sort accordingly
        if (aIsBottom && !bIsBottom) return 1
        if (!aIsBottom && bIsBottom) return -1

        // If both are in the same tier (both top or both bottom), apply user's selected sort
        if (sortBy === 'newest') return new Date(b.applied_at).getTime() - new Date(a.applied_at).getTime()
        if (sortBy === 'oldest') return new Date(a.applied_at).getTime() - new Date(b.applied_at).getTime()
        if (sortBy === 'score_desc') return (b.resume_extraction?.resume_score || 0) - (a.resume_extraction?.resume_score || 0)
        if (sortBy === 'score_asc') return (a.resume_extraction?.resume_score || 0) - (b.resume_extraction?.resume_score || 0)
        return 0
    })

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'submitted': return 'capsule-badge-primary'
            case 'review_later': return 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20'
            case 'approved_for_interview': return 'capsule-badge-info'
            case 'interview_completed': return 'capsule-badge-primary'
            case 'hired': return 'capsule-badge-success'
            case 'rejected':
            case 'rejected_post_interview': return 'capsule-badge-destructive'
            default: return 'capsule-badge-neutral'
        }
    }

    return (
        <div className="space-y-8">
            <h1 className="text-4xl font-black text-foreground mb-2 tracking-tight">Applications</h1>
            <p className="text-muted-foreground mb-8">Review and manage candidate applications.</p>

            {/* Filters Toolbar */}
            <div className="bg-card p-6 rounded-2xl border border-border/50 shadow-sm mb-8 animate-in fade-in slide-in-from-top-4 duration-700 ease-out">
                <div className="flex flex-col gap-6">
                    {/* Row 1: Search and Status */}
                    <div className="flex flex-wrap gap-6 items-center">
                        <div className="flex-1 min-w-[300px]">
                            <div className="relative group">
                                <svg className="absolute left-4 top-1/2 transform -translate-y-1/2 text-muted-foreground group-focus-within:text-primary h-5 w-5 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                                </svg>
                                <input
                                    type="text"
                                    placeholder="Search candidate or job..."
                                    className="w-full pl-12 pr-4 h-11 bg-background border-2 border-input rounded-xl focus:outline-none focus:ring-4 focus:ring-primary/5 focus:border-primary transition-all text-base placeholder:text-muted-foreground text-foreground"
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                />
                            </div>
                        </div>

                        <div className="flex flex-wrap gap-4">
                            <select
                                className="px-4 h-11 bg-background border-2 border-input rounded-xl text-base font-medium focus:outline-none focus:ring-4 focus:ring-primary/5 focus:border-primary transition-all text-foreground cursor-pointer"
                                value={statusFilter}
                                onChange={(e) => setStatusFilter(e.target.value)}
                            >
                                <option value="all">All Statuses</option>
                                <option value="submitted">Submitted</option>
                                <option value="review_later">Review Later</option>
                                <option value="approved_for_interview">Approved for Interview</option>
                                <option value="interview_completed">Interview Completed</option>
                                <option value="hired">Hired</option>
                                <option value="rejected">Rejected</option>
                            </select>

                            <select
                                className="px-4 h-11 bg-background border-2 border-input rounded-xl text-base font-medium focus:outline-none focus:ring-4 focus:ring-primary/5 focus:border-primary transition-all text-foreground cursor-pointer"
                                value={sortBy}
                                onChange={(e) => setSortBy(e.target.value)}
                            >
                                <option value="newest">Newest First</option>
                                <option value="oldest">Oldest First</option>
                                <option value="score_desc">Highest Match Score</option>
                                <option value="score_asc">Lowest Match Score</option>
                            </select>
                        </div>
                    </div>

                    {/* Row 2: Advanced Filters */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        <div className="flex flex-col gap-1.5">
                            <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider ml-1">Job Title</label>
                            <select
                                className="w-full px-4 h-11 bg-background border-2 border-input rounded-xl text-sm font-medium focus:outline-none focus:ring-4 focus:ring-primary/5 focus:border-primary transition-all text-foreground cursor-pointer"
                                value={jobTitleFilter}
                                onChange={(e) => setJobTitleFilter(e.target.value)}
                            >
                                <option value="all">All Jobs</option>
                                {jobTitles.map(title => (
                                    <option key={title} value={title}>{title}</option>
                                ))}
                            </select>
                        </div>

                        <div className="flex flex-col gap-1.5">
                            <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider ml-1">Date Applied</label>
                            <input
                                type="date"
                                className="w-full px-4 h-11 bg-background border-2 border-input rounded-xl text-sm font-medium focus:outline-none focus:ring-4 focus:ring-primary/5 focus:border-primary transition-all text-foreground"
                                value={dateFilter}
                                onChange={(e) => setDateFilter(e.target.value)}
                            />
                        </div>

                        <div className="flex flex-col gap-1.5">
                            <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider ml-1">Job ID</label>
                            <input
                                type="text"
                                placeholder="Filter by Job ID..."
                                className="w-full px-4 h-11 bg-background border-2 border-input rounded-xl text-sm font-medium focus:outline-none focus:ring-4 focus:ring-primary/5 focus:border-primary transition-all text-foreground placeholder:text-muted-foreground"
                                value={jobIdFilter}
                                onChange={(e) => setJobIdFilter(e.target.value)}
                            />
                        </div>

                        <div className="flex flex-col gap-1.5">
                            <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider ml-1">Candidate ID</label>
                            <input
                                type="text"
                                placeholder="Filter by Cand. ID..."
                                className="w-full px-4 h-11 bg-background border-2 border-input rounded-xl text-sm font-medium focus:outline-none focus:ring-4 focus:ring-primary/5 focus:border-primary transition-all text-foreground placeholder:text-muted-foreground"
                                value={candidateIdFilter}
                                onChange={(e) => setCandidateIdFilter(e.target.value)}
                            />
                        </div>
                    </div>
                </div>
            </div>

            {isLoading ? (
                <div className="text-center py-12">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
                </div>
            ) : filteredApplications.length === 0 ? (
                <div className="text-center py-16 bg-card rounded-xl border border-border">
                    <p className="text-muted-foreground">No applications match your filtering criteria.</p>
                </div>
            ) : (
                <div className="flex flex-col gap-4">
                    {filteredApplications.map((app, index) => (
                        <Card 
                            key={app.id}
                            onClick={() => router.push(`/dashboard/hr/applications/${app.id}`)}
                            style={{ animationDelay: `${index * 50}ms` }} 
                            className="hover:shadow-md transition-all duration-300 bg-card border border-border hover:border-border/80 cursor-pointer group animate-in fade-in slide-in-from-bottom-4 duration-500 ease-out fill-mode-both"
                        >
                                <CardContent className="p-4 flex items-center justify-between">
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2 mb-1">
                                            <h3 className="text-base font-bold text-foreground group-hover:text-primary transition-colors">{app.candidate_name}</h3>
                                            {app.interview?.test_id && (
                                                <span className="text-[10px] bg-muted px-1.5 py-0.5 rounded text-muted-foreground border border-border">
                                                    {app.interview.test_id}
                                                </span>
                                            )}
                                        </div>
                                        <p className="text-sm text-muted-foreground">Applied for <span className="font-medium text-foreground">{app.job.title}</span></p>
                                        <div className="flex flex-wrap gap-2 mt-2 text-xs text-muted-foreground items-center">
                                            <span className="flex items-center gap-1 whitespace-nowrap">
                                                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                                </svg>
                                                {new Date(app.applied_at).toLocaleDateString()}
                                            </span>
                                            {app.resume_extraction && (
                                                <span className="text-primary font-medium bg-primary/10 px-2 py-0.5 rounded-sm border border-primary/20 whitespace-nowrap">
                                                    Job Compatibility: {Number(app.resume_extraction.resume_score).toFixed(2)}/10
                                                </span>
                                            )}
                                            {app.interview?.report && (
                                                <div className="flex flex-wrap gap-1.5">
                                                    {app.interview.report.aptitude_score !== null && (
                                                        <span className="text-purple-600 font-medium bg-purple-100 px-2 py-0.5 rounded-sm border border-purple-200 whitespace-nowrap">
                                                            Aptitude: {Number(app.interview.report.aptitude_score).toFixed(2)}/10
                                                        </span>
                                                    )}
                                                    {app.interview.report.technical_skills_score !== null && (
                                                        <span className="text-blue-600 font-medium bg-blue-100 px-2 py-0.5 rounded-sm border border-blue-200 whitespace-nowrap">
                                                            Tech: {Number(app.interview.report.technical_skills_score).toFixed(2)}/10
                                                        </span>
                                                    )}
                                                    {app.interview.report.behavioral_score !== null && (
                                                        <span className="text-green-600 font-medium bg-green-100 px-2 py-0.5 rounded-sm border border-green-200 whitespace-nowrap">
                                                            Behav: {Number(app.interview.report.behavioral_score).toFixed(2)}/10
                                                        </span>
                                                    )}
                                                </div>
                                            )}
                                        </div>

                                        {/* Dynamic Action Buttons */}
                                        <div className="flex gap-2 mt-3" onClick={(e) => e.stopPropagation()}>
                                            {(app.status === 'submitted' || app.status === 'review_later') && (
                                                <>
                                                    <Button
                                                        size="sm"
                                                        className="bg-primary hover:bg-primary/90 text-[10px] font-semibold px-3 py-1 h-7 rounded shadow-sm transition-all"
                                                        onClick={(e) => {
                                                            e.preventDefault();
                                                            handleStatusUpdate(app.id, 'approved_for_interview');
                                                        }}
                                                    >
                                                        APPROVE FOR INTERVIEW
                                                    </Button>
                                                    <RejectDialog
                                                        candidateName={app.candidate_name}
                                                        onConfirm={(reason, notes) => handleStatusUpdate(app.id, 'rejected', reason, notes)}
                                                        trigger={
                                                            <Button
                                                                variant="destructive"
                                                                size="sm"
                                                                className="bg-red-500 hover:bg-red-600 text-[10px] font-semibold px-3 py-1 h-7 rounded shadow-sm transition-all"
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                }}
                                                            >
                                                                REJECT
                                                            </Button>
                                                        }
                                                    />
                                                </>
                                            )}

                                            {/* Stage 2: Interview Completed */}
                                            {app.status === 'interview_completed' && (
                                                <>
                                                    <Button
                                                        size="sm"
                                                        variant="outline"
                                                        className="border-amber-500/50 text-amber-600 dark:text-amber-400 hover:bg-amber-500/10 text-[10px] font-semibold px-3 py-1 h-7 rounded shadow-sm transition-all mr-2"
                                                        onClick={(e) => {
                                                            e.preventDefault();
                                                            handleStatusUpdate(app.id, 'review_later');
                                                        }}
                                                    >
                                                        REVIEW LATER
                                                    </Button>
                                                    <Button
                                                        size="sm"
                                                        className="bg-primary hover:bg-primary/90 text-[10px] font-semibold px-3 py-1 h-7 rounded shadow-sm transition-all"
                                                        onClick={(e) => {
                                                            e.preventDefault();
                                                            handleDecision(app.id, 'hired');
                                                        }}
                                                    >
                                                        HIRE CANDIDATE
                                                    </Button>
                                                    <RejectDialog
                                                        candidateName={app.candidate_name}
                                                        onConfirm={(reason, notes) => handleDecision(app.id, 'rejected', reason, notes)}
                                                        trigger={
                                                            <Button
                                                                variant="destructive"
                                                                size="sm"
                                                                className="bg-red-500 hover:bg-red-600 text-[10px] font-semibold px-3 py-1 h-7 rounded shadow-sm transition-all"
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                }}
                                                            >
                                                                REJECT
                                                            </Button>
                                                        }
                                                    />
                                                </>
                                            )}

                                            {/* Stage 3: Approved but not interviewed - can still Reject or Review Later */}
                                            {app.status === 'approved_for_interview' && (
                                                <>
                                                    <Button
                                                        size="sm"
                                                        variant="outline"
                                                        className="border-amber-500/50 text-amber-600 dark:text-amber-400 hover:bg-amber-500/10 text-[10px] font-semibold px-3 py-1 h-7 rounded shadow-sm transition-all mr-2"
                                                        onClick={(e) => {
                                                            e.preventDefault();
                                                            handleStatusUpdate(app.id, 'review_later');
                                                        }}
                                                    >
                                                        REVIEW LATER
                                                    </Button>
                                                    <RejectDialog
                                                        candidateName={app.candidate_name}
                                                        onConfirm={(reason, notes) => handleStatusUpdate(app.id, 'rejected', reason, notes)}
                                                        trigger={
                                                            <Button
                                                                variant="destructive"
                                                                size="sm"
                                                                className="bg-red-500 hover:bg-red-600 text-[10px] font-semibold px-3 py-1 h-7 rounded shadow-sm transition-all"
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                }}
                                                            >
                                                                REJECT APPLICATION
                                                            </Button>
                                                        }
                                                    />
                                                </>
                                            )}
                                        </div>
                                    </div>
                                    <div className="flex flex-col items-end gap-1.5 shrink-0">
                                        <span className={`capsule-badge text-[10px] px-2 py-0.5 ${getStatusColor(app.status)}`}>
                                            {app.status.replace(/_/g, ' ').toUpperCase()}
                                        </span>
                                        <span className="text-primary text-xs font-medium group-hover:underline flex items-center gap-1">
                                            View Details
                                            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                            </svg>
                                        </span>
                                    </div>
                                </CardContent>
                            </Card>
                    ))}
                </div>
            )}
        </div>
    )
}
