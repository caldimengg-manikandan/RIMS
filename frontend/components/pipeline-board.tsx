"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { RejectDialog } from "@/components/reject-dialog"
import { APIClient } from '@/app/dashboard/lib/api-client'
import { Button } from "@/components/ui/button"
import { XCircle, Trash2, ListX, FileText } from "lucide-react"
import useSWR from 'swr'
import { fetcher } from '@/app/dashboard/lib/swr-fetcher'
import { useRouter } from 'next/navigation'
import { Checkbox } from "@/components/ui/checkbox"
import { API_BASE_URL } from "@/lib/config"
import { performMutation } from "@/app/dashboard/lib/swr-utils"

type Application = {
    id: number
    job_title: string
    candidate: {
        full_name: string
        email: string
        candidate_photo_path?: string
        photo_url?: string
    }
    status: string
    skill_match_percentage?: number
    resume_score?: number
    aptitude_score?: number | null
    behavioral_score?: number | null
    technical_skills_score?: number | null
}

// ─── FSM State Columns ─────────────────────────────────────────────────
const STATUS_COLUMNS = [
    { id: "applied", label: "Applied" },
    { id: "screened", label: "Screened" },
    { id: "interview_scheduled", label: "Interview Scheduled" },
    { id: "interview_completed", label: "Interview Completed" },
    { id: "hired", label: "Hired" },
    { id: "offer_sent", label: "Offer Sent" },
    { id: "onboarded", label: "Onboarded" },
]

// ─── Allowed FSM Actions Per State (for pipeline card actions) ──────────
const STATE_ACTIONS: Record<string, { action: string; label: string; variant: 'primary' | 'destructive' | 'secondary' | 'success' }[]> = {
    applied: [
        { action: "mark_screened", label: "Screen", variant: "primary" },
    ],
    screened: [
        { action: "approve_for_interview", label: "Approve", variant: "primary" },
    ],
    interview_completed: [
        { action: "hire", label: "Hire", variant: "success" },
    ],
}

const APPLICATIONS_PER_PAGE = 5

