'use client'

import React, { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { APIClient } from '@/app/dashboard/lib/api-client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
    DialogDescription,
} from "@/components/ui/dialog"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { RejectDialog } from "@/components/reject-dialog"
import useSWR, { useSWRConfig } from 'swr'
import { fetcher } from '@/app/dashboard/lib/swr-fetcher'
import { API_BASE_URL } from '@/lib/config'

export default function HRApplicationDetailPage() {
    const params = useParams()
    const router = useRouter()
    const applicationId = params.id as string
    const { mutate: globalMutate } = useSWRConfig()

    const { data: application, error: appError, isLoading: appLoading, mutate: mutateApp } = useSWR<any>(`/api/applications/${applicationId}`, (url: string) => fetcher<any>(url))

    // Conditional fetching for the report
    const { data: interviewReport, isLoading: reportLoading, mutate: mutateReport } = useSWR(
        application?.interview?.status === 'completed' ? `/api/interviews/${application.interview.id}/report` : null,
        (url: string) => fetcher<any>(url)
    )

    const isLoading = appLoading || (application?.interview?.status === 'completed' && reportLoading && !interviewReport)
    const [isUpdating, setIsUpdating] = useState(false)

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'hired': return 'bg-primary/10 text-primary border-primary/20'
            case 'rejected': return 'bg-destructive/10 text-destructive border-destructive/20'
            case 'review_later': return 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20'
            case 'interview_scheduled':
            case 'approved_for_interview': return 'bg-accent/10 text-accent border-accent/20'
            case 'interview_completed': return 'bg-primary/10 text-primary border-primary/20'
            default: return 'bg-muted text-muted-foreground border-border'
        }
    }

    const getStatusLabel = (status: string) => {
        return status?.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ') || status
    }


    const updateStatus = async (newStatus: string, reason?: string, notes?: string) => {
        // Only ask confirmation if it's not a rejection (rejection has its own dialog)
        if (newStatus !== 'rejected' && !confirm(`Are you sure you want to update status to: ${newStatus}?`)) return

        // Optimistic update
        const originalData = application
        const updatedData = { ...application, status: newStatus }

        setIsUpdating(true)
        try {
            mutateApp(updatedData, false)

            let userNotes = `Status updated to ${newStatus} by HR`
            if (newStatus === 'rejected') {
                userNotes = `Reason: ${reason}${notes ? `\nNotes: ${notes}` : ''}`
            }

            await APIClient.put(`/api/applications/${applicationId}/status`, {
                status: newStatus,
                hr_notes: userNotes
            })

            mutateApp() // Revalidate
            globalMutate('/api/analytics/dashboard')
            globalMutate('/api/applications')
        } catch (err) {
            mutateApp(originalData, false)
            alert('Failed to update status')
            throw err;
        } finally {
            setIsUpdating(false)
        }
    }

    const makeDecision = async (decision: 'rejected' | 'hired', reason?: string, notes?: string) => {
        // Only ask confirmation if it's a hire (rejection has its own dialog)
        if (decision === 'hired' && !confirm(`Final Decision: HIRED. This action is permanent.`)) return

        setIsUpdating(true)
        try {
            let userComments = `Manual decision by HR: ${decision}`
            if (decision === 'rejected') {
                userComments = `Reason: ${reason}${notes ? `\nNotes: ${notes}` : ''}`
            }

            await APIClient.put(`/api/decisions/applications/${applicationId}/decide`, {
                decision,
                decision_comments: userComments
            })
            router.push('/dashboard/hr/applications')
        } catch (err) {
            alert('Failed to record decision')
            throw err;
        } finally {
            setIsUpdating(false)
        }
    }

    if (isLoading) return <div className="p-8 text-center text-muted-foreground">Loading details...</div>
    if (!application) return <div className="p-8 text-center text-destructive">Application not found</div>

    return (
        <div className="p-8 max-w-5xl mx-auto space-y-6">
            <div className="flex justify-between items-start animate-in fade-in slide-in-from-top-4 duration-700 ease-out fill-mode-both">
                <div className="flex items-center gap-6">
                    <Avatar className="h-24 w-24 border-2 border-border/50 shadow-sm">
                        {application.candidate_photo_path ? (
                            <AvatarImage
                                src={`${API_BASE_URL}/uploads/${application.candidate_photo_path.replace(/\\/g, '/')}`}
                                alt={application.candidate_name}
                                className="object-cover"
                            />
                        ) : (
                            <AvatarFallback className="text-2xl font-bold bg-muted text-muted-foreground">
                                {application.candidate_name.charAt(0).toUpperCase()}
                            </AvatarFallback>
                        )}
                    </Avatar>
                    <div>
                        <h1 className="text-3xl font-bold text-foreground">{application.candidate_name}</h1>
                        <p className="text-muted-foreground">{application.candidate_email}</p>
                        <div className="mt-2 text-sm text-muted-foreground">
                            Applying for <span className="font-semibold text-foreground">{application.job.title}</span>
                        </div>
                    </div>
                </div>
                <div className="flex flex-col items-end gap-3">
                    <span className={`px-3 py-1 rounded-full text-xs font-medium border ${getStatusColor(application.status)}`}>
                        {getStatusLabel(application.status)}
                    </span>
                    <div className="flex gap-2">
                        {(application.status === 'submitted' || application.status === 'review_later') && (
                            <>
                                <Button
                                    onClick={() => updateStatus('approved_for_interview')}
                                    className="bg-primary hover:bg-primary/90 text-primary-foreground"
                                    disabled={isUpdating}
                                >
                                    Approve for Interview
                                </Button>
                                <RejectDialog
                                    candidateName={application.candidate_name}
                                    onConfirm={(reason, notes) => updateStatus('rejected', reason, notes)}
                                    trigger={
                                        <Button
                                            variant="destructive"
                                            disabled={isUpdating}
                                        >
                                            Reject Application
                                        </Button>
                                    }
                                />
                            </>
                        )}

                        {(application.status === 'interview_completed' || application.status === 'approved_for_interview') && (
                            <div className="flex gap-2">
                                <Button
                                    onClick={() => updateStatus('review_later')}
                                    variant="outline"
                                    className="border-amber-500/50 text-amber-600 dark:text-amber-400 hover:bg-amber-500/10"
                                    disabled={isUpdating}
                                >
                                    Review Later
                                </Button>
                                <Button
                                    className="bg-primary text-primary-foreground hover:bg-primary/90"
                                    onClick={() => makeDecision('hired')}
                                    disabled={isUpdating}
                                >
                                    CALL FOR FACE TO FACE INTERVIEW
                                </Button>
                                <RejectDialog
                                    candidateName={application.candidate_name}
                                    onConfirm={(reason, notes) => makeDecision('rejected', reason, notes)}
                                    trigger={
                                        <Button
                                            variant="destructive"
                                            disabled={isUpdating}
                                        >
                                            REJECT
                                        </Button>
                                    }
                                />
                            </div>
                        )}

                    </div>
                </div>
            </div>

            {application.status === 'rejected' && application.hr_notes && (
                <div className="bg-destructive/10 border border-destructive/20 text-destructive p-4 rounded-xl flex items-start gap-3 animate-in fade-in slide-in-from-top-4 duration-700 delay-75">
                    <svg className="w-5 h-5 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
                    <div>
                        <h4 className="font-semibold text-sm">Application Rejected</h4>
                        <p className="text-sm mt-1">{application.hr_notes}</p>
                    </div>
                </div>
            )}

            <div className="grid md:grid-cols-2 gap-6">
                {/* Resume Analysis */}
                <Card className="animate-in fade-in slide-in-from-bottom-8 duration-700 ease-out fill-mode-both delay-100">
                    <CardHeader>
                        <CardTitle>AI Resume Analysis</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {application.resume_extraction ? (
                            <>
                                <div className="flex justify-between text-sm border-b border-border pb-2">
                                    <span className="text-muted-foreground">ATS Score</span>
                                    <span className="font-bold text-accent">{Number(application.resume_extraction.skill_match_percentage).toFixed(2)}%</span>
                                </div>

                                <div>
                                    <h4 className="font-semibold text-sm mb-1">Extracted Skills</h4>
                                    <p className="text-sm text-muted-foreground bg-muted/50 p-2 rounded">
                                        {application.resume_extraction.extracted_skills || 'None detected'}
                                    </p>
                                </div>
                                <div>
                                    <h4 className="font-semibold text-sm mb-1">Summary</h4>
                                    <div className="text-sm text-foreground">
                                        {(application.resume_extraction.summary || application.resume_extraction.extracted_text)?.slice(0, 150)}
                                        {(application.resume_extraction.summary || application.resume_extraction.extracted_text)?.length > 150 ? '...' : ''}

                                        {application.resume_extraction.extracted_text?.length > 150 && (
                                            <Dialog>
                                                <DialogTrigger asChild>
                                                    <span className="text-primary cursor-pointer ml-2 font-medium hover:underline text-xs bg-primary/10 px-2 py-0.5 rounded-full border border-primary/20">
                                                        Read more
                                                    </span>
                                                </DialogTrigger>
                                                <DialogContent className="max-w-2xl bg-background/95 backdrop-blur-sm border-border shadow-xl">
                                                    <DialogHeader>
                                                        <DialogTitle className="text-xl font-bold text-primary flex items-center gap-2">
                                                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                                                            {application.resume_extraction.summary ? "Full Resume Text" : "Professional Summary"}
                                                        </DialogTitle>
                                                        <DialogDescription className="text-sm text-muted-foreground">
                                                            Detailed analysis of the candidate's profile based on their resume.
                                                        </DialogDescription>
                                                    </DialogHeader>
                                                    <div className="mt-4 text-foreground leading-relaxed text-base p-4 bg-muted/30 rounded-lg border border-border whitespace-pre-wrap max-h-[60vh] overflow-y-auto">
                                                        {application.resume_extraction.extracted_text}
                                                    </div>
                                                </DialogContent>
                                            </Dialog>
                                        )}
                                    </div>
                                </div>
                            </>
                        ) : (
                            <p className="text-secondary text-sm">Resume parsing pending or failed.</p>
                        )}
                        {application.resume_file_path ? (
                            <div className="pt-4">
                                <a
                                    href={`${API_BASE_URL}/uploads/${application.resume_file_path.replace(/\\/g, '/')}`}
                                    target="_blank"
                                    className="text-primary hover:underline text-sm font-medium flex items-center gap-2"
                                >
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
                                    Download Original Resume
                                </a>
                            </div>
                        ) : (
                            <div className="pt-4 flex items-center gap-2 text-secondary bg-secondary/10 p-3 rounded-md">
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
                                <span className="text-sm font-medium">No resume file found for this application.</span>
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Interview Results */}
                <Card className="animate-in fade-in slide-in-from-bottom-8 duration-700 ease-out fill-mode-both delay-200">
                    <CardHeader>
                        <CardTitle>AI Interview Results</CardTitle>
                    </CardHeader>
                    <CardContent>
                        {interviewReport ? (
                            <div className="space-y-4">
                                <div className="flex justify-between items-center bg-muted/50 p-3 rounded">
                                    <span className="font-medium">Overall Score</span>
                                    <span className="text-2xl font-bold text-primary">{interviewReport.overall_score.toFixed(1)}/10</span>
                                </div>

                                <div className="space-y-2 text-sm">
                                    <div className="flex justify-between">
                                        <span>Technical Skills</span>
                                        <span className="font-medium">{interviewReport.technical_skills_score}/10</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span>Communication</span>
                                        <span className="font-medium">{interviewReport.communication_score}/10</span>
                                    </div>
                                    {interviewReport.aptitude_score !== undefined && interviewReport.aptitude_score !== null && (
                                        <div className="flex justify-between">
                                            <span>Aptitude</span>
                                            <span className="font-medium">{interviewReport.aptitude_score}/10</span>
                                        </div>
                                    )}
                                    {interviewReport.behavioral_score !== undefined && interviewReport.behavioral_score !== null && (
                                        <div className="flex justify-between">
                                            <span>Behavioral</span>
                                            <span className="font-medium">{interviewReport.behavioral_score}/10</span>
                                        </div>
                                    )}
                                </div>

                                <div>
                                    <h4 className="font-semibold text-sm mb-1">Recommendation</h4>
                                    <div className={`text-sm font-bold uppercase ${interviewReport.recommendation.includes('hire') ? 'text-primary ' : 'text-secondary '
                                        }`}>
                                        {interviewReport.recommendation.replace(/_/g, ' ')}
                                    </div>
                                </div>

                                <div>
                                    <h4 className="font-semibold text-sm mb-1">AI Summary</h4>
                                    <p className="text-sm text-muted-foreground">{interviewReport.summary}</p>
                                </div>
                            </div>
                        ) : (
                            <div className="text-center py-8 text-muted-foreground">
                                {application.status === 'interview_completed'
                                    ? 'Generating report...'
                                    : 'Interview not yet completed'}
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* Overall Interview Video Recording */}
            {application.interview?.status === 'completed' && (
                <Card className="animate-in fade-in slide-in-from-bottom-8 duration-700 ease-out fill-mode-both delay-300">
                    <CardHeader>
                        <CardTitle className="text-xl flex items-center gap-2 text-primary">
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
                            Interview Video Recording
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        {interviewReport?.video_url ? (
                            <div className="bg-slate-900 rounded-2xl overflow-hidden shadow-2xl aspect-video relative group border-4 border-muted">
                                <video
                                    src={`${API_BASE_URL}/${interviewReport.video_url.replace(/\\/g, '/')}`}
                                    controls
                                    className="w-full h-full"
                                />
                                <div className="absolute top-4 left-4 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity">
                                    <div className="bg-black/60 backdrop-blur-md px-3 py-1.5 rounded-full border border-white/20 text-white text-xs font-bold flex items-center gap-2">
                                        <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></div>
                                        Verified Recording
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div className="bg-muted/30 border-2 border-dashed rounded-2xl p-12 flex flex-col items-center justify-center text-center">
                                <svg className="w-12 h-12 text-muted-foreground/30 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
                                <p className="text-sm font-semibold text-muted-foreground">Video Session Not Found</p>
                                <p className="text-xs text-muted-foreground/60 mt-1">This could be due to camera permissions being denied or the session starting before recording was enabled.</p>
                            </div>
                        )}
                    </CardContent>
                </Card>
            )}
        </div>
    )
}
