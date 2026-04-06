'use client'

import React, { useEffect, useState } from 'react'
import Link from 'next/link'
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Briefcase, MapPin, Clock, ArrowRight, Loader2, Search, X } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { ToggleTheme } from '@/components/lightswind/toggle-theme'
import useSWR from 'swr'
import { fetcher } from '@/app/dashboard/lib/swr-fetcher'

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
    created_at: string
    closed_at?: string | null
}

export default function PublicJobsPage() {
    const [searchQuery, setSearchQuery] = useState('')
    const [debouncedSearch, setDebouncedSearch] = useState('')

    useEffect(() => {
        const timer = setTimeout(() => {
            setDebouncedSearch(searchQuery)
        }, 300)
        return () => clearTimeout(timer)
    }, [searchQuery])

    const publicJobsKey = (() => {
        const params = new URLSearchParams()
        params.set('limit', '200')
        if (debouncedSearch) params.set('search', debouncedSearch)
        return `/api/jobs/public?${params.toString()}`
    })()

    const { data: jobs = [], error: fetchError, isLoading } = useSWR<Job[]>(
        publicJobsKey,
        (url: string) => fetcher<Job[]>(url),
        { keepPreviousData: true }
    )

    // Always trust the backend search results.
    // This prevents false negatives when the match exists only in backend-indexed fields.
    const filteredJobs = jobs;

    // Reset to page 1 when search changes
    useEffect(() => { setCurrentPage(1) }, [debouncedSearch]);

    // Pagination
    const JOBS_PER_PAGE = 10
    const [currentPage, setCurrentPage] = useState(1)
    const totalPages = Math.ceil(filteredJobs.length / JOBS_PER_PAGE)
    const paginatedJobs = filteredJobs.slice(
        (currentPage - 1) * JOBS_PER_PAGE,
        currentPage * JOBS_PER_PAGE
    )

    return (
        <div className="min-h-screen bg-background font-sans">
            {/* Main Content */}
            <main className="max-w-7xl mx-auto px-4 sm:px-6 pb-20">
                {/* Immersive Hero Section */}
                <div className="relative overflow-hidden w-full rounded-[2.5rem] bg-slate-950 dark:bg-black border border-slate-800 shadow-2xl mb-16 mt-8">
                    {/* Animated Glow Blobs behind the text - Softened and color-corrected */}
                    <div className="absolute top-0 -left-4 w-72 h-72 bg-indigo-600/10 rounded-full"></div>
                    <div className="absolute top-0 -right-4 w-72 h-72 bg-blue-600/10 rounded-full"></div>
                    <div className="absolute -bottom-8 left-1/2 -translate-x-1/2 w-96 h-96 bg-indigo-700/10 rounded-full"></div>

                    {/* Grid Pattern overlay for tech feel */}
                    <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)]"></div>

                    <div className="relative z-10 px-6 py-24 md:py-32 flex flex-col items-center text-center">
                        <h1 className="text-5xl md:text-7xl font-black tracking-tighter text-transparent bg-clip-text bg-gradient-to-b from-white to-white/60 mb-6 drop-shadow-sm leading-tight">
                            Shape the Future. <br className="hidden md:block" /> Join Us
                        </h1>
                        <p className="text-xl md:text-2xl text-slate-400 max-w-2xl font-light leading-relaxed mb-12">
                            Discover roles that match your unique skills. Our intelligent platform connects exceptional talent with groundbreaking opportunities.
                        </p>

                        <div className="relative max-w-2xl w-full group">
                            {/* Glowing effect behind the search bar - Refined colors */}
                            <div className="absolute -inset-1 bg-gradient-to-r from-indigo-600 to-blue-600 rounded-full blur opacity-25 group-hover:opacity-40 transition duration-1000 group-hover:duration-200"></div>
                            <div className="relative flex items-center gap-4">
                                <div className="relative flex-1">
                                    <Search className="absolute left-6 h-6 w-6 text-indigo-400" />
                                    <Input
                                        placeholder="Search jobs by title, skill, location..."
                                        value={searchQuery}
                                        onChange={(e) => setSearchQuery(e.target.value)}
                                        className="pl-16 pr-14 h-16 w-full bg-slate-900/90 backdrop-blur-xl border-slate-700/50 text-white placeholder:text-slate-500 rounded-full focus:ring-2 focus:ring-indigo-500 text-lg shadow-xl"
                                    />
                                    {searchQuery && (
                                        <button 
                                            onClick={() => setSearchQuery('')}
                                            className="absolute right-6 top-1/2 -translate-y-1/2 p-2 rounded-full hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
                                        >
                                            <X className="h-5 w-5" />
                                        </button>
                                    )}
                                </div>
                                {searchQuery && (
                                    <Button 
                                        variant="outline" 
                                        onClick={() => setSearchQuery('')}
                                        className="h-16 px-8 rounded-full border-slate-700/50 bg-slate-900/90 text-white hover:bg-slate-800 backdrop-blur-xl shadow-xl animate-in fade-in slide-in-from-right-4 duration-300"
                                    >
                                        Clear Filter
                                    </Button>
                                )}
                            </div>
                        </div>
                    </div>
                </div>

                {/* Active Search Indicator / Clear Filter Chip */}
                {searchQuery && (
                    <div className="flex items-center gap-3 mb-8 animate-in fade-in slide-in-from-top-4 duration-300">
                        <div className="flex items-center gap-2 px-4 py-2 bg-indigo-600/10 dark:bg-indigo-500/15 border border-indigo-600/20 rounded-full">
                            <Search className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
                            <span className="text-sm font-medium text-indigo-700 dark:text-indigo-300">
                                Showing results for <span className="font-bold">"{searchQuery}"</span>
                            </span>
                            <button
                                onClick={() => setSearchQuery('')}
                                className="ml-1 p-1 rounded-full hover:bg-indigo-600/20 text-indigo-600 dark:text-indigo-400 transition-colors"
                                aria-label="Clear search"
                            >
                                <X className="h-4 w-4" />
                            </button>
                        </div>
                        <span className="text-sm text-muted-foreground">
                            {filteredJobs.length} {filteredJobs.length === 1 ? 'result' : 'results'} found
                        </span>
                    </div>
                )}

                {isLoading && jobs.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-32 space-y-4">
                        <Loader2 className="h-10 w-10 text-indigo-600 animate-spin" />
                        <p className="text-muted-foreground animate-pulse">Loading open roles...</p>
                    </div>
                ) : fetchError ? (
                    <div className="bg-destructive/10 border border-destructive/20 text-destructive p-6 rounded-2xl text-center">
                        <p className="font-medium">{(fetchError as Error).message || 'Failed to fetch open positions'}</p>
                    </div>
                ) : filteredJobs.length === 0 ? (
                    <div className="text-center py-20 bg-card rounded-2xl border border-border/50 shadow-sm">
                        <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto mb-4">
                            <Search className="h-8 w-8 text-muted-foreground" />
                        </div>
                        <h3 className="text-xl font-bold mb-2">
                            {searchQuery ? `No results for "${searchQuery}"` : 'No open positions found'}
                        </h3>
                        <p className="text-muted-foreground mb-4">
                            {searchQuery ? 'Try a different keyword or check the spelling.' : 'Check back later for new openings.'}
                        </p>
                        {searchQuery && (
                            <Button 
                                variant="outline" 
                                className="border-indigo-600/30 text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-950 gap-2"
                                onClick={() => setSearchQuery('')}
                            >
                                <X className="h-4 w-4" /> Clear Search & View All
                            </Button>
                        )}
                    </div>
                ) : (
                    <div className="space-y-12">
                        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
                            {paginatedJobs.map((job, idx) => (
                                <Link href={`/jobs/${job.id}`} key={job.id} className="group block outline-none">
                                    <div className="relative h-full transition-all duration-500 animate-in fade-in slide-in-from-bottom-8 fill-mode-both" style={{ animationDelay: `${idx * 50}ms` }}>
                                        <div className="absolute -inset-0.5 bg-gradient-to-br from-primary to-accent rounded-[2rem] blur opacity-0 group-hover:opacity-30 transition duration-500 group-hover:duration-200"></div>
                                        <Card className="relative h-full flex flex-col bg-card/60 backdrop-blur-xl border-border/40 shadow-lg group-hover:border-primary/30 group-hover:-translate-y-1 transition-all duration-300 rounded-[1.8rem] overflow-hidden">
                                            <div className={`absolute top-0 right-0 w-32 h-32 rounded-bl-full -mr-8 -mt-8 transition-transform group-hover:scale-125 duration-500 ${job.status === 'closed' ? 'bg-red-500/10' : 'bg-primary/10'}`}></div>

                                            <CardHeader className="pb-4 relative z-10">
                                                <div className="flex justify-between items-start gap-4 mb-4">
                                                    <div className="p-3 bg-gradient-to-br from-primary/10 to-accent/10 text-primary rounded-2xl group-hover:scale-110 transition-transform duration-300 border border-primary/10">
                                                        <Briefcase className="h-6 w-6" />
                                                    </div>
                                                    <div className="flex flex-col items-end gap-1 text-right">
                                                        <Badge className={`capsule-badge capsule-badge-neutral capitalize px-4 py-1.5 font-bold tracking-wide shadow-sm transition-colors ${job.status === 'closed' ? 'bg-red-100 text-red-600 border border-red-200' : ''}`}>
                                                            {job.status === 'closed' ? 'CLOSED' : (job.experience_level || 'Open Level')}
                                                        </Badge>
                                                        {job.status === 'closed' && job.closed_at && (
                                                            <span className="text-xs text-muted-foreground mr-1">
                                                                Closed on {new Date(job.closed_at).toLocaleDateString()}
                                                            </span>
                                                        )}
                                                    </div>
                                                </div>
                                                <CardTitle className="text-2xl font-bold leading-tight group-hover:text-transparent group-hover:bg-clip-text group-hover:bg-gradient-to-r group-hover:from-primary group-hover:to-accent transition-all line-clamp-2">
                                                    {job.title}
                                                </CardTitle>
                                            </CardHeader>

                                            <CardContent className="flex-1 relative z-10">
                                                <p className="text-muted-foreground text-base line-clamp-3 leading-relaxed mb-8">
                                                    {job.description}
                                                </p>

                                                <div className="flex flex-col gap-2">
                                                    <div className="flex flex-wrap items-center gap-3 text-sm font-semibold">
                                                        <div className="flex items-center gap-1.5 px-3 py-1.5 bg-muted/50 rounded-lg text-foreground/80">
                                                            <MapPin className="h-4 w-4 text-primary" />
                                                            {job.mode_of_work || 'Remote'}
                                                        </div>
                                                        <div className="flex items-center gap-1.5 px-3 py-1.5 bg-muted/50 rounded-lg text-foreground/80">
                                                            <Clock className="h-4 w-4 text-accent" />
                                                            {job.job_type || 'Full-Time'}
                                                        </div>
                                                    </div>
                                                    {(job.mode_of_work !== 'Remote' && job.location) && (
                                                        <div className="text-sm font-medium text-muted-foreground ml-1">
                                                            Location: {job.location}
                                                        </div>
                                                    )}
                                                </div>
                                            </CardContent>

                                            <CardFooter className="pt-6 pb-6 relative z-10">
                                                <div className={`w-full flex items-center justify-between font-bold transition-colors ${job.status === 'closed' ? 'text-muted-foreground' : 'text-blue-600 group-hover:text-blue-600'}`}>
                                                    <span>{job.status === 'closed' ? 'View Details' : 'Apply Now'}</span>
                                                    <div className={`w-10 h-10 rounded-full flex items-center justify-center transition-all duration-300 shadow-sm ${job.status === 'closed' ? 'bg-muted text-muted-foreground group-hover:bg-muted/80' : 'bg-blue-600/10 group-hover:bg-blue-600 group-hover:text-white'}`}>
                                                        <ArrowRight className="h-5 w-5 transition-transform group-hover:translate-x-0.5" />
                                                    </div>
                                                </div>
                                            </CardFooter>
                                        </Card>
                                    </div>
                                </Link>
                            ))}
                        </div>

                        {/* Pagination Controls */}
                        {totalPages > 1 && (
                            <div className="flex flex-col sm:flex-row items-center justify-between pt-8 border-t border-border/50 gap-4 relative z-10">
                                <span className="text-sm text-foreground/70 font-medium">
                                    Displaying {((currentPage - 1) * JOBS_PER_PAGE) + 1} &mdash; {Math.min(currentPage * JOBS_PER_PAGE, filteredJobs.length)} of {filteredJobs.length} roles
                                </span>
                                <div className="flex bg-card/60 rounded-full shadow-sm border border-border/60 p-1 backdrop-blur-md">
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className="rounded-full px-4"
                                        onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                                        disabled={currentPage === 1}
                                    >
                                        Previous
                                    </Button>
                                    <div className="flex items-center gap-1 px-2">
                                        {Array.from({ length: totalPages }).map((_, i) => (
                                            <Button
                                                key={i}
                                                variant={currentPage === i + 1 ? "secondary" : "ghost"}
                                                size="sm"
                                                className={`w-8 h-8 p-0 rounded-full ${currentPage === i + 1 ? 'font-bold bg-primary/10 text-primary' : ''}`}
                                                onClick={() => setCurrentPage(i + 1)}
                                            >
                                                {i + 1}
                                            </Button>
                                        ))}
                                    </div>
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className="rounded-full px-4"
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
            </main>
        </div>
    )
}
