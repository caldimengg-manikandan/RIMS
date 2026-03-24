'use client'

import React, { useEffect, useState, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { ArrowLeft, Briefcase, MapPin, Clock, UploadCloud, CheckCircle2, Loader2, AlertCircle, Edit2, XCircle, Trash2 } from 'lucide-react'
import { ToggleTheme } from '@/components/lightswind/toggle-theme'
import { useAuth } from '@/app/dashboard/lib/auth-context'
import { APIClient } from '@/app/dashboard/lib/api-client'
import { toast } from 'sonner'

interface Job {
    id: number
    title: string
    description: string
    experience_level: string
    location?: string
    mode_of_work?: string
    job_type?: string
    domain?: string
    status: string
    closed_at?: string | null
    created_at: string
    aptitude_enabled?: boolean
    first_level_enabled?: boolean
    interview_mode?: string
    aptitude_config?: string
    behavioral_role?: string
    interview_token?: string
}

export default function PublicJobDetailPage() {
    const params = useParams()
    const router = useRouter()
    const jobId = params.id as string

    const [job, setJob] = useState<Job | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const { user } = useAuth()

    // Application Form State
    const [candidateName, setCandidateName] = useState('')
    const [candidateEmail, setCandidateEmail] = useState('')
    const [candidatePhone, setCandidatePhone] = useState('')
    const [resumeFile, setResumeFile] = useState<File | null>(null)
    const [photoFile, setPhotoFile] = useState<File | null>(null)
    const fileInputRef = useRef<HTMLInputElement>(null)
    const photoInputRef = useRef<HTMLInputElement>(null)

    const [isSubmitting, setIsSubmitting] = useState(false)
    const [submitError, setSubmitError] = useState<string | null>(null)
    const [isSuccess, setIsSuccess] = useState(false)

    useEffect(() => {
        fetchJobDetails()
    }, [jobId])

    const fetchJobDetails = async () => {
        try {
            setIsLoading(true)
            const data = await APIClient.get<Job>(`/api/jobs/public/${jobId}`)
            setJob(data)
        } catch (err: any) {
            setError(err.message)
        } finally {
            setIsLoading(false)
        }
    }

    const handleCloseJob = async () => {
        if (!confirm('Are you sure you want to close this job? Applications will be retained.')) return
        try {
            await APIClient.put(`/api/jobs/${jobId}`, { status: 'closed' })
            fetchJobDetails()
        } catch (err) {
            console.error("Close Error:", err)
            alert('Failed to close job')
        }
    }

    const handleDeleteJob = async () => {
        if (!confirm('Are you sure you want to DELETE this job? All applications will be permanently removed.')) return
        try {
            await APIClient.delete(`/api/jobs/${jobId}`)
            router.push('/dashboard/hr/jobs')
        } catch (err) {
            console.error("Delete Error:", err)
            alert('Failed to delete job')
        }
    }

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            const file = e.target.files[0]
            if (file.size > 5 * 1024 * 1024) {
                setSubmitError('File is too large. Maximum size is 5MB.')
                if (fileInputRef.current) fileInputRef.current.value = ''
                setResumeFile(null)
                return
            }
            setResumeFile(file)
            setSubmitError(null)
        }
    }

    const handlePhotoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            const file = e.target.files[0]
            if (file.size > 5 * 1024 * 1024) {
                setSubmitError('Photo is too large. Maximum size is 5MB.')
                if (photoInputRef.current) photoInputRef.current.value = ''
                setPhotoFile(null)
                return
            }
            setPhotoFile(file)
            setSubmitError(null)
        }
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!resumeFile) {
            setSubmitError("Please upload a resume.")
            return
        }

        setIsSubmitting(true)
        setSubmitError(null)

        const formData = new FormData()
        formData.append('job_id', jobId)
        formData.append('candidate_name', candidateName)
        formData.append('candidate_email', candidateEmail)
        if (candidatePhone) formData.append('candidate_phone', candidatePhone)
        formData.append('resume_file', resumeFile)
        if (photoFile) formData.append('photo_file', photoFile)

        try {
            await APIClient.postFormData('/api/applications/apply', formData)
            setIsSuccess(true)
        } catch (err: any) {
            setSubmitError(err.message || 'An unexpected error occurred.')
        } finally {
            setIsSubmitting(false)
        }
    }

    if (isLoading) {
        return (
            <div className="min-h-screen bg-background flex flex-col items-center justify-center">
                <Loader2 className="h-12 w-12 text-indigo-600 animate-spin mb-4" />
                <p className="text-muted-foreground animate-pulse">Loading job details...</p>
            </div>
        )
    }

    if (error || !job) {
        return (
            <div className="min-h-screen bg-background flex flex-col items-center justify-center p-6">
                <div className="bg-destructive/10 border border-destructive/20 text-destructive p-8 rounded-2xl max-w-md w-full text-center">
                    <AlertCircle className="h-12 w-12 mx-auto mb-4 opacity-80" />
                    <h2 className="text-2xl font-bold mb-2">Position Unavailable</h2>
                    <p className="mb-6">{error || 'Could not load job details.'}</p>
                    <Link href="/jobs">
                        <Button variant="outline" className="w-full border-destructive/30 hover:bg-destructive/10 text-destructive">
                            View Other Openings
                        </Button>
                    </Link>
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-[#f0f9ff] dark:bg-slate-950 font-sans relative">
            <div className="pointer-events-none absolute inset-0 z-0 flex justify-center">
                <div className="absolute inset-0 bg-[linear-gradient(to_right,#8080801a_1px,transparent_1px),linear-gradient(to_bottom,#8080801a_1px,transparent_1px)] bg-[size:40px_40px] dark:bg-[linear-gradient(to_right,#ffffff15_1px,transparent_1px),linear-gradient(to_bottom,#ffffff15_1px,transparent_1px)]" />
            </div>

            <main className="max-w-7xl mx-auto px-6 py-12 lg:flex lg:gap-12 relative">
                {/* Back Button */}
                <div className="absolute top-4 left-6 z-10">
                    <Link href="/jobs" className="flex items-center gap-2 text-sm font-medium text-foreground hover:text-indigo-600 transition-colors group">
                        <ArrowLeft className="h-4 w-4 group-hover:-translate-x-1 transition-transform" />
                        <span className="hidden sm:inline">Back</span>
                    </Link>
                </div>

                {/* Job Details Column */}
                <div className="lg:w-2/3 space-y-8 animate-in fade-in slide-in-from-bottom-8 duration-700">
                    <div>
                        <div className="flex flex-wrap items-center gap-3 mb-4">
                            {job.status === 'closed' && (
                                <Badge className="capsule-badge bg-red-100 text-red-600 border border-red-200 capitalize px-3 py-1 font-semibold tracking-wide shadow-sm">
                                    CLOSED
                                </Badge>
                            )}
                            <Badge className="capsule-badge capsule-badge-primary capitalize px-3 py-1 font-semibold tracking-wide">
                                {job.experience_level || 'Open Level'}
                            </Badge>
                            <Badge className="capsule-badge capsule-badge-neutral font-medium px-3 py-1">
                                {job.mode_of_work || 'Remote'}
                            </Badge>
                            {job.status === 'closed' && job.closed_at && (
                                <span className="text-xs text-muted-foreground mr-1">
                                    Closed on {new Date(job.closed_at).toLocaleDateString()}
                                </span>
                            )}
                        </div>

                        <div className="flex flex-col md:flex-row md:items-start justify-between gap-4 mb-6">
                            <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-foreground leading-[1.1]">
                                {job.title}
                            </h1>

                            {/* HR Actions Panel */}
                            {user?.role === 'hr' && (
                                <div className="flex items-center gap-2 p-2 bg-muted/30 border border-border rounded-lg shrink-0">
                                    <Link href={`/dashboard/hr/jobs/${job.id}/edit`}>
                                        <Button variant="ghost" size="sm" className="h-8 text-primary hover:bg-primary/10">
                                            <Edit2 className="w-4 h-4 mr-2" /> Edit
                                        </Button>
                                    </Link>
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className="h-8 text-muted-foreground hover:bg-muted"
                                        onClick={handleCloseJob}
                                    >
                                        <XCircle className="w-4 h-4 mr-2" /> Close
                                    </Button>
                                    <div className="w-px h-4 bg-border mx-1"></div>
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className="h-8 text-destructive hover:bg-destructive/10"
                                        onClick={handleDeleteJob}
                                    >
                                        <Trash2 className="w-4 h-4 mr-2" /> Delete
                                    </Button>
                                </div>
                            )}
                        </div>
                        <div className="flex flex-wrap gap-6 text-sm text-muted-foreground mb-12">
                            <span className="flex items-center gap-2">
                                <MapPin className="h-5 w-5 opacity-70" /> {job.mode_of_work || 'Remote'}
                            </span>
                            {(job.mode_of_work !== 'Remote' && job.location) && (
                                <span className="flex items-center gap-2 text-muted-foreground/80">
                                    {job.location}
                                </span>
                            )}
                            <span className="flex items-center gap-2">
                                <Clock className="h-5 w-5 opacity-70" /> {job.job_type || 'Full-Time'}
                            </span>
                            <span className="flex items-center gap-2">
                                <Briefcase className="h-5 w-5 opacity-70" /> {job.domain || 'Engineering'}
                            </span>
                        </div>
                    </div>

                    <div className="prose prose-slate dark:prose-invert max-w-none text-foreground leading-relaxed text-lg">
                        <div className="whitespace-pre-wrap">{job.description}</div>
                    </div>

                    {/* Interview Pipeline Info */}
                    {(job.aptitude_enabled || job.first_level_enabled || job.behavioral_role) && (
                        <div className="mt-10 p-6 bg-indigo-500/5 border border-indigo-500/20 rounded-2xl space-y-4 animate-in fade-in duration-500">
                            <h3 className="text-lg font-bold text-foreground flex items-center gap-2">
                                <svg className="w-5 h-5 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" /></svg>
                                Interview Pipeline
                            </h3>
                            <p className="text-sm text-muted-foreground">Here's what to expect during the interview process for this role:</p>
                            <div className="flex flex-col gap-3">
                                {job.aptitude_enabled && (
                                    <div className="flex items-start gap-3 p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl">
                                        <div className="w-8 h-8 rounded-full bg-amber-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                                            <span className="text-amber-600 dark:text-amber-400 font-bold text-sm">1</span>
                                        </div>
                                        <div>
                                            <p className="font-semibold text-foreground text-sm">Aptitude Round</p>
                                        </div>
                                    </div>
                                )}
                                {job.first_level_enabled && (
                                    <div className="flex items-start gap-3 p-3 bg-blue-500/10 border border-blue-500/20 rounded-xl">
                                        <div className="w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                                            <span className="text-blue-600 dark:text-blue-400 font-bold text-sm">
                                                {job.aptitude_enabled ? '2' : '1'}
                                            </span>
                                        </div>
                                        <div>
                                            <p className="font-semibold text-foreground text-sm">Technical Interview</p>
                                            <p className="text-xs text-muted-foreground">
                                                {job.interview_mode === 'ai_questions' && 'AI-generated technical questions tailored to your skills and the role requirements.'}
                                                {job.interview_mode === 'mixed_questions' && 'A mix of AI-generated and recruiter-curated questions covering technical aspects.'}
                                                {job.interview_mode === 'upload_questions' && 'Recruiter-curated questions specifically designed for this position.'}
                                                {!job.interview_mode && 'Questions covering technical skills and domain knowledge.'}
                                            </p>
                                        </div>
                                    </div>
                                )}
                                {job.behavioral_role && (
                                    <div className="flex items-start gap-3 p-3 bg-purple-500/10 border border-purple-500/20 rounded-xl">
                                        <div className="w-8 h-8 rounded-full bg-purple-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                                            <span className="text-purple-600 dark:text-purple-400 font-bold text-sm">
                                                {(job.aptitude_enabled && job.first_level_enabled) ? '3' : (job.aptitude_enabled || job.first_level_enabled) ? '2' : '1'}
                                            </span>
                                        </div>
                                        <div>
                                            <p className="font-semibold text-foreground text-sm">Behavioral Assessment</p>
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>

                {/* Application Form Column (Sticky Sidebar) */}
                <div className="lg:w-1/3 w-full mt-16 lg:mt-0">
                    <div className="lg:sticky lg:top-28 z-10 w-full pb-12">
                        {user?.role === 'hr' ? (
                            <Card className="bg-muted/10 border-dashed border-2 border-border/60 shadow-none">
                                <CardContent className="pt-10 pb-10 text-center space-y-4">
                                    <div className="w-16 h-16 bg-muted/50 rounded-full flex items-center justify-center mx-auto mb-2">
                                        <Briefcase className="h-8 w-8 text-muted-foreground/60" />
                                    </div>
                                    <h3 className="text-lg font-semibold text-foreground/80">HR Preview Mode</h3>
                                    <p className="text-sm text-muted-foreground leading-relaxed px-2">
                                        You are viewing this job posting as an administrator. Standard users and candidates will see the application form here.
                                    </p>

                                    {job.interview_token && (
                                        <div className="mt-6 pt-6 border-t border-border/50 text-left">
                                            <h4 className="text-sm font-semibold text-foreground mb-2">Job Link</h4>
                                            <p className="text-xs text-muted-foreground mb-3 leading-relaxed">
                                                Share this job link online.
                                            </p>
                                            <div className="flex items-center gap-2">
                                                <input
                                                    type="text"
                                                    readOnly
                                                    value={`${typeof window !== 'undefined' ? window.location.origin : ''}/jobs/${job.id}`}
                                                    className="flex-1 text-xs px-3 py-2 bg-background border border-border rounded-md text-muted-foreground font-mono focus:outline-none"
                                                />
                                                <Button
                                                    variant="secondary"
                                                    size="sm"
                                                    onClick={() => {
                                                        const link = `${window.location.origin}/jobs/${job.id}`;
                                                        navigator.clipboard.writeText(link);
                                                        toast.success('Job link copied to clipboard');
                                                        setTimeout(() => {
                                                            toast.dismiss();
                                                        }, 2000);
                                                        
                                                    }}
                                                >
                                                    Copy
                                                </Button>
                                            </div>
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        ) : isSuccess ? (
                            <Card className="bg-primary/5 border-primary/20 text-center p-8 animate-in zoom-in-95 duration-500 shadow-xl">
                                <CardContent className="pt-6 space-y-6">
                                    <div className="w-20 h-20 bg-primary/10 rounded-full flex items-center justify-center mx-auto ring-8 ring-primary/5">
                                        <CheckCircle2 className="h-10 w-10 text-primary" />
                                    </div>
                                    <h2 className="text-2xl font-bold text-foreground">Application Received!</h2>
                                    <p className="text-muted-foreground leading-relaxed">
                                        Thank you, {candidateName.split(' ')[0]}. We've sent a confirmation email to <span className="text-foreground font-medium">{candidateEmail}</span>. Our AI system will begin reviewing your resume shortly.
                                    </p>
                                    <Link href="/jobs" className="block w-full">
                                        <Button className="w-full bg-primary hover:bg-primary/90 text-primary-foreground rounded-xl h-12 text-lg font-semibold transition-all">
                                            Return to Openings
                                        </Button>
                                    </Link>
                                </CardContent>
                            </Card>
                        ) : job.status === 'closed' ? (
                            <Card className="bg-red-500/5 border-red-500/20 text-center p-8 shadow-xl">
                                <CardContent className="pt-6 space-y-6">
                                    <div className="w-16 h-16 bg-red-500/10 rounded-full flex items-center justify-center mx-auto ring-8 ring-red-500/5">
                                        <XCircle className="h-8 w-8 text-red-500" />
                                    </div>
                                    <h2 className="text-2xl font-bold text-foreground">Position Closed</h2>
                                    <p className="text-muted-foreground leading-relaxed">
                                        We are no longer accepting applications for this listing. Please check out our other open positions.
                                    </p>
                                    <Link href="/jobs" className="block w-full">
                                        <Button className="w-full bg-slate-900 border border-slate-700 hover:bg-slate-800 text-white rounded-xl h-12 text-lg font-semibold transition-all">
                                            View Other Openings
                                        </Button>
                                    </Link>
                                </CardContent>
                            </Card>
                        ) : (
                            <Card className="relative shadow-xl border border-white dark:border-slate-800 bg-white dark:bg-slate-900/80 rounded-2xl overflow-hidden backdrop-blur-xl">
                                <div className="absolute top-0 left-0 w-full h-1.5 bg-blue-500" style={{ borderTopLeftRadius: "1.5rem", borderTopRightRadius: "1.5rem" }}></div>
                                <CardHeader className="pt-8 pb-4">
                                    <CardTitle className="text-2xl font-bold text-slate-900 dark:text-white">Apply Now</CardTitle>
                                    <p className="text-sm text-slate-600 dark:text-slate-400">Submit your resume and we'll process your application immediately.</p>
                                </CardHeader>
                                <CardContent>
                                    <form onSubmit={handleSubmit} className="space-y-6">
                                        {submitError && (
                                            <div className="p-4 bg-destructive/10 border border-destructive/20 text-destructive rounded-lg text-sm font-medium animate-in fade-in slide-in-from-top-2">
                                                {submitError}
                                            </div>
                                        )}

                                        <div className="space-y-4">
                                            <div className="space-y-2">
                                                <Label htmlFor="name" className="text-sm font-semibold">Full Name *</Label>
                                                <Input
                                                    id="name"
                                                    required
                                                    value={candidateName}
                                                    onChange={(e) => setCandidateName(e.target.value)}
                                                    className="h-12 bg-muted/50 focus:bg-background transition-colors border-input"
                                                    placeholder="Jane Doe"
                                                />
                                            </div>

                                            <div className="space-y-2">
                                                <Label htmlFor="email" className="text-sm font-semibold">Email *</Label>
                                                <Input
                                                    id="email"
                                                    type="email"
                                                    required
                                                    value={candidateEmail}
                                                    onChange={(e) => setCandidateEmail(e.target.value)}
                                                    className="h-12 bg-muted/50 focus:bg-background transition-colors border-input"
                                                    placeholder="jane@example.com"
                                                />
                                            </div>

                                            <div className="space-y-2">
                                                <Label htmlFor="phone" className="text-sm font-semibold text-muted-foreground">Phone (Optional)</Label>
                                                <Input
                                                    id="phone"
                                                    type="tel"
                                                    value={candidatePhone}
                                                    onChange={(e) => setCandidatePhone(e.target.value)}
                                                    className="h-12 bg-muted/50 focus:bg-background transition-colors border-input"
                                                    placeholder="+1 (555) 000-0000"
                                                />
                                            </div>

                                            <div className="space-y-2 pt-2">
                                                <Label htmlFor="resume" className="text-sm font-semibold">Resume/CV *</Label>
                                                <div
                                                    className={`border-2 border-dashed rounded-xl p-6 text-center transition-all duration-300 ${resumeFile
                                                        ? 'border-primary bg-primary/5'
                                                        : 'border-border hover:border-primary/50 hover:bg-primary/5'
                                                        }`}
                                                >
                                                    <input
                                                        id="resume"
                                                        type="file"
                                                        required
                                                        accept=".pdf,.doc,.docx"
                                                        className="hidden"
                                                        ref={fileInputRef}
                                                        onChange={handleFileChange}
                                                    />

                                                    {resumeFile ? (
                                                        <div className="space-y-2">
                                                            <div className="w-10 h-10 bg-primary/10 text-primary rounded-full flex items-center justify-center mx-auto mb-1">
                                                                <CheckCircle2 className="h-5 w-5" />
                                                            </div>
                                                            <p className="text-xs font-medium text-primary break-words line-clamp-1">
                                                                {resumeFile.name}
                                                            </p>
                                                            <Button
                                                                type="button"
                                                                variant="ghost"
                                                                size="sm"
                                                                className="text-muted-foreground hover:text-destructive h-7 text-[10px]"
                                                                onClick={(e) => {
                                                                    e.preventDefault();
                                                                    setResumeFile(null);
                                                                    if (fileInputRef.current) fileInputRef.current.value = '';
                                                                }}
                                                            >
                                                                Remove
                                                            </Button>
                                                        </div>
                                                    ) : (
                                                        <div
                                                            className="flex flex-col items-center gap-2 cursor-pointer group"
                                                            onClick={() => fileInputRef.current?.click()}
                                                        >
                                                            <div className="w-10 h-10 bg-muted rounded-full flex items-center justify-center group-hover:bg-primary/10 group-hover:text-primary transition-colors">
                                                                <UploadCloud className="h-5 w-5 text-muted-foreground group-hover:text-primary transition-colors" />
                                                            </div>
                                                            <div className="space-y-0.5">
                                                                <p className="text-xs font-semibold text-foreground">Click to upload resume</p>
                                                                <p className="text-[10px] text-muted-foreground">PDF or DOCX</p>
                                                            </div>
                                                        </div>
                                                    )}
                                                </div>
                                            </div>

                                            <div className="space-y-2 pt-2">
                                                <Label htmlFor="photo" className="text-sm font-semibold text-muted-foreground">Candidate Photo (Optional)</Label>
                                                <div
                                                    className={`border-2 border-dashed rounded-xl p-6 text-center transition-all duration-300 ${photoFile
                                                        ? 'border-primary bg-primary/5'
                                                        : 'border-border hover:border-primary/50 hover:bg-primary/5'
                                                        }`}
                                                >
                                                    <input
                                                        id="photo"
                                                        type="file"
                                                        accept="image/*"
                                                        className="hidden"
                                                        ref={photoInputRef}
                                                        onChange={handlePhotoChange}
                                                    />

                                                    {photoFile ? (
                                                        <div className="space-y-2">
                                                            <div className="w-10 h-10 bg-primary/10 text-primary rounded-full flex items-center justify-center mx-auto mb-1">
                                                                <CheckCircle2 className="h-5 w-5" />
                                                            </div>
                                                            <p className="text-xs font-medium text-primary break-words line-clamp-1">
                                                                {photoFile.name}
                                                            </p>
                                                            <Button
                                                                type="button"
                                                                variant="ghost"
                                                                size="sm"
                                                                className="text-muted-foreground hover:text-destructive h-7 text-[10px]"
                                                                onClick={(e) => {
                                                                    e.preventDefault();
                                                                    setPhotoFile(null);
                                                                    if (photoInputRef.current) photoInputRef.current.value = '';
                                                                }}
                                                            >
                                                                Remove
                                                            </Button>
                                                        </div>
                                                    ) : (
                                                        <div
                                                            className="flex flex-col items-center gap-2 cursor-pointer group"
                                                            onClick={() => photoInputRef.current?.click()}
                                                        >
                                                            <div className="w-10 h-10 bg-muted rounded-full flex items-center justify-center group-hover:bg-primary/10 group-hover:text-primary transition-colors">
                                                                <UploadCloud className="h-5 w-5 text-muted-foreground group-hover:text-primary transition-colors" />
                                                            </div>
                                                            <div className="space-y-0.5">
                                                                <p className="text-xs font-semibold text-foreground">Click to upload photo</p>
                                                                <p className="text-[10px] text-muted-foreground">JPG/PNG (Max 5MB)</p>
                                                            </div>
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        </div>

                                        <Button
                                            type="submit"
                                            className="w-full h-14 text-base font-bold bg-gradient-to-r from-primary to-accent hover:from-primary/90 hover:to-accent/90 text-primary-foreground rounded-xl shadow-lg hover:shadow-primary/25 transition-all transform hover:-translate-y-0.5 active:translate-y-0"
                                            disabled={isSubmitting}
                                        >
                                            {isSubmitting ? (
                                                <span className="flex items-center gap-2">
                                                    <Loader2 className="h-5 w-5 animate-spin" />
                                                    Submitting...
                                                </span>
                                            ) : (
                                                "Submit Application"
                                            )}
                                        </Button>
                                    </form>
                                </CardContent>
                            </Card>
                        )}
                    </div>
                </div>

            </main>
        </div>
    )
}
