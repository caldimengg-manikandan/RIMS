'use client'

import React, { useState, useRef, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { APIClient } from '@/app/dashboard/lib/api-client'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Sparkles, UploadCloud, Loader2, FileText, X, PlusCircle, ArrowLeft, CheckCircle2 } from 'lucide-react'
import { API_BASE_URL } from '@/lib/config'
import { toast } from 'sonner'

const MAX_QUESTION_FILE_SIZE = 5 * 1024 * 1024 // 5MB

interface JobFormProps {
    mode: 'create' | 'edit'
    initialData?: any
    onSubmit: (formData: any) => Promise<void>
    isSubmitting: boolean
}

export function JobForm({ mode, initialData, onSubmit, isSubmitting }: JobFormProps) {
    const router = useRouter()
    const [isAILoading, setIsAILoading] = useState(false)
    const [showConfirm, setShowConfirm] = useState(false)
    const [error, setError] = useState('')
    const [isUploadingQuestions, setIsUploadingQuestions] = useState(false)
    const [questionFileName, setQuestionFileName] = useState('')
    const fileInputRef = useRef<HTMLInputElement>(null)
    const questionFileRef = useRef<HTMLInputElement>(null)
    const aptitudeFileRef = useRef<HTMLInputElement>(null)

    const [formData, setFormData] = useState({
        title: initialData?.title || '',
        description: initialData?.description || '',
        experience_level: initialData?.experience_level || 'junior',
        location: initialData?.location || '',
        mode_of_work: initialData?.mode_of_work || 'Remote',
        job_type: initialData?.job_type || 'Full-Time',
        domain: initialData?.domain || 'Engineering',
        status: initialData?.status || 'open',

        // Interview pipeline
        aptitude_enabled: initialData?.aptitude_enabled || false,
        aptitude_mode: initialData?.aptitude_mode || 'ai',
        first_level_enabled: initialData?.first_level_enabled ?? true,
        interview_mode: initialData?.interview_mode || 'ai',
        behavioral_role: initialData?.behavioral_role || 'general',
        uploaded_question_file: initialData?.uploaded_question_file || null,
        aptitude_questions_file: initialData?.aptitude_questions_file || null,
        primary_evaluated_skills: initialData?.primary_evaluated_skills || [],
        duration_minutes: initialData?.duration_minutes || 60,
    })

    const [isUploadingAptitude, setIsUploadingAptitude] = useState(false)
    const [aptitudeFileName, setAptitudeFileName] = useState(initialData?.aptitude_questions_file ? 'Existing File' : '')
    const [aptitudeQuestionCount, setAptitudeQuestionCount] = useState(0)

    const [locationSuggestions, setLocationSuggestions] = useState<string[]>([])
    const [showSuggestions, setShowSuggestions] = useState(false)
    const suggestionRef = useRef<HTMLDivElement>(null)

    const [domainsList, setDomainsList] = useState<string[]>([
        "Engineering", "Software", "Support", "Design",
        "Structural Engineering", "Civil Engineering",
        "Electrical Engineering", "Mechanical Engineering",
        "Automobile Engineering", "HR"
    ])
    const [showDomainSuggestions, setShowDomainSuggestions] = useState(false)
    const domainRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        if (initialData) {
            setFormData({
                ...formData,
                ...initialData,
                primary_evaluated_skills: typeof initialData.primary_evaluated_skills === 'string' 
                    ? JSON.parse(initialData.primary_evaluated_skills) 
                    : (initialData.primary_evaluated_skills || [])
            })
            if (initialData.uploaded_question_file) setQuestionFileName('Existing File')
            if (initialData.aptitude_questions_file) setAptitudeFileName('Existing File')
        }
    }, [initialData])

    // Warning for unsaved changes (H020)
    useEffect(() => {
        const handleBeforeUnload = (e: BeforeUnloadEvent) => {
            const hasData = formData.title || formData.description || formData.location;
            if (isSubmitting || !hasData) return;
            e.preventDefault();
            e.returnValue = '';
        };

        window.addEventListener('beforeunload', handleBeforeUnload);
        return () => window.removeEventListener('beforeunload', handleBeforeUnload);
    }, [isSubmitting, formData]);

    useEffect(() => {
        const handleClickOutside = (e: MouseEvent) => {
            if (suggestionRef.current && !suggestionRef.current.contains(e.target as Node)) {
                setShowSuggestions(false)
            }
            if (domainRef.current && !domainRef.current.contains(e.target as Node)) {
                setShowDomainSuggestions(false)
            }
        }
        document.addEventListener('mousedown', handleClickOutside)
        return () => document.removeEventListener('mousedown', handleClickOutside)
    }, [])

    useEffect(() => {
        const fetchLocations = async () => {
            if (!formData.location || formData.location.length < 2) {
                setLocationSuggestions([])
                return
            }
            try {
                const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(formData.location)}&limit=5`)
                if (!res.ok) return
                const data = await res.json()
                if (Array.isArray(data)) {
                    setLocationSuggestions(Array.from(new Set(data.map((item: any) => item.display_name))))
                }
            } catch (error) {
                console.error("Location fetch error", error)
            }
        }
        const timer = setTimeout(fetchLocations, 400)
        return () => clearTimeout(timer)
    }, [formData.location])

    const prevExpRef = useRef(formData.experience_level)
    useEffect(() => {
        if (prevExpRef.current !== formData.experience_level) {
            let newBehavioralRole = formData.behavioral_role;
            if (formData.experience_level === 'intern' || formData.experience_level === 'junior') {
                newBehavioralRole = 'junior';
            } else if (formData.experience_level === 'mid') {
                newBehavioralRole = 'mid';
            } else if (formData.experience_level === 'senior' || formData.experience_level === 'lead') {
                newBehavioralRole = 'lead';
            }

            setFormData(prev => ({
                ...prev,
                behavioral_role: newBehavioralRole,
                ...(prevExpRef.current === 'junior' && formData.experience_level !== 'junior' && { aptitude_enabled: false }),
            }))
            prevExpRef.current = formData.experience_level
        }
    }, [formData.experience_level])

    const handleAIFill = async (file?: File) => {
        setIsAILoading(true)
        setError('')
        try {
            const data = new FormData()
            if (file) {
                data.append('file', file)
            } else if (formData.description) {
                data.append('text_content', formData.description)
            } else {
                setError('Please provide a job description or upload a file to extract details.')
                setIsAILoading(false)
                return
            }

            const baseUrl = API_BASE_URL

            const response = await fetch(`${baseUrl}/api/jobs/extract`, {
                method: 'POST',
                credentials: 'include',
                body: data,
            })

            if (!response.ok) {
                const errData = await response.json()
                throw new Error(errData.detail || 'Failed to extract job details')
            }

            const result = await response.json()

            const expLevelMap: Record<string, string> = {
                'intern': 'intern',
                'junior': 'junior',
                'mid-level': 'mid',
                'senior': 'senior',
                'lead / manager': 'lead'
            }

            setFormData(prev => ({
                ...prev,
                title: result.title || prev.title,
                experience_level: result.experience_level ? (expLevelMap[result.experience_level.toLowerCase()] || prev.experience_level) : prev.experience_level,
                domain: result.domain || prev.domain,
                job_type: result.job_type || prev.job_type,
                mode_of_work: result.mode_of_work || prev.mode_of_work,
                location: result.location || prev.location,
                description: result.description || prev.description,
                primary_evaluated_skills: result.primary_evaluated_skills || prev.primary_evaluated_skills
            }))

            const warnings: string[] = Array.isArray(result.warnings) ? result.warnings : []
            if (warnings.length > 0) {
                toast.warning(warnings.join(" "), { duration: 8000 })
            }

        } catch (err: any) {
            setError(err.message || 'Error occurred during AI extraction.')
        } fileInputRef.current && (fileInputRef.current.value = '')
        setIsAILoading(false)
    }

    const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            handleAIFill(e.target.files[0])
        }
    }

    const handleQuestionFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!e.target.files || e.target.files.length === 0) return
        const file = e.target.files[0]

        const ext = file.name.split('.').pop()?.toLowerCase()
        if (!ext || !['txt', 'pdf', 'docx'].includes(ext)) {
            setError('Invalid file type. Only .txt, .pdf, .docx are allowed.')
            return
        }
        if (file.size > MAX_QUESTION_FILE_SIZE) {
            setError('File is too large. Maximum size is 5MB.')
            return
        }

        setIsUploadingQuestions(true)
        setError('')

        try {
            const data = new FormData()
            data.append('file', file)
            const result = await APIClient.postFormData<{ file_path: string; original_name: string }>(
                '/api/jobs/upload-questions',
                data
            )
            setFormData(prev => ({ ...prev, uploaded_question_file: result.file_path }))
            setQuestionFileName(result.original_name)
        } catch (err: any) {
            setError(err.message || 'Failed to upload question file.')
        } finally {
            setIsUploadingQuestions(false)
            if (questionFileRef.current) questionFileRef.current.value = ''
        }
    }

    const removeQuestionFile = () => {
        setFormData(prev => ({ ...prev, uploaded_question_file: null }))
        setQuestionFileName('')
        if (questionFileRef.current) questionFileRef.current.value = ''
    }

    const handleAptitudeFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!e.target.files || e.target.files.length === 0) return
        const file = e.target.files[0]

        const ext = file.name.split('.').pop()?.toLowerCase()
        if (!ext || !['xlsx'].includes(ext)) {
            setError('Invalid file type. Only Excel (.xlsx) files are allowed for aptitude questions.')
            return
        }
        if (file.size > MAX_QUESTION_FILE_SIZE) {
            setError('File is too large. Maximum size is 5MB.')
            return
        }

        setIsUploadingAptitude(true)
        setError('')

        try {
            const data = new FormData()
            data.append('file', file)
            const result = await APIClient.postFormData<{ file_path: string; original_name: string; questions_count: number }>(
                '/api/jobs/upload-aptitude-questions',
                data
            )
            setFormData(prev => ({ ...prev, aptitude_questions_file: result.file_path }))
            setAptitudeFileName(result.original_name)
            setAptitudeQuestionCount(result.questions_count)
        } catch (err: any) {
            setError(err.message || 'Failed to upload aptitude question file.')
        } finally {
            setIsUploadingAptitude(false)
            if (aptitudeFileRef.current) aptitudeFileRef.current.value = ''
        }
    }

    const removeAptitudeFile = () => {
        setFormData(prev => ({ ...prev, aptitude_questions_file: null }))
        setAptitudeFileName('')
        setAptitudeQuestionCount(0)
        if (aptitudeFileRef.current) aptitudeFileRef.current.value = ''
    }

    const [titleError, setTitleError] = useState<string | null>(null)
    const [descError, setDescError] = useState<string | null>(null)
    const [durationError, setDurationError] = useState<string | null>(null)

    const validateTitle = (value: string) => {
        const v = (value || '').trim()
        if (!v) { setTitleError(null); return }
        if (v.length < 3 || v.length > 100) { setTitleError('Job title must contain 3-100 characters'); return }
        if (!/[A-Za-z]/.test(v)) { setTitleError('Job title must contain text'); return }
        setTitleError(null)
    }

    const validateDescription = (value: string) => {
        const v = (value || '').trim()
        if (!v) { setDescError(null); return }
        if (v.length < 10) { setDescError('Description must be at least 10 characters'); return }
        setDescError(null)
    }

    const validateDuration = (value: number) => {
        if (!value) { setDurationError(null); return }
        if (value < 1 || value > 300) { setDurationError('Duration must be 1-300 mins'); return }
        setDurationError(null)
    }

    const requiresQuestionFile =
        Boolean(formData.first_level_enabled) &&
        (formData.interview_mode === 'upload' || formData.interview_mode === 'mixed')

    const isFormValid =
        formData.title.trim().length >= 3 &&
        formData.description.trim().length >= 10 &&
        !titleError && !descError && !durationError &&
        (!requiresQuestionFile || Boolean(formData.uploaded_question_file))

    const isJunior = formData.experience_level === 'junior' || formData.experience_level === 'intern'

    return (
        <div className="p-4 sm:p-6 md:p-8 max-w-3xl mx-auto overflow-x-hidden">
            <Card className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm rounded-xl animate-in fade-in slide-in-from-bottom-8 duration-700 ease-out fill-mode-both w-full">
                <CardHeader className="space-y-4">
                    <div className="mb-2">
                        <Button
                            variant="ghost"
                            onClick={() => router.back()}
                            className="gap-2 text-muted-foreground hover:text-foreground h-auto p-0 flex items-center transition-colors group"
                        >
                            <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-1" />
                            <span className="text-sm font-bold">Back to Job Listings</span>
                        </Button>
                    </div>
                    <CardTitle className="text-xl sm:text-2xl font-bold text-blue-600 dark:text-blue-400 break-words">
                        {mode === 'create' ? 'Create New Job Position' : 'Edit Job Position'}
                    </CardTitle>
                    <div className="flex flex-col gap-4 pt-2 text-slate-600 dark:text-slate-400">
                        <p className="text-sm">Define the role requirements manually or use AI to auto-fill them.</p>
                        <div className="flex flex-wrap gap-2">
                            <input
                                type="file"
                                accept=".pdf,.doc,.docx,.txt"
                                className="hidden"
                                ref={fileInputRef}
                                onChange={handleFileUpload}
                            />
                            <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                onClick={() => fileInputRef.current?.click()}
                                disabled={isAILoading || isSubmitting}
                                className="gap-2 text-xs flex-1 sm:flex-none"
                            >
                                <UploadCloud className="h-4 w-4" /> Upload JD
                            </Button>
                            <Button
                                type="button"
                                variant="secondary"
                                size="sm"
                                onClick={() => handleAIFill()}
                                disabled={isAILoading || isSubmitting}
                                className="gap-2 bg-primary/10 text-primary hover:bg-primary/20 border-primary/20 text-xs flex-1 sm:flex-none"
                            >
                                {isAILoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                                AI Auto-Fill
                            </Button>
                        </div>
                    </div>
                </CardHeader>
                <CardContent>
                    <form onSubmit={(e) => { 
                        e.preventDefault(); 
                        setError('');
                        setShowConfirm(true); 
                    }} className="space-y-6">
                        {error && (
                            <div className="p-4 bg-destructive/10 text-destructive rounded-lg text-sm border border-destructive/20 ">
                                {error}
                            </div>
                        )}

                        <div>
                            <label htmlFor="title" className="block text-sm font-bold text-foreground mb-1.5 uppercase tracking-wider px-1">
                                Job Title
                            </label>
                            <input
                                id="title"
                                type="text"
                                required
                                className="w-full h-11 px-4 border-2 border-input rounded-xl focus:outline-none focus:ring-4 focus:ring-primary/5 focus:border-primary bg-background text-foreground text-base transition-all"
                                placeholder="e.g. Senior Frontend Engineer"
                                value={formData.title}
                                aria-invalid={Boolean(titleError)}
                                onChange={(e) => { const v = e.target.value; setFormData({ ...formData, title: v }); validateTitle(v) }}
                            />
                            {titleError && <p className="text-xs text-destructive mt-1" role="alert">{titleError}</p>}
                        </div>

                        <div className="grid md:grid-cols-2 gap-6">
                            <div>
                                <label htmlFor="experience" className="block text-sm font-bold text-foreground mb-1.5 uppercase tracking-wider px-1">
                                    Experience Level
                                </label>
                                <select
                                    id="experience"
                                    className="w-full h-11 px-4 border-2 border-input rounded-xl focus:outline-none focus:ring-4 focus:ring-primary/5 focus:border-primary bg-background text-foreground text-base transition-all"
                                    value={formData.experience_level}
                                    onChange={(e) => setFormData({ ...formData, experience_level: e.target.value })}
                                >
                                    <option value="intern">Intern</option>
                                    <option value="junior">Junior (0-2 years)</option>
                                    <option value="mid">Mid-Level (3-5 years)</option>
                                    <option value="senior">Senior (5+ years)</option>
                                    <option value="lead">Lead / Manager</option>
                                </select>
                            </div>
                            <div className="relative" ref={domainRef}>
                                <label htmlFor="domain" className="block text-sm font-bold text-foreground mb-1.5 uppercase tracking-wider px-1">
                                    Domain
                                </label>
                                <input
                                    id="domain"
                                    type="text"
                                    autoComplete="off"
                                    className="w-full px-4 py-2 border border-slate-200 dark:border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-white shadow-sm"
                                    placeholder="Type or select a domain"
                                    value={formData.domain}
                                    onChange={(e) => {
                                        setFormData({ ...formData, domain: e.target.value })
                                        setShowDomainSuggestions(true)
                                    }}
                                    onFocus={() => setShowDomainSuggestions(true)}
                                />
                                {showDomainSuggestions && (
                                    <div className="absolute z-50 w-full mt-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-lg max-h-60 overflow-y-auto">
                                        {(() => {
                                            const searchLower = formData.domain.toLowerCase()
                                            const filtered = domainsList.filter(d => d.toLowerCase().includes(searchLower))
                                            const exactMatch = domainsList.some(d => d.toLowerCase() === searchLower)

                                            return (
                                                <>
                                                    {filtered.map((suggestion, idx) => (
                                                        <div
                                                            key={idx}
                                                            className="px-4 py-3 hover:bg-slate-50 dark:hover:bg-slate-700 cursor-pointer text-sm text-foreground transition-colors border-b border-border/50 last:border-0"
                                                            onClick={() => {
                                                                setFormData({ ...formData, domain: suggestion })
                                                                setShowDomainSuggestions(false)
                                                            }}
                                                        >
                                                            {suggestion}
                                                        </div>
                                                    ))}
                                                    {!exactMatch && formData.domain.trim() !== '' && (
                                                        <div
                                                            className="px-4 py-3 hover:bg-blue-50 dark:hover:bg-blue-900/20 cursor-pointer text-sm font-medium text-blue-600 dark:text-blue-400 transition-colors flex items-center gap-2"
                                                            onClick={() => {
                                                                const newDomain = formData.domain.trim()
                                                                setDomainsList(prev => [...prev, newDomain])
                                                                setFormData({ ...formData, domain: newDomain })
                                                                setShowDomainSuggestions(false)
                                                            }}
                                                        >
                                                            <PlusCircle className="h-4 w-4" /> Add "{formData.domain.trim()}"
                                                        </div>
                                                    )}
                                                </>
                                            )
                                        })()}
                                    </div>
                                )}
                            </div>
                            <div>
                                <label htmlFor="job_type" className="block text-sm font-bold text-foreground mb-1.5 uppercase tracking-wider px-1">
                                    Job Type
                                </label>
                                <select
                                    id="job_type"
                                    className="w-full px-4 py-2 border border-slate-200 dark:border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-white shadow-sm"
                                    value={formData.job_type}
                                    onChange={(e) => setFormData({ ...formData, job_type: e.target.value })}
                                >
                                    <option value="Full-Time">Full-Time</option>
                                    <option value="Part-Time">Part-Time</option>
                                    <option value="Contract">Contract</option>
                                    <option value="Internship">Internship</option>
                                    <option value="Temporary">Temporary</option>
                                </select>
                            </div>
                            <div>
                                <label htmlFor="mode_of_work" className="block text-sm font-bold text-foreground mb-1.5 uppercase tracking-wider px-1">
                                    Mode of Work
                                </label>
                                <select
                                    id="mode_of_work"
                                    className="w-full px-4 py-2 border border-slate-200 dark:border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary bg-white dark:bg-slate-800 text-slate-900 dark:text-white shadow-sm"
                                    value={formData.mode_of_work}
                                    onChange={(e) => {
                                        const newMode = e.target.value;
                                        setFormData({
                                            ...formData,
                                            mode_of_work: newMode,
                                            location: formData.location === 'On-Site' ? '' : formData.location
                                        });
                                    }}
                                >
                                    <option value="On-Site">On-Site</option>
                                    <option value="Remote">Remote</option>
                                    <option value="Hybrid">Hybrid</option>
                                </select>
                            </div>
                            {formData.mode_of_work !== 'Remote' && (
                                <div className="relative" ref={suggestionRef}>
                                    <label htmlFor="location" className="block text-sm font-bold text-foreground mb-1.5 uppercase tracking-wider px-1">
                                        Location
                                    </label>
                                    <input
                                        id="location"
                                        type="text"
                                        autoComplete="off"
                                        className="w-full h-11 px-4 border-2 border-input rounded-xl focus:outline-none focus:ring-4 focus:ring-primary/5 focus:border-primary bg-background text-foreground text-base transition-all"
                                        placeholder="e.g. TN, Bangalore, India"
                                        value={formData.location}
                                        onChange={(e) => {
                                            setFormData({ ...formData, location: e.target.value })
                                            setShowSuggestions(true)
                                        }}
                                        onFocus={() => setShowSuggestions(true)}
                                    />
                                    {showSuggestions && locationSuggestions.length > 0 && (
                                        <div className="absolute z-50 w-full mt-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-lg max-h-60 overflow-y-auto">
                                            {locationSuggestions.map((suggestion, idx) => (
                                                <div
                                                    key={idx}
                                                    className="px-4 py-3 hover:bg-slate-50 dark:hover:bg-slate-700 cursor-pointer text-sm text-foreground transition-colors border-b border-border/50 last:border-0"
                                                    onClick={() => {
                                                        setFormData({ ...formData, location: suggestion })
                                                        setShowSuggestions(false)
                                                    }}
                                                >
                                                    {suggestion}
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}
                            {mode === 'edit' && (
                                <div>
                                    <label htmlFor="status" className="block text-sm font-bold text-foreground mb-1.5 uppercase tracking-wider px-1">
                                        Job Status
                                    </label>
                                    <select
                                        id="status"
                                        className="w-full px-4 py-2 border border-slate-200 dark:border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-white shadow-sm"
                                        value={formData.status}
                                        onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                                    >
                                        <option value="open">Active / Open</option>
                                        <option value="closed">Closed / Finalized</option>
                                    </select>
                                </div>
                            )}
                        </div>

                        <div>
                            <label htmlFor="description" className="block text-sm font-bold text-foreground mb-1.5 uppercase tracking-wider px-1">
                                Job Description
                            </label>
                            <textarea
                                id="description"
                                required
                                rows={6}
                                className="w-full px-4 py-3 border-2 border-input rounded-xl focus:outline-none focus:ring-4 focus:ring-primary/5 focus:border-primary bg-background text-foreground text-base transition-all leading-relaxed"
                                placeholder="Describe the role responsibilities, team culture, and key expectations..."
                                value={formData.description}
                                aria-invalid={Boolean(descError)}
                                onChange={(e) => { const v = e.target.value; setFormData({ ...formData, description: v }); validateDescription(v) }}
                            />
                            {descError && <p className="text-xs text-destructive mt-1" role="alert">{descError}</p>}
                        </div>

                        <div className="rounded-xl border border-border bg-muted/30 p-5 space-y-5">
                            <div>
                                <h3 className="text-sm font-semibold text-foreground tracking-wide uppercase">
                                    Interview Pipeline
                                </h3>
                                <p className="text-xs text-muted-foreground mt-0.5">
                                    Configure the evaluation stages for candidates applying to this role.
                                </p>
                            </div>

                            {/* Interview Duration */}
                            <div className="space-y-2">
                                <label htmlFor="duration_minutes" className="block text-sm font-medium text-foreground">
                                    Total Interview Duration (minutes)
                                </label>
                                <div className="flex items-center gap-3">
                                    <input
                                        id="duration_minutes"
                                        type="number"
                                        min="10"
                                        max="300"
                                        className="w-32 h-10 px-3 border-2 border-input rounded-lg focus:outline-none focus:ring-4 focus:ring-primary/5 focus:border-primary bg-background text-foreground transition-all"
                                        value={formData.duration_minutes}
                                        aria-invalid={Boolean(durationError)}
                                        onChange={(e) => { const n = parseInt(e.target.value) || 60; setFormData({ ...formData, duration_minutes: n }); validateDuration(n) }}
                                    />
                                    <span className="text-sm text-muted-foreground">Sets the timer for all rounds combined.</span>
                                </div>
                                {durationError && <p className="text-xs text-destructive" role="alert">{durationError}</p>}
                            </div>

                            {/* Aptitude Round */}
                            {isJunior && (
                                <label className="flex items-center gap-3 cursor-pointer group">
                                    <input
                                        type="checkbox"
                                        checked={formData.aptitude_enabled}
                                        onChange={(e) => setFormData({ ...formData, aptitude_enabled: e.target.checked })}
                                        className="h-4 w-4 rounded border-input text-primary focus:ring-primary"
                                    />
                                    <div>
                                        <span className="text-sm font-medium text-foreground group-hover:text-primary transition-colors">
                                            Enable Aptitude Round
                                        </span>
                                        <p className="text-xs text-muted-foreground">Screen candidates with aptitude questions before the interview.</p>
                                    </div>
                                </label>
                            )}

                            {isJunior && formData.aptitude_enabled && (
                                <div className="ml-7 space-y-3 animate-in fade-in slide-in-from-top-2 duration-300">
                                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                                        Aptitude Generation Mode
                                    </p>
                                    <div className="space-y-2">
                                        {[
                                            { value: 'ai', label: 'AI Generated', desc: 'Generate exactly 10 aptitude questions.' },
                                            { value: 'upload', label: 'Upload Excel', desc: 'Upload .xlsx with Question and Answer columns (10 randomly selected).' },
                                        ].map((mode) => (
                                            <label
                                                key={mode.value}
                                                className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all
                                                    ${formData.aptitude_mode === mode.value
                                                        ? 'border-primary bg-primary/5 ring-1 ring-primary/20'
                                                        : 'border-border hover:border-primary/40 bg-background'
                                                    }`}
                                            >
                                                <input
                                                    type="radio"
                                                    name="aptitude_mode"
                                                    value={mode.value}
                                                    checked={formData.aptitude_mode === mode.value}
                                                    onChange={() => {
                                                        setFormData(prev => ({
                                                            ...prev,
                                                            aptitude_mode: mode.value,
                                                            ...(mode.value !== 'upload' && { aptitude_questions_file: null }),
                                                        }))
                                                        if (mode.value !== 'upload') removeAptitudeFile()
                                                    }}
                                                    className="mt-0.5 h-4 w-4 text-primary focus:ring-primary border-input"
                                                />
                                                <div>
                                                    <span className="text-sm font-medium text-foreground">{mode.label}</span>
                                                    <p className="text-xs text-muted-foreground">{mode.desc}</p>
                                                </div>
                                            </label>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {isJunior && formData.aptitude_enabled && formData.aptitude_mode === 'upload' && (
                                <div className="ml-7 mt-3 space-y-3 animate-in fade-in slide-in-from-top-2 duration-300">
                                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                                        Aptitude Questions File
                                    </p>
                                    {formData.aptitude_questions_file ? (
                                        <div className="flex items-center gap-3 p-3 rounded-lg border border-green-500/30 bg-green-500/5">
                                            <FileText className="h-5 w-5 text-green-600" />
                                            <div className="flex-1 min-w-0">
                                                <p className="text-sm font-medium text-foreground truncate">{aptitudeFileName}</p>
                                                <p className="text-xs text-muted-foreground">Uploaded successfully</p>
                                            </div>
                                            <button
                                                type="button"
                                                onClick={removeAptitudeFile}
                                                className="p-1 rounded-full hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors"
                                            >
                                                <X className="h-4 w-4" />
                                            </button>
                                        </div>
                                    ) : (
                                        <div>
                                            <input
                                                type="file"
                                                ref={aptitudeFileRef}
                                                accept=".xlsx"
                                                className="hidden"
                                                onChange={handleAptitudeFileUpload}
                                            />
                                            <Button
                                                type="button"
                                                variant="outline"
                                                size="sm"
                                                onClick={() => aptitudeFileRef.current?.click()}
                                                disabled={isUploadingAptitude}
                                                className="gap-2"
                                            >
                                                {isUploadingAptitude ? (
                                                    <Loader2 className="h-4 w-4 animate-spin" />
                                                ) : (
                                                    <UploadCloud className="h-4 w-4" />
                                                )}
                                                {isUploadingAptitude ? 'Uploading...' : 'Upload Aptitude Questions'}
                                            </Button>
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* First Level Interview */}
                            <div className="space-y-4">
                                <div className="flex items-center gap-2">
                                    <CheckCircle2 className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                                    <div>
                                        <span className="text-sm font-bold text-foreground">
                                            First Level Interview
                                        </span>
                                        <p className="text-xs text-muted-foreground">Evaluate candidates through a structured interview round.</p>
                                    </div>
                                </div>

                                <div className="ml-7 space-y-3 animate-in fade-in slide-in-from-top-2 duration-300">
                                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                                        Interview Mode
                                    </p>
                                    <div className="space-y-2">
                                        {[
                                            { value: 'ai', label: 'AI Generated Questions', desc: 'System generates all questions automatically using AI. No file upload needed.' },
                                            { value: 'upload', label: 'Upload Questions (AI Evaluated)', desc: 'Only your uploaded questions will be asked. AI evaluates candidate answers.' },
                                            { value: 'mixed', label: 'Mixed Questions', desc: 'Combines your uploaded questions (50%) with AI-generated questions (50%).' },
                                        ].map((modeItem) => (
                                            <label
                                                key={modeItem.value}
                                                className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all
                                                ${formData.interview_mode === modeItem.value
                                                        ? 'border-primary bg-primary/5 ring-1 ring-primary/20'
                                                        : 'border-border hover:border-primary/40 bg-background'
                                                    }`}
                                            >
                                                <input
                                                    type="radio"
                                                    name="interview_mode"
                                                    value={modeItem.value}
                                                    checked={formData.interview_mode === modeItem.value}
                                                    onChange={() => {
                                                        setFormData(prev => ({
                                                            ...prev,
                                                            interview_mode: modeItem.value,
                                                            first_level_enabled: true,
                                                            ...(modeItem.value === 'ai' && { uploaded_question_file: null }),
                                                        }))
                                                        if (modeItem.value === 'ai') setQuestionFileName('')
                                                    }}
                                                    className="mt-0.5 h-4 w-4 text-primary focus:ring-primary border-input"
                                                />
                                                <div className="flex-1">
                                                    <span className="text-sm font-medium text-foreground">{modeItem.label}</span>
                                                    <p className="text-xs text-muted-foreground">{modeItem.desc}</p>

                                                    {(modeItem.value === 'upload' || modeItem.value === 'mixed') && formData.interview_mode === modeItem.value && (
                                                        <div className="mt-3 animate-in fade-in slide-in-from-top-2 duration-200">
                                                            {formData.uploaded_question_file ? (
                                                                <div className="flex items-center gap-3 p-3 rounded-lg border border-green-500/30 bg-green-500/5">
                                                                    <FileText className="h-5 w-5 text-green-600" />
                                                                    <div className="flex-1 min-w-0">
                                                                        <p className="text-sm font-medium text-foreground truncate">{questionFileName}</p>
                                                                        <p className="text-xs text-muted-foreground">Uploaded successfully</p>
                                                                    </div>
                                                                    <button
                                                                        type="button"
                                                                        onClick={removeQuestionFile}
                                                                        className="p-1 rounded-full hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors"
                                                                    >
                                                                        <X className="h-4 w-4" />
                                                                    </button>
                                                                </div>
                                                            ) : (
                                                                <div>
                                                                    <input
                                                                        type="file"
                                                                        ref={questionFileRef}
                                                                        accept=".txt,.pdf,.docx"
                                                                        className="hidden"
                                                                        onChange={handleQuestionFileUpload}
                                                                    />
                                                                    <Button
                                                                        type="button"
                                                                        variant="outline"
                                                                        size="sm"
                                                                        onClick={() => questionFileRef.current?.click()}
                                                                        disabled={isUploadingQuestions}
                                                                        className="gap-2"
                                                                    >
                                                                        {isUploadingQuestions ? <Loader2 className="h-4 w-4 animate-spin" /> : <UploadCloud className="h-4 w-4" />}
                                                                        {isUploadingQuestions ? 'Uploading...' : 'Upload Questions'}
                                                                    </Button>
                                                                </div>
                                                            )}
                                                        </div>
                                                    )}
                                                </div>
                                            </label>
                                        ))}
                                    </div>
                                </div>
                            </div>

                            {/* Behavioral Level Selector */}
                            <div className="space-y-4 pt-4 border-t border-border">
                                <label htmlFor="behavioral_role" className="block text-sm font-medium text-foreground tracking-wide">
                                    Behavioral Role Evaluation
                                </label>
                                <p className="text-xs text-muted-foreground mt-0.5 mb-3">
                                    The system will automatically generate 5 role-specific behavioral questions.
                                </p>
                                <select
                                    id="behavioral_role"
                                    className="w-full md:w-1/2 h-11 px-4 text-base border-2 border-input rounded-xl focus:outline-none focus:ring-4 focus:ring-primary/5 focus:border-primary bg-background text-foreground transition-all"
                                    value={formData.behavioral_role}
                                    onChange={(e) => setFormData({ ...formData, behavioral_role: e.target.value })}
                                >
                                    <option value="general">General (Standard Questions)</option>
                                    <option value="junior">Junior (Learning, Adaptability)</option>
                                    <option value="mid">Mid-Level (Ownership, Problem Solving)</option>
                                    <option value="lead">Lead/Manager (Leadership, Mentorship)</option>
                                </select>
                            </div>
                        </div>

                        <div className="flex flex-col sm:flex-row justify-end gap-3 pt-4">
                            <Link href="/dashboard/hr/jobs" className="w-full sm:w-auto">
                                <Button type="button" variant="outline" className="w-full" disabled={isSubmitting || isAILoading}>Cancel</Button>
                            </Link>
                            <Button
                                type="submit"
                                className="bg-blue-600 hover:bg-blue-700 text-white min-w-[150px] w-full sm:w-auto shadow-lg"
                                disabled={isSubmitting || isAILoading || !isFormValid}
                            >
                                {isSubmitting ? (mode === 'create' ? 'Creating...' : 'Saving...') : (mode === 'create' ? 'Review & Post Job' : 'Review & Update Job')}
                            </Button>
                        </div>
                    </form>
                </CardContent>
            </Card>

            <AlertDialog open={showConfirm} onOpenChange={setShowConfirm}>
                <AlertDialogContent className="rounded-2xl">
                    <AlertDialogHeader>
                        <AlertDialogTitle>Are you sure you want to {mode === 'create' ? 'post' : 'update'} this job?</AlertDialogTitle>
                        <AlertDialogDescription>
                            Please verify the details below. Once {mode === 'create' ? 'posted' : 'updated'}, changes will be live.
                        </AlertDialogDescription>
                        <ul className="mt-4 space-y-2 text-foreground font-medium bg-secondary/20 p-4 rounded-xl border border-border text-left text-sm">
                            <li><span className="text-muted-foreground mr-2 font-normal">Title:</span> {formData.title}</li>
                            <li><span className="text-muted-foreground mr-2 font-normal">Experience:</span> {formData.experience_level}</li>
                            <li><span className="text-muted-foreground mr-2 font-normal">Domain:</span> {formData.domain}</li>
                        </ul>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel className="rounded-xl">Cancel</AlertDialogCancel>
                        <AlertDialogAction onClick={() => onSubmit(formData)} className="bg-primary text-primary-foreground rounded-xl">
                            Yes, {mode === 'create' ? 'Post Job' : 'Update Job'}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    )
}
