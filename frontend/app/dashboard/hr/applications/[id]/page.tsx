"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { APIClient } from "@/app/dashboard/lib/api-client"
import { API_BASE_URL } from "@/lib/config"
import { RejectDialog } from "@/components/reject-dialog"
import { ArrowLeft, FileText, CheckCircle2, XCircle, Clock, PhoneCall, Star, RotateCw, Eye, ChevronRight, Edit2, Save, X } from "lucide-react"
import { Textarea } from "@/components/ui/textarea"
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog"

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
    const [isEditingNotes, setIsEditingNotes] = useState(false)
    const [notesDraft, setNotesDraft] = useState("")
    const [isPhysicalInterviewPopupOpen, setIsPhysicalInterviewPopupOpen] = useState(false)

    const fetchApplication = async () => {
        try {
            const data = await APIClient.get<any>(`/api/applications/${applicationId}`)
            setApplication(data)
            setNotesDraft(data.hr_notes || "")
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

    const handleSaveNotes = async () => {
        setActionLoading('save_notes')
        try {
            await APIClient.put(`/api/applications/${applicationId}/notes`, {
                hr_notes: notesDraft
            })
            await fetchApplication()
            setIsEditingNotes(false)
        } catch (err: any) {
            alert(err.message || "Failed to save notes")
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

    const educationItems = (() => {
        try {
            const raw = resumeExtraction.education
            if (!raw) return []
            if (typeof raw === 'string') {
                const trimmed = raw.trim()
                if (trimmed.startsWith('[') && trimmed.endsWith(']')) {
                    return JSON.parse(trimmed)
                }
                return [raw]
            }
            if (Array.isArray(raw)) return raw
            return []
        } catch { return [] }
    })()

    // Extract interview report
    const report = application.interview?.report || null

    return (
        <div className=" space-y-6 max-w-7xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
            {/* ─── Candidate Info Card ───────────────────────────────── */}
            <Card className=" border shadow-md bg-gradient-to-br from-white to-slate-50 relative overflow-hidden">
                {/* Status Indicator - Top Right Anchor */}
                <div className="absolute top-4 right-4 z-10 md:top-6 md:right-6">
                    <Badge className={`px-4 py-1.5 text-xs font-bold uppercase border shadow-sm whitespace-nowrap ${statusInfo.color}`}>
                        {statusInfo.label}
                    </Badge>
                </div>

                <CardHeader className="pb-6">
                    {/* Integrated Navigation */}
                    <div className="mb-4">
                        <Button 
                            variant="ghost" 
                            onClick={() => router.back()} 
                            className="gap-2 text-muted-foreground hover:text-foreground h-auto p-0 flex items-center transition-colors hover:bg-transparent group"
                        >
                            <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-1" /> 
                            <span className="text-sm font-bold">Back to Applications</span>
                        </Button>
                    </div>

                    <div className="flex flex-col md:flex-row items-center md:items-start gap-6 relative pr-12 md:pr-0">
                        {application.candidate_photo_path ? (
                            <img
                                src={`${API_BASE_URL}/${application.candidate_photo_path.replace(/\\/g, '/')}`}
                                alt={application.candidate_name}
                                className="w-24 h-24 rounded-2xl object-cover border-4 border-white shadow-xl ring-1 ring-slate-200"
                            />
                        ) : (
                            <div className="w-24 h-24 rounded-2xl bg-primary/10 flex items-center justify-center border-2 border-primary/20 shadow-inner">
                                <span className="text-3xl font-bold text-primary">{application.candidate_name?.[0]}</span>
                            </div>
                        )}
                        <div className="text-center md:text-left space-y-1">
                            <CardTitle className="text-3xl font-extrabold tracking-tight text-slate-900">{application.candidate_name}</CardTitle>
                            <CardDescription className="text-lg font-medium text-slate-500">{application.candidate_email}</CardDescription>
                            <div className="flex items-center justify-center md:justify-start gap-2 mt-2">
                                <Badge variant="outline" className="bg-white text-slate-600 border-slate-200">
                                    Applied for: <span className="ml-1 font-bold text-slate-900">{application.job?.title || 'Unknown Position'}</span>
                                </Badge>
                                <Badge variant="outline" className="bg-white text-slate-600 border-slate-200 capitalize">
                                    {application.job?.location || 'Remote'}
                                </Badge>
                            </div>
                        </div>
                    </div>
                </CardHeader>
            </Card>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
                {/* ─── Main Content (Left) ─── */}
                <div className="lg:col-span-2 space-y-6">
                    
                    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                        {/* ─── AI Resume Analysis ─── */}
                        <Card className="border shadow-sm h-full flex flex-col">
                            <CardHeader className="">
                                <CardTitle className="text-lg flex items-center gap-2 font-bold text-slate-800">
                                    <FileText className="h-5 w-5 text-indigo-600" />
                                    AI Resume Analysis
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="pt-2 space-y-4 flex-grow">
                                {resumeExtraction.resume_score != null ? (
                                    <>
                                        <div className="space-y-3">
                                            <div className="grid grid-cols-3 gap-3">
                                                <div className="text-center p-3 bg-indigo-50/50 rounded-xl border border-indigo-100">
                                                    <p className="text-2xl font-black text-indigo-700">{(resumeExtraction.resume_score * 10).toFixed(1)}</p>
                                                    <p className="text-[10px] uppercase font-bold text-indigo-500 tracking-wider">Score</p>
                                                </div>
                                                <div className="text-center p-3 bg-emerald-50/50 rounded-xl border border-emerald-100">
                                                    <p className="text-2xl font-black text-emerald-700">{resumeExtraction.skill_match_percentage?.toFixed(0) || '0'}%</p>
                                                    <p className="text-[10px] uppercase font-bold text-emerald-500 tracking-wider">Skill Match</p>
                                                </div>
                                                <div className="text-center p-3 bg-slate-50 rounded-xl border border-slate-100">
                                                    <p className="text-lg font-bold text-slate-700 truncate">{resumeExtraction.years_of_experience || resumeExtraction.experience_years || '0'} years</p>
                                                    <p className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Experience</p>
                                                </div>
                                            </div>
                                            <div className="w-full p-4 bg-slate-50 rounded-xl border border-slate-100 min-h-[4.5rem] flex flex-col justify-center">
                                                {educationItems.length > 0 ? (
                                                    <ul className="text-sm font-bold text-slate-700 space-y-1 text-left">
                                                        {educationItems.map((item: string, i: number) => (
                                                            <li key={i} className="flex gap-2">
                                                                <span className="text-indigo-500 font-bold">•</span>
                                                                <span>{item}</span>
                                                            </li>
                                                        ))}
                                                    </ul>
                                                ) : (
                                                    <p className="text-sm font-bold text-slate-700 text-center">N/A</p>
                                                )}
                                                <p className="text-[10px] uppercase font-bold text-slate-500 tracking-wider mt-2 text-center">Education</p>
                                            </div>
                                        </div>

                                        {skills.length > 0 && (
                                            <div>
                                                <h4 className="font-bold text-xs mb-2 text-slate-500 uppercase tracking-widest">Detected Skills</h4>
                                                <div className="flex flex-wrap gap-1.5">
                                                    {skills.slice(0, 8).map((skill: string, i: number) => (
                                                        <Badge key={i} variant="secondary" className="text-[10px] font-semibold bg-slate-100 text-slate-700 hover:bg-slate-200 border-none px-2 py-0.5">
                                                            {skill}
                                                        </Badge>
                                                    ))}
                                                    {skills.length > 8 && <span className="text-[10px] text-slate-400 font-bold">+{skills.length - 8} more</span>}
                                                </div>
                                            </div>
                                        )}

                                        {resumeExtraction.summary && (
                                            <div className="space-y-3">
                                                <div className="flex items-center justify-between">
                                                    <h4 className="font-bold text-xs text-slate-500 uppercase tracking-widest">AI Summary</h4>
                                                    
                                                    <Dialog>
                                                        <DialogTrigger asChild>
                                                            <Button variant="link" size="sm" className="h-auto p-0 text-indigo-600 font-bold text-xs hover:no-underline flex items-center gap-1 group">
                                                                View More <ChevronRight className="h-3 w-3 transition-transform group-hover:translate-x-0.5" />
                                                            </Button>
                                                        </DialogTrigger>
                                                        <DialogContent className="max-w-4xl! max-h-[90vh] overflow-y-auto w-[95vw]">
                                                            <DialogHeader>
                                                                <DialogTitle className="flex items-center gap-2 text-xl font-bold">
                                                                    <FileText className="h-5 w-5 text-indigo-600" />
                                                                    AI Analysis Details
                                                                </DialogTitle>
                                                            </DialogHeader>
                                                            
                                                            <div className="space-y-6 py-4">

                                                                {/* Optimized Metrics Grid */}
                                                                <div className="space-y-3">
                                                                    <div className="grid grid-cols-3 gap-3">
                                                                        <div className="text-center p-4 bg-indigo-50 rounded-xl border border-indigo-100">
                                                                            <p className="text-2xl font-black text-indigo-700">{(resumeExtraction.resume_score * 10).toFixed(1)}</p>
                                                                            <p className="text-[10px] uppercase font-bold text-indigo-500 tracking-wider">Score</p>
                                                                        </div>
                                                                        <div className="text-center p-4 bg-emerald-50 rounded-xl border border-emerald-100">
                                                                            <p className="text-2xl font-black text-emerald-700">{resumeExtraction.skill_match_percentage?.toFixed(0) || '0'}%</p>
                                                                            <p className="text-[10px] uppercase font-bold text-emerald-500 tracking-wider">Skill Match</p>
                                                                        </div>
                                                                        <div className="text-center p-4 bg-slate-50 rounded-xl border border-slate-100">
                                                                            <p className="text-xl font-bold text-slate-700 truncate">{resumeExtraction.years_of_experience || resumeExtraction.experience_years || '0'}y</p>
                                                                            <p className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Experience</p>
                                                                        </div>
                                                                    </div>
                                                                    <div className="w-full p-4 bg-slate-50 rounded-xl border border-slate-100 flex flex-col justify-center">
                                                                        <p className="text-[10px] uppercase font-bold text-slate-500 tracking-wider mt-2 text-center">Education</p>
                                                                        {educationItems.length > 0 ? (
                                                                            <ul className="text-base font-bold text-slate-700 space-y-1 text-left">
                                                                                {educationItems.map((item: string, i: number) => (
                                                                                    <li key={i} className="flex gap-2">
                                                                                        <span className="text-indigo-500 font-bold">•</span>
                                                                                        <span>{item}</span>
                                                                                    </li>
                                                                                ))}
                                                                            </ul>
                                                                        ) : (
                                                                            <p className="text-base font-bold text-slate-700 text-center">N/A</p>
                                                                        )}
                                                                    </div>
                                                                </div>


                                                                {/* Summary Sections */}
                                                                <div className="space-y-4">
                                                                    {(() => {
                                                                        const summary = resumeExtraction.summary || "";
                                                                        const sections = summary.split(/\*\*Key Highlights:\*\*|\*\*Potential Gaps:\*\*/);
                                                                        const mainSummary = sections[0]?.trim();
                                                                        const highlights = summary.match(/\*\*Key Highlights:\*\*\n([\s\S]*?)(?=\n\n\*\*Potential Gaps:\*\*|$)/)?.[1]?.trim();
                                                                        const gaps = summary.match(/\*\*Potential Gaps:\*\*\n([\s\S]*?)$/)?.[1]?.trim();

                                                                        return (
                                                                            <>
                                                                                {mainSummary && (
                                                                                    <div className="bg-slate-50 p-5 rounded-xl border border-slate-100 shadow-sm">
                                                                                        <h5 className="text-[10px] font-black uppercase text-slate-400 tracking-wider mb-2">Professional Summary</h5>
                                                                                        <p className="text-sm text-slate-700 leading-relaxed font-medium">{mainSummary}</p>
                                                                                    </div>
                                                                                )}
                                                                                
                                                                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                                                                    <div className="bg-emerald-50/50 p-4 rounded-xl border border-emerald-100/50">
                                                                                        <h5 className="text-[10px] font-black uppercase text-emerald-600 tracking-wider mb-2">Core Strengths</h5>
                                                                                        {highlights ? (
                                                                                            <div className="text-sm text-slate-700 space-y-1.5">
                                                                                                {highlights.split('\n').map((line: string, i: number) => (
                                                                                                    <p key={i} className="flex gap-2">
                                                                                                        <span className="text-emerald-500 font-bold">•</span> {line.replace(/^- /, '')}
                                                                                                    </p>
                                                                                                ))}
                                                                                            </div>
                                                                                        ) : <p className="text-sm text-slate-400 italic">No highlights identified.</p>}
                                                                                    </div>
                                                                                    
                                                                                    <div className="bg-amber-50/50 p-4 rounded-xl border border-amber-100/50">
                                                                                        <h5 className="text-[10px] font-black uppercase text-amber-600 tracking-wider mb-2">Potential Gaps</h5>
                                                                                        {gaps ? (
                                                                                            <div className="text-sm text-slate-700 space-y-1.5">
                                                                                                {gaps.split('\n').map((line: string, i: number) => (
                                                                                                    <p key={i} className="flex gap-2">
                                                                                                        <span className="text-amber-500 font-bold">•</span> {line.replace(/^- /, '')}
                                                                                                    </p>
                                                                                                ))}
                                                                                            </div>
                                                                                        ) : <p className="text-sm text-slate-400 italic">No significant gaps found.</p>}
                                                                                    </div>
                                                                                </div>
                                                                            </>
                                                                        );
                                                                    })()}
                                                                </div>

                                                                {/* Full Skills list */}
                                                                {skills.length > 0 && (
                                                                    <div className="bg-slate-50/50 p-4 rounded-xl border border-slate-100">
                                                                        <h5 className="text-[10px] font-black uppercase text-slate-400 tracking-wider mb-3">Extracted Skills</h5>
                                                                        <div className="flex flex-wrap gap-1.5">
                                                                            {skills.map((skill: string, i: number) => (
                                                                                <Badge key={i} variant="secondary" className="text-[10px] font-semibold bg-white text-slate-600 border border-slate-200">
                                                                                    {skill}
                                                                                </Badge>
                                                                            ))}
                                                                        </div>
                                                                    </div>
                                                                )}
                                                            </div>
                                                        </DialogContent>
                                                    </Dialog>
                                                </div>
                                                <p className="text-sm text-slate-600 leading-relaxed font-medium italic line-clamp-4">
                                                    "{resumeExtraction.summary.split('\n\n**Key Highlights:**')[0]}"
                                                </p>
                                            </div>
                                        )}
                                    </>
                                ) : (
                                    <div className="text-center py-10 space-y-4">
                                        <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto">
                                            <RotateCw className={`h-8 w-8 text-slate-300 ${actionLoading === 'retry' ? 'animate-spin' : ''}`} />
                                        </div>
                                        <div className="space-y-2">
                                            <p className="text-slate-500 font-medium">
                                                {application.resume_score === null || application.resume_score === undefined
                                                    ? "Analysis in progress..."
                                                    : "No detailed analysis available."}
                                            </p>
                                            <Button 
                                                variant="outline" 
                                                size="sm" 
                                                onClick={handleRetryAnalysis}
                                                disabled={actionLoading === 'retry'}
                                                className="rounded-full px-6 border-indigo-200 text-indigo-600 hover:bg-indigo-50"
                                            >
                                                Retry Analysis
                                            </Button>
                                        </div>
                                    </div>
                                )}
                            </CardContent>
                        </Card>

                        {/* ─── Interview Report ─── */}
                        <Card className="border shadow-sm h-full flex flex-col">
                            <CardHeader className="">
                                <CardTitle className="text-lg flex items-center gap-2 font-bold text-slate-800">
                                    <Star className="h-5 w-5 text-amber-500" />
                                    Interview Report
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="pt-2 space-y-6 flex-grow flex flex-col">
                                {report ? (
                                    <div className="space-y-6 flex-grow">
                                        <div className="grid grid-cols-2 gap-3">
                                            <div className="text-center p-3 bg-orange-50/50 rounded-xl border border-orange-100">
                                                <p className="text-2xl font-black text-black">{report.overall_score?.toFixed(1) || '0.0'}</p>
                                                <p className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Overall</p>
                                            </div>
                                            <div className="text-center p-3 bg-purple-50/50 rounded-xl border border-purple-100">
                                                <p className="text-2xl font-black text-purple-700">{report.aptitude_score?.toFixed(1) || '0.0'}</p>
                                                <p className="text-[10px] uppercase font-bold text-purple-500 tracking-wider">Aptitude</p>
                                            </div>
                                            <div className="text-center p-3 bg-blue-50/50 rounded-xl border border-blue-100">
                                                <p className="text-2xl font-black text-blue-700">{report.technical_skills_score?.toFixed(1) || '0.0'}</p>
                                                <p className="text-[10px] uppercase font-bold text-blue-500 tracking-wider">Technical</p>
                                            </div>
                                            <div className="text-center p-3 bg-emerald-50/50 rounded-xl border border-emerald-100">
                                                <p className="text-2xl font-black text-emerald-700">{report.communication_score?.toFixed(1) || '0.0'}</p>
                                                <p className="text-[10px] uppercase font-bold text-emerald-500 tracking-wider">Communication</p>
                                            </div>
                                        </div>

                                        {report.recommendation && (
                                            <div className="p-4 bg-slate-50 rounded-xl border border-slate-100">
                                                <h4 className="font-bold text-xs mb-2 text-slate-500 uppercase tracking-widest text-center">Recommendation</h4>
                                                <div className="flex justify-center">
                                                    <Badge
                                                        className={`${
                                                            report.recommendation === 'strong_hire' ? 'bg-emerald-500 text-white' :
                                                            report.recommendation === 'hire' || report.recommendation === 'recommended' ? 'bg-green-500 text-white' :
                                                            report.recommendation === 'consider' ? 'bg-amber-500 text-white' :
                                                            'bg-red-500 text-white'
                                                        } px-6 py-1.5 text-xs font-black uppercase tracking-widest border-none shadow-sm`}
                                                    >
                                                        {report.recommendation.replace('_', ' ')}
                                                    </Badge>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                ) : (
                                    <div className="flex flex-col items-center justify-center py-12 text-center space-y-3 flex-grow">
                                        <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center">
                                            <Clock className="h-8 w-8 text-slate-300" />
                                        </div>
                                        <p className="text-slate-500 font-medium">Interview report will be<br/>available after completion.</p>
                                    </div>
                                )}

                                {report && (
                                    <div className="mt-auto pt-4">
                                        <Button
                                            variant="default"
                                            className="w-full h-11 font-bold shadow-md bg-slate-800 hover:bg-slate-900 rounded-xl group"
                                            onClick={() => {
                                                router.push(`/dashboard/hr/reports?search=${encodeURIComponent(application.candidate_name)}&reportId=${report.id}`)
                                            }}
                                        >
                                            View Detailed Report
                                            <Eye className="ml-2 h-4 w-4 transition-transform group-hover:scale-110" />
                                        </Button>
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    </div>


                </div>

                {/* ─── Sidebar (Right) ─── */}
                <div className="space-y-6">
                    {/* ─── Actions Card ─── */}
                    {!isTerminal && buttons.length > 0 && (
                        <Card className="border shadow-lg bg-white overflow-hidden ring-1 ring-primary/5">
                            <div className="h-1.5 bg-primary w-full" />
                            <CardHeader>
                                <CardTitle className="text-lg font-bold">Pipeline Actions</CardTitle>
                                <CardDescription>Advance the candidate to the next stage.</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-3">
                                {buttons.map((btn, idx) => {
                                    if (btn.action === 'reject') {
                                        return (
                                            <RejectDialog
                                                key={idx}
                                                candidateName={application.candidate_name || 'Candidate'}
                                                onConfirm={handleReject}
                                                trigger={
                                                    <Button
                                                        variant="ghost"
                                                        className="w-full h-12 justify-start gap-3 font-bold text-red-600 hover:bg-red-50 hover:text-red-700 border border-transparent hover:border-red-100 rounded-xl"
                                                        disabled={actionLoading !== null}
                                                    >
                                                        <XCircle className="h-5 w-5" />
                                                        {actionLoading === 'reject' ? 'Rejecting...' : 'Reject Candidate'}
                                                    </Button>
                                                }
                                            />
                                        )
                                    }
                                    return (
                                        <Button
                                            key={idx}
                                            className={`w-full h-12 justify-start gap-3 rounded-xl transition-all active:scale-[0.98] ${btn.className}`}
                                            disabled={actionLoading !== null}
                                            onClick={() => handleTransition(btn.action)}
                                        >
                                            {btn.icon}
                                            <span className="font-bold uppercase tracking-wider text-xs">
                                                {actionLoading === btn.action ? 'Processing...' : btn.label}
                                            </span>
                                        </Button>
                                    )
                                })}

                                {currentStatus === 'physical_interview' && (
                                    <Dialog open={isPhysicalInterviewPopupOpen} onOpenChange={setIsPhysicalInterviewPopupOpen}>
                                        <DialogTrigger asChild>
                                            <Button
                                                variant="outline"
                                                className="w-full h-12 justify-start gap-3 rounded-xl border-2 border-primary/20 text-primary hover:bg-primary/5 font-bold"
                                            >
                                                <Edit2 className="h-5 w-5" />
                                                <span className="uppercase tracking-wider text-xs">Completed Physical Interview</span>
                                            </Button>
                                        </DialogTrigger>
                                        <DialogContent>
                                            <DialogHeader>
                                                <DialogTitle>Physical Interview Result</DialogTitle>
                                            </DialogHeader>
                                            <div className="space-y-4 py-4">
                                                <p className="text-sm text-muted-foreground italic font-medium">Add remarks to the candidate based on the physical interview.</p>
                                                <Textarea 
                                                    placeholder="Enter interview feedback, observations..."
                                                    className="min-h-[150px] rounded-xl"
                                                    value={notesDraft}
                                                    onChange={(e) => setNotesDraft(e.target.value)}
                                                />
                                                <div className="flex justify-end gap-2">
                                                    <Button variant="ghost" onClick={() => setIsPhysicalInterviewPopupOpen(false)}>Cancel</Button>
                                                    <Button 
                                                        className="rounded-full px-8 bg-primary hover:bg-primary/90 font-bold"
                                                        onClick={() => {
                                                            handleSaveNotes();
                                                            setIsPhysicalInterviewPopupOpen(false);
                                                        }}
                                                    >
                                                        Save Remarks
                                                    </Button>
                                                </div>
                                            </div>
                                        </DialogContent>
                                    </Dialog>
                                )}
                            </CardContent>
                        </Card>
                    )}

                    {/* ─── HR Notes ─── */}
                    <Card className="border shadow-sm overflow-hidden">
                        <div className="h-1 bg-amber-400 w-full" />
                        <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                            <CardTitle className="text-sm font-bold uppercase tracking-widest text-slate-500">Processing Notes / Observations</CardTitle>
                            {!isEditingNotes && (
                                <Button 
                                    variant="ghost" 
                                    size="sm" 
                                    className="h-8 w-8 p-0" 
                                    onClick={() => setIsEditingNotes(true)}
                                >
                                    <Edit2 className="h-4 w-4 text-slate-400" />
                                </Button>
                            )}
                        </CardHeader>
                        <CardContent>
                            {isEditingNotes ? (
                                <div className="space-y-3">
                                    <Textarea
                                        value={notesDraft}
                                        onChange={(e) => setNotesDraft(e.target.value)}
                                        placeholder="Add internal notes about this candidate..."
                                        className="min-h-[120px] bg-amber-50/10 border-amber-200/50 rounded-xl"
                                    />
                                    <div className="flex justify-end gap-2">
                                        <Button 
                                            size="sm" 
                                            variant="ghost" 
                                            onClick={() => {
                                                setIsEditingNotes(false)
                                                setNotesDraft(application.hr_notes || "")
                                            }}
                                            className="h-8 text-xs font-bold"
                                        >
                                            <X className="h-3 w-3 mr-1" /> Cancel
                                        </Button>
                                        <Button 
                                            size="sm" 
                                            onClick={handleSaveNotes}
                                            disabled={actionLoading === 'save_notes'}
                                            className="h-8 text-xs font-bold bg-amber-500 hover:bg-amber-600 text-white"
                                        >
                                            {actionLoading === 'save_notes' ? <RotateCw className="h-3 w-3 animate-spin mr-1" /> : <Save className="h-3 w-3 mr-1" />}
                                            Save Note
                                        </Button>
                                    </div>
                                </div>
                            ) : (
                                <div className="p-4 bg-amber-50/30 rounded-lg border border-amber-100/50 min-h-[60px] flex flex-col justify-center">
                                    {application.hr_notes ? (
                                        <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">{application.hr_notes}</p>
                                    ) : (
                                        <p className="text-sm text-slate-400 italic">No notes added yet. Click edit to add observations.</p>
                                    )}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                    
                    {/* ─── Terminal State Banner ─── */}
                    {isTerminal && (
                        <Card className={`border-2 shadow-sm ${currentStatus === 'hired' ? 'bg-emerald-50 border-emerald-200' : 'bg-red-50 border-red-200'}`}>
                            <CardContent className="py-8 text-center space-y-2">
                                <p className={`text-2xl font-black tracking-tight ${currentStatus === 'hired' ? 'text-emerald-700' : 'text-red-700'}`}>
                                    {currentStatus === 'hired' ? '🎉 CANDIDATE HIRED' : '❌ APPLICATION REJECTED'}
                                </p>
                                <p className="text-slate-500 font-medium">This application is closed and no further actions are available.</p>
                            </CardContent>
                        </Card>
                    )}

                </div>
            </div>
        </div>
    )
}
