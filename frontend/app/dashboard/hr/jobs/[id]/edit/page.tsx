'use client'

import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/app/dashboard/lib/auth-context'
import { APIClient } from '@/app/dashboard/lib/api-client'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Save, PlusCircle } from 'lucide-react'

// Correctly typing params as a Promise for Next.js 15+
interface PageProps {
    params: Promise<{ id: string }>
}

export default function HREditJobPage({ params }: PageProps) {
    const router = useRouter()
    const { user } = useAuth()

    // Unwrap params using React.use() or await in useEffect (since this is client component)
    // For simplicity in client components with async params in Next.js 15:
    const [jobId, setJobId] = useState<string | null>(null)

    const [isSubmitting, setIsSubmitting] = useState(false)
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState('')

    const [formData, setFormData] = useState({
        title: '',
        description: '',
        experience_level: 'junior',
        domain: 'Engineering',
        job_type: 'Full-Time',
        mode_of_work: 'Remote',
        location: '',
        status: 'open',
        primary_evaluated_skills: [] as string[]
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

    // Close suggestions on outside click
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

    useEffect(() => {
        // Unwrap params
        params.then(unwrappedParams => {
            setJobId(unwrappedParams.id)
            fetchJobDetails(unwrappedParams.id)
        })
    }, [params])

    const fetchJobDetails = async (id: string) => {
        try {
            setIsLoading(true)
            const data = await APIClient.get<any>(`/api/jobs/${id}`)
            setFormData({
                title: data.title,
                description: data.description,
                experience_level: data.experience_level,
                domain: data.domain || 'Engineering',
                job_type: data.job_type || 'Full-Time',
                mode_of_work: data.mode_of_work || 'Remote',
                location: data.location || '',
                status: data.status,
                primary_evaluated_skills: typeof data.primary_evaluated_skills === 'string'
                    ? JSON.parse(data.primary_evaluated_skills)
                    : (data.primary_evaluated_skills || [])
            })
        } catch (err) {
            setError('Failed to fetch job details')
            console.error(err)
        } finally {
            setIsLoading(false)
        }
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!jobId) return

        setError('')
        setIsSubmitting(true)

        try {
            await APIClient.put(`/api/jobs/${jobId}`, formData)
            router.push('/dashboard/hr/jobs')
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
        <div className="p-8 max-w-3xl mx-auto">
            <Card className="border-border backdrop-blur-md bg-card/70 shadow-xl rounded-3xl animate-in fade-in slide-in-from-bottom-8 duration-700 ease-out fill-mode-both">
                <CardHeader>
                    <div className="mb-4">
                        <Button
                            variant="ghost"
                            onClick={() => router.back()}
                            className="gap-2 text-muted-foreground hover:text-foreground h-auto p-0 flex items-center transition-colors group"
                        >
                            <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-1" />
                            <span className="text-sm font-bold">Back to Job Listings</span>
                        </Button>
                    </div>
                    <CardTitle className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-accent ">
                        Edit Job Position
                    </CardTitle>
                    <CardDescription>
                        Update the role requirements and details.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <form onSubmit={handleSubmit} className="space-y-6">
                        {error && (
                            <div className="p-4 bg-destructive/10 text-destructive rounded-2xl text-sm border border-destructive/20 ">
                                {error}
                            </div>
                        )}

                        <div>
                            <label htmlFor="title" className="block text-sm font-medium text-foreground mb-1">
                                Job Title
                            </label>
                            <input
                                id="title"
                                type="text"
                                required
                                className="w-full px-4 py-2 border border-input rounded-xl focus:outline-none focus:ring-2 focus:ring-primary bg-background/50"
                                value={formData.title}
                                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                            />
                        </div>

                        <div className="grid md:grid-cols-2 gap-6">
                            <div>
                                <label htmlFor="experience" className="block text-sm font-medium text-foreground mb-1">
                                    Experience Level
                                </label>
                                <select
                                    id="experience"
                                    className="w-full px-4 py-2 border border-input rounded-xl focus:outline-none focus:ring-2 focus:ring-primary bg-background/50"
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
                                <label htmlFor="domain" className="block text-sm font-medium text-foreground mb-1">
                                    Domain
                                </label>
                                <input
                                    id="domain"
                                    type="text"
                                    autoComplete="off"
                                    className="w-full px-4 py-2 border border-input rounded-xl focus:outline-none focus:ring-2 focus:ring-primary bg-background/50"
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
                                                            className="px-4 py-3 hover:bg-primary/10 cursor-pointer text-sm font-medium text-primary transition-colors flex items-center gap-2"
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
                                <label htmlFor="job_type" className="block text-sm font-medium text-foreground mb-1">
                                    Job Type
                                </label>
                                <select
                                    id="job_type"
                                    className="w-full px-4 py-2 border border-input rounded-xl focus:outline-none focus:ring-2 focus:ring-primary bg-background/50"
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
                                <label htmlFor="mode_of_work" className="block text-sm font-medium text-foreground mb-1">
                                    Mode of Work
                                </label>
                                <select
                                    id="mode_of_work"
                                    className="w-full px-4 py-2 border border-input rounded-xl focus:outline-none focus:ring-2 focus:ring-primary bg-background/50"
                                    value={formData.mode_of_work}
                                    onChange={(e) => {
                                        const newMode = e.target.value;
                                        setFormData({
                                            ...formData,
                                            mode_of_work: newMode,
                                            location: formData.location === 'Remote' ? '' : formData.location
                                        });
                                    }}
                                >
                                    <option value="Remote">Remote</option>
                                    <option value="Hybrid">Hybrid</option>
                                    <option value="On-Site">On-Site</option>
                                </select>
                            </div>
                            
                            {formData.mode_of_work !== 'Remote' && (
                                <div className="relative" ref={suggestionRef}>
                                    <label htmlFor="location" className="block text-sm font-medium text-foreground mb-1">
                                        Location
                                    </label>
                                    <input
                                        id="location"
                                        type="text"
                                        autoComplete="off"
                                        className="w-full px-4 py-2 border border-input rounded-xl focus:outline-none focus:ring-2 focus:ring-primary bg-background/50"
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

                            <div>
                                <label htmlFor="status" className="block text-sm font-medium text-foreground mb-1">
                                    Status
                                </label>
                                <select
                                    id="status"
                                    className="w-full px-4 py-2 border border-input rounded-xl focus:outline-none focus:ring-2 focus:ring-primary bg-background/50"
                                    value={formData.status}
                                    onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                                >
                                    <option value="open">Open</option>
                                    <option value="closed">Closed</option>
                                </select>
                            </div>
                        </div>

                        <div>
                            <label htmlFor="description" className="block text-sm font-medium text-foreground mb-1">
                                Job Description
                            </label>
                            <textarea
                                id="description"
                                required
                                rows={6}
                                className="w-full px-4 py-2 border border-input rounded-xl focus:outline-none focus:ring-2 focus:ring-primary bg-background/50"
                                value={formData.description}
                                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                            />
                        </div>

                        <div className="flex justify-end gap-3 pt-4">
                            <Link href="/dashboard/hr/jobs">
                                <Button type="button" variant="outline" className="rounded-full">Cancel</Button>
                            </Link>
                            <Button
                                type="submit"
                                className="bg-primary hover:bg-primary/90 text-primary-foreground min-w-[150px] rounded-full"
                                disabled={isSubmitting}
                            >
                                <Save className="w-4 h-4 mr-2" />
                                {isSubmitting ? 'Saving...' : 'Save Changes'}
                            </Button>
                        </div>
                    </form>
                </CardContent>
            </Card>
        </div>
    )
}
