'use client'

import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/app/dashboard/lib/auth-context'
import { APIClient } from '@/app/dashboard/lib/api-client'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import useSWR, { useSWRConfig } from 'swr'
import { fetcher } from '@/app/dashboard/lib/swr-fetcher'
import { performMutation } from '@/app/dashboard/lib/swr-utils'
import { ArrowLeft, Save, PlusCircle, CheckCircle2, Loader2, Brain } from 'lucide-react'

// Correctly typing params as a Promise for Next.js 15+
interface PageProps {
    params: Promise<{ id: string }>
}

export default function HREditJobPage({ params }: PageProps) {
    const router = useRouter()
    const { mutate: globalMutate } = useSWRConfig()
    const { user } = useAuth()
    const unwrappedParams = React.use(params)
    const jobId = unwrappedParams.id

    const [isSubmitting, setIsSubmitting] = useState(false)
    const [error, setError] = useState('')
    const [saveSuccess, setSaveSuccess] = useState(false)
    const [isDirty, setIsDirty] = useState(false)

    const [formData, setFormData] = useState({
        title: '',
        description: '',
        experience_level: 'junior',
        domain: 'Engineering',
        job_type: 'Full-Time',
        mode_of_work: 'Remote',
        location: '',
        status: 'open',
        primary_evaluated_skills: [] as string[],
        duration_minutes: 60,
        aptitude_enabled: false,
        aptitude_mode: 'ai',
        first_level_enabled: true,
        interview_mode: 'ai',
        behavioral_role: 'general',
    })

    // Location auto-complete state
    const [locationSuggestions, setLocationSuggestions] = useState<string[]>([])
    const [showSuggestions, setShowSuggestions] = useState(false)
    const suggestionRef = React.useRef<HTMLDivElement>(null)

    // Domain auto-complete state
    const [domainsList, setDomainsList] = useState<string[]>([
        "Engineering", "Software", "Support", "Design",
        "Structural Engineering", "Civil Engineering",
        "Electrical Engineering", "Mechanical Engineering",
        "Automobile Engineering", "HR"
    ])
    const [showDomainSuggestions, setShowDomainSuggestions] = useState(false)
    const domainRef = React.useRef<HTMLDivElement>(null)

    // Warning for unsaved changes (H020)
    useEffect(() => {
        const handleBeforeUnload = (e: BeforeUnloadEvent) => {
            if (isSubmitting || !isDirty) return;
            e.preventDefault();
            e.returnValue = '';
        };

        window.addEventListener('beforeunload', handleBeforeUnload);
        return () => window.removeEventListener('beforeunload', handleBeforeUnload);
    }, [isSubmitting, isDirty]);

    // Helper to update form data and mark dirty
    const updateField = (updates: Partial<typeof formData>) => {
        setFormData(prev => ({ ...prev, ...updates }))
        setIsDirty(true)
        setSaveSuccess(false)
    }

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

    // Fetch locations from Nominatim API
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

    const { data: job, isLoading } = useSWR<any>(
        jobId ? `/api/jobs/${jobId}` : null,
        fetcher
    )

    useEffect(() => {
        if (job && !isDirty) {
            setFormData({
                title: job.title,
                description: job.description,
                experience_level: job.experience_level,
                domain: job.domain || 'Engineering',
                job_type: job.job_type || 'Full-Time',
                mode_of_work: job.mode_of_work || 'Remote',
                location: job.location || '',
                status: job.status,
                primary_evaluated_skills: typeof job.primary_evaluated_skills === 'string'
                    ? (() => { try { return JSON.parse(job.primary_evaluated_skills); } catch { return []; } })()
                    : (job.primary_evaluated_skills || []),
                duration_minutes: job.duration_minutes || 60,
                aptitude_enabled: job.aptitude_enabled || false,
                aptitude_mode: job.aptitude_mode || 'ai',
                first_level_enabled: job.first_level_enabled || false,
                interview_mode: job.interview_mode || 'ai',
                behavioral_role: job.behavioral_role || 'general'
            })
        }
    }, [job, isDirty])

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!jobId) return

        const titleTrimmed = formData.title.trim();
        
        // Keep edit validation exactly aligned with backend _validate_job_content.
        if (titleTrimmed.length < 3 || titleTrimmed.length > 100) {
            setError('Job title must contain meaningful text with alphabets');
            return;
        }
        if (!/[A-Za-z]/.test(titleTrimmed)) {
            setError('Job title must contain meaningful text with alphabets');
            return;
        }
        if (!/^[A-Za-z0-9\s\-.,()\/]+$/.test(titleTrimmed)) {
            setError('Job title must contain meaningful text with alphabets');
            return;
        }
        if (/([\-.,()\/])\1{3,}/.test(titleTrimmed)) {
            setError('Job title must contain meaningful text with alphabets');
            return;
        }

        // Job Title & Description Validation (JP004)
        if (formData.description.trim().length < 10) {
            setError('Description must contain meaningful text (minimum 10 characters)');
            return;
        }
        if (!/[a-zA-Z]/.test(formData.description)) {
            setError('Description must contain meaningful text');
            return;
        }
        if (/([\-.,()\/])\1{3,}/.test(formData.description.trim())) {
            setError('Description must contain meaningful text');
            return;
        }

        // Interview duration validation (H024)
        if (formData.duration_minutes < 1 || formData.duration_minutes > 300) {
            setError('Interview duration must be between 1 and 300 minutes');
            return;
        }

        setError('')
        setIsSubmitting(true)
        setSaveSuccess(false)

        try {
            const actionFn = () => APIClient.put(`/api/jobs/${jobId}`, formData)
            
            await performMutation(
                '/api/jobs',
                (data, options) => globalMutate('/api/jobs', data as any, options as any),
                actionFn,
                {
                    lockKey: `job-${jobId}`,
                    successMessage: 'Job updated successfully',
                    invalidateKeys: [`/api/jobs/${jobId}`, '/api/analytics/dashboard']
                }
            )

            // H011: Ensure caches are refreshed before redirecting.
            try {
                await globalMutate(`/api/jobs/${jobId}`)
                await globalMutate(
                    (key) => typeof key === 'string' && (key === '/api/jobs' || key.startsWith('/api/jobs?')),
                )
            } catch {}

            setIsDirty(false)
            setSaveSuccess(true)
            
            // Show success for 1.5 seconds then redirect
            setTimeout(() => {
                router.push('/dashboard/hr/jobs')
            }, 1500)
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to update job')
            setIsSubmitting(false)
        }
    }

    if (isLoading) {
        return (
            <div className="flex justify-center items-center min-h-[60vh]">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            </div>
        )
    }

    return (
        <div className="p-4 sm:p-6 md:p-8 max-w-4xl mx-auto">
            <Card className="border-slate-200 shadow-2xl rounded-3xl overflow-hidden bg-white/80 backdrop-blur-sm">
                <CardHeader className="bg-slate-50/50 border-b">
                    <div className="flex justify-between items-center mb-4">
                        <Button
                            variant="ghost"
                            onClick={() => router.back()}
                            className="gap-2 text-slate-500 hover:text-slate-900 group"
                        >
                            <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-1" />
                            <span className="font-semibold text-sm">Back</span>
                        </Button>
                    </div>
                    <CardTitle className="text-3xl font-bold text-slate-900">
                        Edit Job Posting
                    </CardTitle>
                    <CardDescription className="text-slate-500 text-lg">
                        Refine your requirements and interview process.
                    </CardDescription>
                </CardHeader>
                
                <CardContent className="p-8">
                    <form onSubmit={handleSubmit} className="space-y-8">
                        {error && (
                            <div className="p-4 bg-red-50 text-red-700 rounded-2xl text-sm border border-red-100 flex items-center gap-2 animate-pulse">
                                <span className="font-bold">Error:</span> {error}
                            </div>
                        )}
                        
                        <div className="space-y-6">
                            <h3 className="text-lg font-bold text-slate-800 border-b pb-2">Basic Information</h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="md:col-span-2">
                                    <label className="text-sm font-semibold text-slate-700 mb-2 block">Job Position Title</label>
                                    <input
                                        type="text"
                                        required
                                        className="w-full px-4 py-3 border rounded-xl focus:ring-2 focus:ring-blue-500 bg-white outline-none"
                                        value={formData.title}
                                        onChange={(e) => updateField({ title: e.target.value })}
                                    />
                                </div>

                                <div>
                                    <label className="text-sm font-semibold text-slate-700 mb-2 block">Experience Level</label>
                                    <select
                                        className="w-full px-4 py-3 border rounded-xl focus:ring-2 focus:ring-blue-500 bg-white outline-none"
                                        value={formData.experience_level}
                                        onChange={(e) => updateField({ experience_level: e.target.value })}
                                    >
                                        <option value="intern">Intern</option>
                                        <option value="junior">Junior (0-2 years)</option>
                                        <option value="mid">Mid-Level (3-5 years)</option>
                                        <option value="senior">Senior (5+ years)</option>
                                        <option value="lead">Lead / Manager</option>
                                    </select>
                                </div>

                                <div className="relative" ref={domainRef}>
                                    <label className="text-sm font-semibold text-slate-700 mb-2 block">Industry Domain</label>
                                    <input
                                        type="text"
                                        className="w-full px-4 py-3 border rounded-xl focus:ring-2 focus:ring-blue-500 bg-white outline-none"
                                        value={formData.domain}
                                        onChange={(e) => {
                                            updateField({ domain: e.target.value })
                                            setShowDomainSuggestions(true)
                                        }}
                                        onFocus={() => setShowDomainSuggestions(true)}
                                    />
                                    {showDomainSuggestions && (
                                        <div className="absolute z-50 w-full mt-1 bg-white border rounded-xl shadow-xl max-h-60 overflow-y-auto">
                                            {domainsList.filter(d => d.toLowerCase().includes(formData.domain.toLowerCase())).map((d, i) => (
                                                <div key={i} className="px-4 py-3 hover:bg-slate-50 cursor-pointer" onClick={() => { updateField({ domain: d }); setShowDomainSuggestions(false); }}>{d}</div>
                                            ))}
                                        </div>
                                    )}
                                </div>

                                <div>
                                    <label className="text-sm font-semibold text-slate-700 mb-2 block">Work Mode</label>
                                    <select
                                        className="w-full px-4 py-3 border rounded-xl focus:ring-2 focus:ring-blue-500 bg-white outline-none"
                                        value={formData.mode_of_work}
                                        onChange={(e) => updateField({ mode_of_work: e.target.value })}
                                    >
                                        <option value="Remote">Remote</option>
                                        <option value="Hybrid">Hybrid</option>
                                        <option value="On-Site">On-Site</option>
                                    </select>
                                </div>

                                <div>
                                    <label className="text-sm font-semibold text-slate-700 mb-2 block">Job Status</label>
                                    <select
                                        className="w-full px-4 py-3 border rounded-xl focus:ring-2 focus:ring-blue-500 bg-white outline-none"
                                        value={formData.status}
                                        onChange={(e) => updateField({ status: e.target.value })}
                                    >
                                        <option value="open">Active / Open</option>
                                        <option value="closed">Closed / Finalized</option>
                                    </select>
                                </div>
                            </div>
                        </div>

                        {/* Interview Pipeline */}
                        <div className="space-y-6 pt-6 border-t">
                            <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                                <Brain className="w-5 h-5 text-blue-600" />
                                Interview Pipeline Configuration
                            </h3>
                            
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="p-4 border rounded-xl hover:border-blue-200 transition-colors bg-white shadow-sm">
                                    <div className="flex items-start gap-3">
                                        <input
                                            id="aptitude_enabled"
                                            type="checkbox"
                                            checked={formData.aptitude_enabled}
                                            onChange={(e) => updateField({ aptitude_enabled: e.target.checked })}
                                            className="mt-1 h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                                        />
                                        <div>
                                            <label htmlFor="aptitude_enabled" className="text-sm font-semibold text-slate-800 block">Enable Aptitude Round</label>
                                            <p className="text-xs text-slate-500">Initial MCQ-based screening</p>
                                        </div>
                                    </div>
                                </div>

                                <div className="p-4 border rounded-xl bg-slate-50/50 shadow-sm">
                                    <label className="text-sm font-semibold text-slate-800 mb-3 block">Interview Mode</label>
                                    <div className="flex gap-4">
                                        {['ai', 'manual'].map((m) => (
                                            <label key={m} className="flex items-center gap-2 cursor-pointer">
                                                <input
                                                    type="radio"
                                                    checked={formData.interview_mode === m}
                                                    onChange={() => updateField({ interview_mode: m, first_level_enabled: true })}
                                                    className="h-4 w-4 text-blue-600"
                                                />
                                                <span className="text-sm capitalize">{m}</span>
                                            </label>
                                        ))}
                                    </div>
                                </div>

                                <div className="md:col-span-2">
                                    <label className="text-sm font-semibold text-slate-700 mb-2 block">Interview Focus / Role Seniority</label>
                                    <select
                                        value={formData.behavioral_role}
                                        onChange={(e) => updateField({ behavioral_role: e.target.value })}
                                        className="w-full px-4 py-3 border rounded-xl outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                                    >
                                        <option value="junior">Junior (Focus on Fundamentals)</option>
                                        <option value="mid">Mid-Level (Focus on Ownership)</option>
                                        <option value="lead">Lead/Senior (Focus on Leadership)</option>
                                        <option value="general">General (Standard Industry)</option>
                                    </select>
                                </div>
                            </div>
                        </div>

                        {/* Description */}
                        <div className="space-y-4 pt-6 border-t">
                            <label className="text-lg font-bold text-slate-800 flex items-center gap-2">
                                <PlusCircle className="w-5 h-5 text-blue-600" />
                                Job Description
                            </label>
                            <textarea
                                required
                                rows={8}
                                className="w-full px-4 py-3 border rounded-2xl focus:ring-2 focus:ring-blue-500 bg-slate-50/30 outline-none"
                                value={formData.description}
                                onChange={(e) => updateField({ description: e.target.value })}
                            />
                        </div>

                        <div className="flex flex-col sm:flex-row justify-end gap-4 pt-8 border-t">
                            <Link href="/dashboard/hr/jobs" className="w-full sm:w-auto">
                                <Button type="button" variant="outline" className="w-full px-8 rounded-full">Cancel</Button>
                            </Link>
                            <Button
                                type="submit"
                                disabled={isSubmitting || saveSuccess}
                                className="bg-blue-600 hover:bg-blue-700 text-white min-w-[180px] rounded-full gap-2 shadow-lg"
                            >
                                {isSubmitting ? <Loader2 className="animate-spin h-4 w-4" /> : <Save className="h-4 w-4" />}
                                {saveSuccess ? 'Changes Saved!' : 'Save Job Posting'}
                            </Button>
                        </div>
                    </form>
                </CardContent>
            </Card>
        </div>
    )
}
