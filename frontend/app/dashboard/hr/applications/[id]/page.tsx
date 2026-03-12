"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { APIClient } from "@/app/dashboard/lib/api-client"
import { API_BASE_URL } from "@/lib/config"
import { RejectDialog } from "@/components/reject-dialog"
import { ArrowLeft, FileText, CheckCircle2, XCircle, Clock, PhoneCall, Star, RotateCw, Eye } from "lucide-react"

// ─── FSM Button Config ──────────────────────────────────────────────────
const FSM_BUTTONS: Record<string, { action: string; label: string; icon: React.ReactNode; className: string }[]> = {
    applied: [
        { action: "approve_for_interview", label: "APPROVE FOR INTERVIEW", icon: <CheckCircle2 className="h-4 w-4" />, className: "bg-primary hover:bg-primary/90 text-primary-foreground shadow-lg" },
        { action: "reject", label: "REJECT CANDIDATE", icon: <XCircle className="h-4 w-4" />, className: "bg-destructive hover:bg-destructive/90 text-white shadow-lg" },
    ],
    aptitude_round: [
        { action: "reject", label: "REJECT CANDIDATE", icon: <XCircle className="h-4 w-4" />, className: "bg-destructive hover:bg-destructive/90 text-white shadow-lg" },
    ],
    ai_interview: [
        { action: "reject", label: "REJECT CANDIDATE", icon: <XCircle className="h-4 w-4" />, className: "bg-destructive hover:bg-destructive/90 text-white shadow-lg" },
    ],
    ai_interview_completed: [
        { action: "call_for_interview", label: "CALL FOR INTERVIEW", icon: <PhoneCall className="h-4 w-4" />, className: "bg-primary hover:bg-primary/90 text-primary-foreground shadow-lg" },
        { action: "review_later", label: "REVIEW LATER", icon: <Clock className="h-4 w-4" />, className: "bg-amber-500 hover:bg-amber-600 text-white shadow-lg" },
        { action: "reject", label: "REJECT CANDIDATE", icon: <XCircle className="h-4 w-4" />, className: "bg-destructive hover:bg-destructive/90 text-white shadow-lg" },
    ],
    review_later: [
        { action: "call_for_interview", label: "CALL FOR INTERVIEW", icon: <PhoneCall className="h-4 w-4" />, className: "bg-primary hover:bg-primary/90 text-primary-foreground shadow-lg" },
        { action: "reject", label: "REJECT CANDIDATE", icon: <XCircle className="h-4 w-4" />, className: "bg-destructive hover:bg-destructive/90 text-white shadow-lg" },
    ],
    physical_interview: [
        { action: "hire", label: "HIRE CANDIDATE", icon: <Star className="h-4 w-4" />, className: "bg-emerald-600 hover:bg-emerald-700 text-white shadow-lg" },
        { action: "reject", label: "REJECT CANDIDATE", icon: <XCircle className="h-4 w-4" />, className: "bg-destructive hover:bg-destructive/90 text-white shadow-lg" },
    ],
    // hired and rejected: no buttons (terminal states)
}

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
    applied: { label: "Applied", color: "bg-blue-100 text-blue-700 border-blue-200" },
    aptitude_round: { label: "Aptitude Round", color: "bg-purple-100 text-purple-700 border-purple-200" },
    ai_interview: { label: "AI Interview", color: "bg-indigo-100 text-indigo-700 border-indigo-200" },
    ai_interview_completed: { label: "AI Interview Completed", color: "bg-cyan-100 text-cyan-700 border-cyan-200" },
    review_later: { label: "Review Later", color: "bg-amber-100 text-amber-700 border-amber-200" },
    physical_interview: { label: "Physical Interview", color: "bg-teal-100 text-teal-700 border-teal-200" },
    hired: { label: "Hired", color: "bg-emerald-100 text-emerald-700 border-emerald-200" },
    rejected: { label: "Rejected", color: "bg-red-100 text-red-700 border-red-200" },
}