export function PipelineBoard({ jobId }: { jobId?: string }) {
    const router = useRouter()
    const apiPath = jobId
        ? `/api/applications?job_id=${jobId}&limit=49`
        : '/api/applications?limit=49'
    const { data: swrData, error, isLoading, mutate } = useSWR<any>(apiPath, (url: string) => fetcher<any>(url))
    const rawApplications = swrData?.items || (Array.isArray(swrData) ? swrData : [])

    const applications: Application[] = rawApplications.map((app: any) => ({
        id: app.id,
        job_title: app.job?.title || "Unknown",
        candidate: {
            full_name: app.candidate_name || "Unknown",
            email: app.candidate_email || "",
            candidate_photo_path: app.candidate_photo_path,
            photo_url: app.photo_url
        },
        status: app.status,
        skill_match_percentage: app.resume_extraction?.skill_match_percentage,
        resume_score: app.resume_extraction?.resume_score,
        aptitude_score: app.interview?.report?.aptitude_score,
        behavioral_score: app.interview?.report?.behavioral_score,
        technical_skills_score: app.interview?.report?.technical_skills_score,
    }))

    const [fetchError, setFetchError] = useState<string | null>(null)
    const [pages, setPages] = useState<Record<string, number>>({})
    const [selectedApps, setSelectedApps] = useState<number[]>([])

    const toggleAppSelection = (id: number) => {
        setSelectedApps(prev => prev.includes(id) ? prev.filter(appId => appId !== id) : [...prev, id])
    }
    
    const handleClearOrDelete = async (colId: string, colApps: Application[]) => {
        const colAppIds = colApps.map(app => app.id)
        const selectedInCol = selectedApps.filter(id => colAppIds.includes(id))
        
        const isDeleteMode = selectedInCol.length > 0
        const itemsToDelete = isDeleteMode ? selectedInCol : colAppIds

        if (itemsToDelete.length === 0) return

        const actionText = isDeleteMode ? `delete ${itemsToDelete.length} selected` : `clear all ${itemsToDelete.length}`
        if (!confirm(`Are you sure you want to ${actionText} applications? This action cannot be undone.`)) {
            return
        }

        const actionFn = () => Promise.all(itemsToDelete.map(id => APIClient.delete(`/api/applications/${id}`)))

        await performMutation<any[]>(
            apiPath,
            mutate,
            actionFn,
            {
                lockKey: `pipeline-bulk-delete-${jobId ?? 'all'}`,
                optimisticData: (current: any) => {
                    const items = Array.isArray(current) ? current : (current?.items || []);
                    const newItems = items.filter((app: any) => !itemsToDelete.includes(app.id));
                    return Array.isArray(current) ? newItems : { ...current, items: newItems };
                },
                successMessage: `Successfully deleted ${itemsToDelete.length} candidate(s)`,
                invalidateKeys: ['/api/analytics/dashboard']
            }
        )
        setSelectedApps(prev => prev.filter(id => !itemsToDelete.includes(id)))
    }

    // ─── FSM Transition Handler ────────────────────────────────────────
    const handleTransition = async (applicationId: number, action: string, notes?: string) => {
        const actionFn = () => APIClient.put(`/api/applications/${applicationId}/status`, {
            action,
            hr_notes: notes || `Action: ${action}`
        })

        await performMutation<any[]>(
            apiPath,
            mutate,
            actionFn,
            {
                lockKey: `application-${applicationId}`,
                optimisticData: (current: any) => {
                    const items = Array.isArray(current) ? current : (current?.items || []);
                    const newItems = items.map((app: any) =>
                        app.id === applicationId 
                            ? { ...app, status: action === 'reject' ? 'rejected' : app.status } 
                            : app
                    );
                    return Array.isArray(current) ? newItems : { ...current, items: newItems };
                },
                invalidateKeys: ['/api/analytics/dashboard']
            }
        )
    }

    const handleReject = async (applicationId: number, reason: string, notes: string) => {
        await handleTransition(applicationId, 'reject', `Reason: ${reason}${notes ? `\nNotes: ${notes}` : ''}`)
    }

    if (isLoading && rawApplications.length === 0) {
        return <div className="flex justify-center items-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
    }

    if (fetchError || error) {
        return (
            <div className="p-4 bg-destructive/10 text-destructive rounded-md border border-destructive/20">
                <h3 className="font-bold">Status</h3>
                <p>{fetchError || (error as Error).message}</p>
                <div className="mt-2 text-sm text-gray-700">
                    <p>Debugging Check:</p>
                    <ul className="list-disc pl-5">
                        <li>Ensure you are logged in as <strong>hr@example.com</strong> (Password: password123)</li>
                        <li>Applications are only visible to the HR user who posted the job.</li>
                    </ul>
                </div>
            </div>
        )
    }

    const getColumnApplications = (status: string) => {
        return applications.filter(app => app.status === status)
    }

    // Determine which non-reject action buttons to show on a card
    const getCardActions = (status: string) => {
        return STATE_ACTIONS[status] || []
    }

    // Check if reject is allowed for this state
    const isRejectAllowed = (status: string) => {
        return !['rejected', 'hired'].includes(status)
    }

    return (
        <div className="flex h-full gap-4 overflow-x-auto pb-4 scrollbar-thin scrollbar-thumb-muted-foreground/20 scrollbar-track-transparent">
            {STATUS_COLUMNS.map((column, colIndex) => (
                <div key={column.id} style={{ animationDelay: `${colIndex * 150}ms` }} className="min-w-[280px] flex-1 max-w-[350px] h-full max-h-full flex flex-col bg-muted rounded-xl border border-border/40 p-2.5 shadow-inner overflow-hidden animate-in fade-in slide-in-from-bottom-8 duration-700 ease-out fill-mode-both">
                    <div className="flex items-center justify-between p-2 mb-2 shrink-0">
                        <div className="flex items-center gap-2">
                            <h3 className="font-bold text-sm text-muted-foreground uppercase tracking-wide">{column.label}</h3>
                        </div>
                        <div className="flex items-center gap-1.5">
                            <Button 
                                variant="ghost" 
                                size="icon" 
                                className="h-6 w-6 text-muted-foreground focus:ring-0 hover:bg-destructive/10 hover:text-destructive transition-colors shrink-0"
                                onClick={() => handleClearOrDelete(column.id, getColumnApplications(column.id))}
                                disabled={getColumnApplications(column.id).length === 0}
                                title={selectedApps.filter(id => getColumnApplications(column.id).map(a => a.id).includes(id)).length > 0 ? "Delete Selected" : "Clear Column"}
                            >
                                {selectedApps.filter(id => getColumnApplications(column.id).map(a => a.id).includes(id)).length > 0
                                    ? <Trash2 className="h-4 w-4" />
                                    : <ListX className="h-4 w-4" />}
                            </Button>
                            <Badge variant="secondary" className="bg-background text-muted-foreground shadow-sm border border-border">
                                {getColumnApplications(column.id).length}
                            </Badge>
                        </div>
                    </div>

                    <ScrollArea className="flex-1 min-h-0 pr-2 pb-2">
                        <div className="space-y-3 p-1">
                            {getColumnApplications(column.id)
                                .slice((pages[column.id] || 0) * APPLICATIONS_PER_PAGE, ((pages[column.id] || 0) + 1) * APPLICATIONS_PER_PAGE)
                                .map((app, index) => (
                                <Card 
                                    key={app.id} 
                                    style={{ animationDelay: `${index * 50}ms` }} 
                                    className={`relative cursor-pointer transition-all duration-300 bg-card border group animate-in fade-in slide-in-from-bottom-4 duration-500 fill-mode-both hover:-translate-y-1 hover:shadow-lg ${selectedApps.includes(app.id) ? 'border-primary shadow-sm bg-primary/5' : 'border-border/50'}`}
                                    onClick={() => router.push(`/dashboard/hr/applications/${app.id}`)}
                                >
                                    {/* Right side controls */}
                                    <div className="absolute inset-y-0 right-1.5 flex flex-col items-center justify-evenly py-2 z-10">
                                        <div onClick={e => e.stopPropagation()} className="cursor-pointer p-1">
                                            <Checkbox 
                                                className="h-5 w-5 bg-background border-2 border-muted-foreground/40 hover:border-primary/80 data-[state=checked]:bg-primary data-[state=checked]:border-primary transition-colors shadow-sm"
                                                checked={selectedApps.includes(app.id)}
                                                onCheckedChange={() => toggleAppSelection(app.id)}
                                            />
                                        </div>
                                        {isRejectAllowed(column.id) && (
                                            <div onClick={(e) => e.stopPropagation()}>
                                                <RejectDialog
                                                    candidateName={app.candidate.full_name}
                                                    onConfirm={(reason, notes) => handleReject(app.id, reason, notes)}
                                                    trigger={
                                                        <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-destructive hover:bg-destructive/10">
                                                            <XCircle className="h-5 w-5" />
                                                        </Button>
                                                    }
                                                />
                                            </div>
                                        )}
                                    </div>
                                    <CardHeader className="p-3 pb-1.5 flex flex-row items-center space-y-0 relative pr-10">
                                        <div className="flex items-start space-x-2.5 flex-1 min-w-0">
                                            <Avatar className="h-8 w-8 border-2 border-background shadow-sm shrink-0">
                                                {app.candidate.photo_url || app.candidate.candidate_photo_path ? (
                                                    <AvatarImage 
                                                        src={app.candidate.photo_url || (app.candidate.candidate_photo_path ? `${API_BASE_URL}/${app.candidate.candidate_photo_path.replace(/\\/g, '/')}` : undefined)}
                                                        alt={app.candidate.full_name}
                                                        className="object-cover"
                                                    />
                                                ) : (
                                                    <AvatarFallback className="bg-primary/10 text-primary font-bold text-xs">
                                                        {app.candidate.full_name?.charAt(0)}
                                                    </AvatarFallback>
                                                )}
                                            </Avatar>
                                            <div className="overflow-hidden min-w-0 pt-0.5">
                                                <CardTitle className="text-[13px] font-bold text-foreground truncate leading-tight">{app.candidate.full_name}</CardTitle>
                                                <CardDescription className="text-[11px] truncate text-muted-foreground font-medium leading-tight mt-0.5" title={app.job_title}>
                                                    {app.job_title}
                                                </CardDescription>
                                            </div>
                                        </div>
                                    </CardHeader>
                                    <CardContent className="p-3 pt-0 pr-10">
                                        <div className="flex flex-wrap gap-1.5 mt-1 items-center">
                                            {app.resume_score && (
                                                <Badge
                                                    variant="outline"
                                                    className={`text-[9px] px-1.5 py-0 h-4 border ${app.resume_score > 80
                                                        ? "bg-primary/10 text-primary border-primary/20"
                                                        : "bg-secondary/10 text-secondary-foreground border-border"
                                                        }`}
                                                >
                                                    Job Comp: {app.resume_score * 10}%
                                                </Badge>
                                            )}
                                            {app.aptitude_score !== null && app.aptitude_score !== undefined && (
                                                <Badge variant="outline" className="text-[9px] px-1.5 py-0 h-4 bg-purple-100 text-purple-700 border-purple-200">
                                                    Apt: {app.aptitude_score.toFixed(1)}
                                                </Badge>
                                            )}
                                            {app.behavioral_score !== null && app.behavioral_score !== undefined && (
                                                <Badge variant="outline" className="text-[9px] px-1.5 py-0 h-4 bg-green-100 text-green-700 border-green-200">
                                                    Behav: {app.behavioral_score.toFixed(1)}
                                                </Badge>
                                            )}
                                            {app.technical_skills_score !== null && app.technical_skills_score !== undefined && (
                                                <Badge variant="outline" className="text-[9px] px-1.5 py-0 h-4 bg-blue-100 text-blue-700 border-blue-200">
                                                    Tech: {app.technical_skills_score.toFixed(1)}
                                                </Badge>
                                            )}
                                        </div>

                                        {/* ─── FSM Action Buttons (inline on cards) ──── */}
                                        {getCardActions(column.id).length > 0 && (
                                            <div className="flex flex-wrap gap-1.5 mt-2" onClick={e => e.stopPropagation()}>
                                                {getCardActions(column.id).map(btn => (
                                                    <Button
                                                        key={btn.action}
                                                        variant={btn.variant === 'primary' ? 'default' : btn.variant === 'destructive' ? 'destructive' : 'outline'}
                                                        size="sm"
                                                        className={`h-6 px-2 text-[10px] font-bold uppercase tracking-wider ${
                                                            btn.variant === 'success' 
                                                                ? 'bg-emerald-600 hover:bg-emerald-700 text-white border-emerald-700' 
                                                                : btn.variant === 'secondary'
                                                                    ? 'bg-amber-500/10 text-amber-600 border-amber-500/30 hover:bg-amber-500/20'
                                                                    : ''
                                                        }`}
                                                        onClick={() => handleTransition(app.id, btn.action)}
                                                    >
                                                        {btn.label}
                                                    </Button>
                                                ))}
                                            </div>
                                        )}
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    </ScrollArea>
                    
                    {/* Pagination controls */}
                    {getColumnApplications(column.id).length > APPLICATIONS_PER_PAGE && (
                        <div className="flex justify-between items-center px-1 pt-2 shrink-0 border-t mt-1 border-border/40">
                            <Button 
                                variant="outline" 
                                size="sm" 
                                className="h-6 px-2 text-xs"
                                disabled={(pages[column.id] || 0) === 0}
                                onClick={() => setPages(p => ({ ...p, [column.id]: (p[column.id] || 0) - 1 }))}
                            >
                                &larr; Prev
                            </Button>
                            <span className="text-xs text-muted-foreground font-medium">
                                {(pages[column.id] || 0) + 1} / {Math.ceil(getColumnApplications(column.id).length / APPLICATIONS_PER_PAGE)}
                            </span>
                            <Button 
                                variant="outline" 
                                size="sm" 
                                className="h-6 px-2 text-xs"
                                disabled={((pages[column.id] || 0) + 1) * APPLICATIONS_PER_PAGE >= getColumnApplications(column.id).length}
                                onClick={() => setPages(p => ({ ...p, [column.id]: (p[column.id] || 0) + 1 }))}
                            >
                                Next &rarr;
                            </Button>
                        </div>
                    )}
                </div>
            ))}
        </div>
    )
}