export default function HRApplicationDetailPage() {
    const params = useParams()
    const router = useRouter()
    const applicationId = params.id
    const [application, setApplication] = useState<any>(null)
    const [loading, setLoading] = useState(true)
    const [actionLoading, setActionLoading] = useState<string | null>(null)
    const [error, setError] = useState<string | null>(null)

    const fetchApplication = async () => {
        try {
            const data = await APIClient.get<any>(`/api/applications/${applicationId}`)
            setApplication(data)
            setError(null)
        } catch (err: any) {
            setError(err.message || "Failed to load application")
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        if (applicationId) {
            fetchApplication()
        }
    }, [applicationId])

    // ─── FSM Transition Handler ────────────────────────────────────────
    const handleTransition = async (action: string, notes?: string) => {
        setActionLoading(action)
        try {
            await APIClient.put(`/api/applications/${applicationId}/status`, {
                action,
                hr_notes: notes || `HR action: ${action}`,
            })
            await fetchApplication()
        } catch (err: any) {
            alert(err.message || `Failed to execute: ${action}`)
        } finally {
            setActionLoading(null)
        }
    }

    const handleReject = async (reason: string, notes: string) => {
        await handleTransition('reject', `Reason: ${reason}${notes ? `\nNotes: ${notes}` : ''}`)
    }

    const handleRetryAnalysis = async () => {
        setActionLoading('retry')
        try {
            await APIClient.post(`/api/applications/${applicationId}/retry-analysis`, {})
            await fetchApplication()
        } catch (err: any) {
            alert(err.message || "Failed to retry analysis")
        } finally {
            setActionLoading(null)
        }
    }

    if (loading) {
        return <div className="flex justify-center items-center h-screen">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
    }

    if (error || !application) {
        return (
            <div className="p-6">
                <Button variant="ghost" onClick={() => router.back()} className="mb-4">
                    <ArrowLeft className="h-4 w-4 mr-2" /> Back
                </Button>
                <Card className="p-6 bg-destructive/10 border-destructive/20">
                    <p className="text-destructive font-bold">{error || "Application not found"}</p>
                </Card>
            </div>
        )
    }

    const currentStatus = application.status || 'applied'
    const statusInfo = STATUS_LABELS[currentStatus] || { label: currentStatus, color: "bg-gray-100 text-gray-700 border-gray-200" }
    const buttons = FSM_BUTTONS[currentStatus] || []
    const isTerminal = ['hired', 'rejected'].includes(currentStatus)

    // Extract resume data
    const resumeExtraction = application.resume_extraction || {}
    const skills = (() => {
        try {
            const raw = resumeExtraction.skills
            if (typeof raw === 'string') return JSON.parse(raw)
            if (Array.isArray(raw)) return raw
            return []
        } catch { return [] }
    })()

    // Extract interview report
    const report = application.interview?.report || null

    return (
        <div className="p-6 space-y-6 max-w-5xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
            {/* ─── Header ────────────────────────────────────────────── */}
            <div className="flex items-center justify-between">
                <Button variant="ghost" onClick={() => router.back()} className="gap-2 text-muted-foreground hover:text-foreground">
                    <ArrowLeft className="h-4 w-4" /> Back to Applications
                </Button>
                <Badge className={`px-3 py-1.5 text-xs font-bold uppercase border ${statusInfo.color}`}>
                    {statusInfo.label}
                </Badge>
            </div>

            {/* ─── Candidate Info ─────────────────────────────────────── */}
            <Card className="border shadow-sm">
                <CardHeader>
                    <div className="flex items-start gap-4">
                        {application.candidate_photo_path && (
                            <img
                                src={`${API_BASE_URL}/${application.candidate_photo_path.replace(/\\/g, '/')}`}
                                alt={application.candidate_name}
                                className="w-20 h-20 rounded-full object-cover border-2 border-primary/20 shadow-md"
                            />
                        )}
                        <div>
                            <CardTitle className="text-2xl font-bold">{application.candidate_name}</CardTitle>
                            <CardDescription className="text-base mt-1">{application.candidate_email}</CardDescription>
                            <p className="text-sm text-muted-foreground mt-1">
                                Applied for: <strong>{application.job?.title || 'Unknown Position'}</strong>
                            </p>
                        </div>
                    </div>
                </CardHeader>
            </Card>

            {/* ─── FSM Action Buttons ────────────────────────────────── */}
            {!isTerminal && buttons.length > 0 && (
                <Card className="border shadow-sm bg-muted/30">
                    <CardHeader>
                        <CardTitle className="text-lg">Actions</CardTitle>
                        <CardDescription className="text-sm">
                            Available actions for current state: <strong>{statusInfo.label}</strong>
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="flex flex-wrap gap-3">
                            {buttons.map(btn => {
                                if (btn.action === 'reject') {
                                    return (
                                        <RejectDialog
                                            key={btn.action}
                                            candidateName={application.candidate_name || 'Candidate'}
                                            onConfirm={handleReject}
                                            trigger={
                                                <Button
                                                    className={`gap-2 font-bold ${btn.className}`}
                                                    disabled={actionLoading !== null}
                                                >
                                                    {btn.icon}
                                                    {actionLoading === btn.action ? 'Processing...' : btn.label}
                                                </Button>
                                            }
                                        />
                                    )
                                }
                                return (
                                    <Button
                                        key={btn.action}
                                        className={`gap-2 font-bold ${btn.className}`}
                                        disabled={actionLoading !== null}
                                        onClick={() => handleTransition(btn.action)}
                                    >
                                        {btn.icon}
                                        {actionLoading === btn.action ? 'Processing...' : btn.label}
                                    </Button>
                                )
                            })}
                        </div>
                    </CardContent>
                </Card>
            )}
            {/* ─── AI Resume Analysis ────────────────────────────────── */}
            <Card className="border shadow-sm">
                <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                        <FileText className="h-5 w-5 text-primary" />
                        AI Resume Analysis
                    </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    {resumeExtraction.resume_score != null ? (
                        <>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                <div className="text-center p-3 bg-muted rounded-lg">
                                    <p className="text-2xl font-bold text-primary">{(resumeExtraction.resume_score * 10).toFixed(1)}</p>
                                    <p className="text-xs text-muted-foreground">Resume Score</p>
                                </div>
                                <div className="text-center p-3 bg-muted rounded-lg">
                                    <p className="text-2xl font-bold text-primary">{resumeExtraction.skill_match_percentage?.toFixed(1) || 'N/A'}%</p>
                                    <p className="text-xs text-muted-foreground">Skill Match</p>
                                </div>
                                <div className="text-center p-3 bg-muted rounded-lg">
                                    <p className="text-2xl font-bold text-primary">{resumeExtraction.experience_years || 'N/A'}</p>
                                    <p className="text-xs text-muted-foreground">Experience (Years)</p>
                                </div>
                                <div className="text-center p-3 bg-muted rounded-lg">
                                    <p className="text-2xl font-bold text-primary">{resumeExtraction.education || 'N/A'}</p>
                                    <p className="text-xs text-muted-foreground">Education</p>
                                </div>
                            </div>

                            {skills.length > 0 && (
                                <div>
                                    <h4 className="font-semibold text-sm mb-2 text-muted-foreground">Detected Skills</h4>
                                    <div className="flex flex-wrap gap-1.5">
                                        {skills.map((skill: string, i: number) => (
                                            <Badge key={i} variant="secondary" className="text-xs px-2 py-0.5">{skill}</Badge>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {resumeExtraction.summary && (
                                <div>
                                    <h4 className="font-semibold text-sm mb-1 text-muted-foreground">AI Summary</h4>
                                    <p className="text-sm text-foreground/80 leading-relaxed">{resumeExtraction.summary}</p>
                                </div>
                            )}
                        </>
                    ) : (
                        <div className="text-center py-8 space-y-3">
                            <p className="text-muted-foreground">
                                {application.resume_score === null || application.resume_score === undefined
                                    ? "Analysis in progress or not yet started..."
                                    : "Analysis completed. No detailed extraction available."}
                            </p>
                            <Button 
                                variant="outline" 
                                size="sm" 
                                onClick={handleRetryAnalysis}
                                disabled={actionLoading === 'retry'}
                                className="gap-2"
                            >
                                <RotateCw className={`h-4 w-4 ${actionLoading === 'retry' ? 'animate-spin' : ''}`} />
                                Retry AI Analysis
                            </Button>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* ─── Interview Report (Compact Summary + View Full Report) ── */}
            <Card className="border shadow-sm">
                <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                        <Eye className="h-5 w-5 text-primary" />
                        Interview Report
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    {report ? (
                        <div className="space-y-4">
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                <div className="text-center p-3 bg-muted rounded-lg">
                                    <p className="text-2xl font-bold text-primary">{report.overall_score?.toFixed(1) || 'N/A'}</p>
                                    <p className="text-xs text-muted-foreground">Overall Score</p>
                                </div>
                                <div className="text-center p-3 bg-muted rounded-lg">
                                    <p className="text-2xl font-bold text-purple-600">{report.aptitude_score?.toFixed(1) || 'N/A'}</p>
                                    <p className="text-xs text-muted-foreground">Aptitude</p>
                                </div>
                                <div className="text-center p-3 bg-muted rounded-lg">
                                    <p className="text-2xl font-bold text-blue-600">{report.technical_skills_score?.toFixed(1) || 'N/A'}</p>
                                    <p className="text-xs text-muted-foreground">Technical</p>
                                </div>
                                <div className="text-center p-3 bg-muted rounded-lg">
                                    <p className="text-2xl font-bold text-green-600">{report.communication_score?.toFixed(1) || 'N/A'}</p>
                                    <p className="text-xs text-muted-foreground">Communication</p>
                                </div>
                            </div>

                            {report.recommendation && (
                                <div className="flex items-center gap-2">
                                    <span className="text-sm text-muted-foreground font-medium">Recommendation:</span>
                                    <Badge
                                        className={`${
                                            report.recommendation === 'strong_hire' ? 'bg-emerald-100 text-emerald-700 border-emerald-200' :
                                            report.recommendation === 'hire' || report.recommendation === 'recommended' ? 'bg-green-100 text-green-700 border-green-200' :
                                            report.recommendation === 'consider' ? 'bg-amber-100 text-amber-700 border-amber-200' :
                                            'bg-red-100 text-red-700 border-red-200'
                                        } border px-3 py-1 text-xs font-bold uppercase`}
                                    >
                                        {report.recommendation.replace('_', ' ')}
                                    </Badge>
                                </div>
                            )}

                            <Button
                                variant="outline"
                                className="w-full gap-2 font-semibold border-primary/30 text-primary hover:bg-primary/5"
                                onClick={() => {
                                    // Navigate to reports page with search params to focus on this report
                                    router.push(`/dashboard/hr/reports?search=${encodeURIComponent(application.candidate_name)}`);
                                }}
                            >
                                <FileText className="h-4 w-4" />
                                View Full Report
                            </Button>
                        </div>
                    ) : (
                        <p className="text-muted-foreground text-center py-6">No interview report available yet.</p>
                    )}
                </CardContent>
            </Card>

            {/* ─── HR Notes ──────────────────────────────────────────── */}
            {application.hr_notes && (
                <Card className="border shadow-sm">
                    <CardHeader>
                        <CardTitle className="text-lg">HR Notes</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <p className="text-sm text-foreground/80 whitespace-pre-wrap">{application.hr_notes}</p>
                    </CardContent>
                </Card>
            )}


            {/* ─── Terminal State Banner ─────────────────────────────── */}
            {isTerminal && (
                <Card className={`border shadow-sm ${currentStatus === 'hired' ? 'bg-emerald-50 border-emerald-200' : 'bg-red-50 border-red-200'}`}>
                    <CardContent className="py-6 text-center">
                        <p className={`text-lg font-bold ${currentStatus === 'hired' ? 'text-emerald-700' : 'text-red-700'}`}>
                            {currentStatus === 'hired' ? '🎉 This candidate has been hired!' : '❌ This candidate has been rejected.'}
                        </p>
                        {application.hr_notes && (
                            <p className="text-sm text-muted-foreground mt-2">{application.hr_notes}</p>
                        )}
                    </CardContent>
                </Card>
            )}
        </div>
    )
}
