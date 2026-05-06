'use client'

import React, { useState, useEffect } from 'react'
import useSWR from 'swr'
import { performMutation } from '@/app/dashboard/lib/swr-utils'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Label } from "@/components/ui/label"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import {
    LifeBuoy,
    Clock,
    User,
    Mail,
    AlertCircle,
    CheckCircle2,
    XCircle,
    RotateCcw,
    MessageSquare,
    Send,
    Star
} from 'lucide-react'
import { Switch } from "@/components/ui/switch"
import Link from 'next/link'
import { APIClient } from '@/app/dashboard/lib/api-client'
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog"
import { PageHeader } from '@/components/page-header'
import { Textarea } from "@/components/ui/textarea"
import { toast } from "sonner"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"

interface Ticket {
    id: number
    interview_id: number
    application_id: number | null
    test_id: string | null
    job_id: number | null
    job_identifier: string | null
    candidate_name: string
    candidate_email: string
    issue_type: string
    description: string
    status: 'pending' | 'resolved' | 'dismissed'
    hr_response: string | null
    is_reissue_granted: boolean
    created_at: string
    resolved_at: string | null
}

interface Feedback {
    id: number
    interview_id: number
    candidate_name: string
    candidate_email: string
    job_title: string
    job_id: number | null
    ui_ux_rating: number
    feedback_text: string | null
    created_at: string
}


export default function HRTicketsPage() {
    const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(null)
    const [hrResponse, setHrResponse] = useState('')
    const [isResolving, setIsResolving] = useState(false)
    const [filter, setFilter] = useState<'pending' | 'all' | 'feedback'>('pending')
    const [sendEmail, setSendEmail] = useState(true)

    const endpoint = filter === 'feedback' ? '/api/tickets/feedback' : `/api/tickets?status=${filter}`
    const { data: resp, isLoading, mutate } = useSWR<any>(endpoint)
    
    const tickets = (filter === 'feedback' ? [] : (resp?.items || [])) as Ticket[]
    const feedbacks = (filter === 'feedback' ? (resp?.items || []) : []) as Feedback[]



    const handleResolve = async (ticketId: number, action: 'reissue_key' | 'resolve' | 'dismissed' | 'reply') => {
        // 'dismissed' action doesn't require a response; all others do
        if (!hrResponse.trim() && action !== 'dismissed') {
            toast.error("Please provide a response message for the candidate before taking this action.")
            return
        }

        const actionFn = () => APIClient.put(`/api/tickets/${ticketId}/resolve`, {
            hr_response: hrResponse,
            action: action,
            send_email: sendEmail
        })

        let successMsg = "Ticket resolved";
        if (action === 'reissue_key') successMsg = "Key re-issued and ticket resolved";
        else if (action === 'reply') successMsg = "Reply sent to candidate";

        setIsResolving(true)
        try {
            await performMutation<any>(
                `/api/tickets?status=${filter}`,
                mutate,
                actionFn,
                {
                    lockKey: `ticket-${ticketId}`,
                    optimisticData: (current) => {
                        const defaultResp = { items: [], total: 0 };
                        const data = current || defaultResp;
                        
                        if (filter === 'pending') {
                            const newItems = data.items.filter((t: Ticket) => t.id !== ticketId);
                            return { ...data, items: newItems, total: data.total - (data.items.length - newItems.length) };
                        } else {
                            return {
                                ...data,
                                items: data.items.map((t: Ticket) => t.id === ticketId ? {
                                    ...t,
                                    status: (action === 'dismissed' ? 'dismissed' : action === 'reply' ? 'pending' : 'resolved') as Ticket['status'],
                                    hr_response: hrResponse || t.hr_response,
                                } : t)
                            };
                        }
                    },
                    successMessage: successMsg,
                    invalidateKeys: ['/api/analytics/dashboard']
                }
            )
            setSelectedTicket(null)
            setHrResponse('')
        } finally {
            setIsResolving(false)
        }
    }

    const getIssueTypeBadge = (type: string) => {
        switch (type) {
            case 'interruption': return 'bg-amber-100 text-amber-700 border-amber-200'
            case 'technical': return 'bg-blue-100 text-blue-700 border-blue-200'
            case 'misconduct_appeal': return 'bg-purple-100 text-purple-700 border-purple-200'
            default: return 'bg-slate-100 text-slate-700'
        }
    }

    return (
        <div className="w-full max-w-[1600px] mx-auto space-y-8 animate-in fade-in duration-700">
            <PageHeader
                title="Support Tickets"
                description="Manage candidate issues and interruption reports."
                icon={LifeBuoy}
            >
                <div className="flex bg-muted p-1 rounded-xl border border-border/50">
                    <Button
                        variant={filter === 'pending' ? 'default' : 'ghost'}
                        size="sm"
                        onClick={() => setFilter('pending')}
                        className="rounded-lg font-bold"
                    >
                        Pending
                    </Button>
                    <Button
                        variant={filter === 'all' ? 'default' : 'ghost'}
                        size="sm"
                        onClick={() => setFilter('all')}
                        className="rounded-lg font-bold"
                    >
                        All History
                    </Button>
                    <Button
                        variant={filter === 'feedback' ? 'default' : 'ghost'}
                        size="sm"
                        onClick={() => setFilter('feedback')}
                        className="rounded-lg font-bold"
                    >
                        Feedback
                    </Button>
                </div>
            </PageHeader>

            {isLoading ? (
                <div className="flex justify-center py-20">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
                </div>
            ) : (filter !== 'feedback' && tickets.length === 0) || (filter === 'feedback' && feedbacks.length === 0) ? (
                <Card className="border-dashed py-20 bg-card/50">
                    <CardContent className="flex flex-col items-center justify-center text-center space-y-4">
                        <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center">
                            <CheckCircle2 className="h-8 w-8 text-primary" />
                        </div>
                        <div className="space-y-1">
                            <h3 className="text-xl font-bold">All clear!</h3>
                            <p className="text-muted-foreground">{filter === 'feedback' ? 'No candidate feedback available.' : 'No pending support tickets at the moment.'}</p>
                        </div>
                    </CardContent>
                </Card>
            ) : filter === 'feedback' ? (
                <div className="bg-card rounded-2xl border border-border overflow-hidden shadow-sm">
                    {/* List Header */}
                    <div className="grid grid-cols-12 gap-4 px-6 py-3 bg-muted/50 border-b border-border text-xs uppercase tracking-widest font-black text-muted-foreground">
                        <div className="col-span-2">Rating</div>
                        <div className="col-span-3">Candidate</div>
                        <div className="col-span-3">Position</div>
                        <div className="col-span-3">Feedback</div>
                        <div className="col-span-1 text-right">Date</div>
                    </div>
                    <div className="divide-y divide-border/50">
                        {feedbacks.map((fb) => (
                            <Tooltip key={fb.id}>
                                <TooltipTrigger asChild>
                                    <div className="grid grid-cols-12 gap-4 px-6 py-4 items-center hover:bg-muted/30 transition-colors group cursor-pointer relative">
                                        <div className="col-span-2 flex gap-0.5">
                                            {[1, 2, 3, 4, 5].map(star => (
                                                <Star key={star} className={`h-4 w-4 ${star <= fb.ui_ux_rating ? 'fill-amber-400 text-amber-400' : 'text-muted-foreground/20'}`} />
                                            ))}
                                        </div>
                                        <div className="col-span-3 min-w-0">
                                            <div className="font-bold text-base truncate">{fb.candidate_name}</div>
                                            <div className="text-sm text-muted-foreground truncate">{fb.candidate_email}</div>
                                        </div>
                                        <div className="col-span-3 text-sm font-semibold text-primary/80 truncate">
                                            {fb.job_title}
                                        </div>
                                        <div className="col-span-3">
                                            <p className="text-sm text-muted-foreground italic line-clamp-1">
                                                {fb.feedback_text ? `"${fb.feedback_text}"` : "No specific comments"}
                                            </p>
                                        </div>
                                        <div className="col-span-1 text-right text-xs font-medium text-muted-foreground">
                                            {fb.created_at ? new Date(fb.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : 'N/A'}
                                        </div>
                                    </div>
                                </TooltipTrigger>
                                <TooltipContent>
                                    Click to expand feedback
                                </TooltipContent>
                            </Tooltip>
                        ))}
                    </div>
                </div>
            ) : (
                <div className="bg-card rounded-2xl border border-border overflow-hidden shadow-sm">
                    {/* List Header */}
                    <div className="grid grid-cols-12 gap-4 px-0 py-3 bg-muted/50 border-b border-border text-xs uppercase tracking-widest font-black text-muted-foreground">
                        <div className="col-span-1 text-center">ID</div>
                        <div className="col-span-2">Type</div>
                        <div className="col-span-3">Candidate</div>
                        <div className="col-span-4">Issue Description</div>
                        <div className="col-span-1 text-center">Date</div>
                    </div>
                    <div className="divide-y divide-border/50">
                        {tickets.map((ticket) => (
                            <Tooltip key={ticket.id}>
                                <TooltipTrigger asChild>
                                    <div 
                                        onClick={() => setSelectedTicket(ticket)}
                                        className="grid grid-cols-12 gap-4 px-0 py-4 items-center hover:bg-muted/30 transition-all cursor-pointer group"
                                    >
                                        <div className="col-span-1 flex justify-center">
                                            {ticket.id}
                                        </div>
                                        <div className="col-span-2">
                                            <Badge variant="outline" className={`text-xs font-black uppercase px-2 py-0 border-none ${getIssueTypeBadge(ticket.issue_type)}`}>
                                                {ticket.issue_type.replace('_', ' ')}
                                            </Badge>
                                        </div>
                                        <div className="col-span-3 min-w-0">
                                            <div className="font-bold text-base truncate">{ticket.candidate_name}</div>
                                            <div className="text-sm text-muted-foreground truncate">{ticket.candidate_email}</div>
                                        </div>
                                        <div className="col-span-4">
                                            <p className="text-sm text-muted-foreground line-clamp-1 pr-4">
                                                "{ticket.description}"
                                            </p>
                                        </div>
                                        <div className="col-span-1 text-center text-xs font-medium text-muted-foreground">
                                            {new Date(ticket.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                                        </div>
                                    </div>
                                </TooltipTrigger>
                                <TooltipContent>
                                    Click to open ticket
                                </TooltipContent>
                            </Tooltip>
                        ))}
                    </div>
                </div>
            )}

            {/* Resolution Dialog */}
            <Dialog open={!!selectedTicket} onOpenChange={(open) => !open && setSelectedTicket(null)}>
                <DialogContent className="max-w-5xl w-[95vw] sm:w-[90vw] bg-card border-border shadow-2xl p-0 overflow-hidden">
                    <DialogHeader className="p-6 pb-0">
                        <DialogTitle className="text-2xl font-black tracking-tight flex items-center gap-2">
                            Ticket Details
                            {selectedTicket && (
                                <Badge variant="outline" className={`capitalize ${getIssueTypeBadge(selectedTicket.issue_type)}`}>
                                    {selectedTicket.issue_type.replace('_', ' ')}
                                </Badge>
                            )}
                        </DialogTitle>
                        <DialogDescription>
                            Review the candidate's reported issue and take necessary action.
                        </DialogDescription>
                    </DialogHeader>

                    {selectedTicket && (
                        <>
                            <div className="space-y-6 px-6 py-4 max-h-[70vh] overflow-y-auto min-w-0">
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-muted/50 p-6 rounded-2xl border border-border/50">
                                    <div className="space-y-1 min-w-0">
                                        <Label className="text-xs uppercase tracking-widest text-muted-foreground font-black">Candidate</Label>
                                        <div className="flex items-center gap-2 font-bold text-xl truncate">
                                            <User className="h-6 w-6 text-primary flex-shrink-0" />
                                            <span className="truncate">{selectedTicket.candidate_name}</span>
                                        </div>
                                        <div className="text-sm text-muted-foreground flex items-center gap-2 mt-1 overflow-hidden">
                                            <Badge variant="secondary" className="px-2 py-0.5 text-xs font-bold flex-shrink-0">CANDIDATE ID: {selectedTicket.test_id || 'N/A'}</Badge>
                                            <span className="flex items-center gap-1.5 truncate">
                                                <Mail className="h-4 w-4 flex-shrink-0" />
                                                <span className="truncate">{selectedTicket.candidate_email}</span>
                                            </span>
                                        </div>
                                    </div>
                                    <div className="space-y-1 min-w-0">
                                        <Label className="text-xs uppercase tracking-widest text-muted-foreground font-black">Position & Timing</Label>
                                        <div className="flex items-center gap-2 font-bold text-xl text-foreground truncate">
                                            {selectedTicket.job_id ? (
                                                <Link href={`/dashboard/hr/jobs/${selectedTicket.job_id}`}>
                                                    <Badge variant="outline" className="border-primary/30 text-primary hover:bg-primary/5 transition-colors cursor-pointer font-black px-3 py-1 truncate max-w-full text-sm">
                                                        JOB ID: {selectedTicket.job_identifier || selectedTicket.job_id}
                                                    </Badge>
                                                </Link>
                                            ) : (
                                                <Badge variant="outline" className="border-muted text-muted-foreground font-black px-3 py-1 text-sm">
                                                    JOB ID: N/A
                                                </Badge>
                                            )}
                                        </div>
                                        <div className="flex items-center gap-1.5 text-sm text-muted-foreground font-medium mt-1 truncate">
                                            <Clock className="h-4 w-4 text-primary/70 flex-shrink-0" />
                                            {new Date(selectedTicket.created_at).toLocaleString()}
                                        </div>
                                    </div>
                                </div>

                                <div className="space-y-3 min-w-0">
                                    <Label className="text-xs uppercase tracking-widest text-muted-foreground font-black flex items-center gap-2">
                                        <AlertCircle className="h-4 w-4 text-destructive" />
                                        Issue Description
                                    </Label>
                                    <div className="p-6 bg-card rounded-2xl border-2 border-border/50 italic text-foreground text-base leading-relaxed shadow-sm max-w-full overflow-hidden break-words">
                                        "{selectedTicket.description}"
                                    </div>
                                </div>

                                {selectedTicket.status === 'pending' ? (
                                    <div className="space-y-4 min-w-0">
                                        <Separator />
                                        <div className="space-y-2">
                                            <Label className="text-base font-bold flex items-center gap-2">
                                                <MessageSquare className="h-5 w-5 text-primary" />
                                                Your Response
                                            </Label>
                                            <Textarea
                                                placeholder="Explain the resolution or why the appeal was rejected..."
                                                className="min-h-[140px] rounded-xl border-2 focus:ring-primary/20 transition-all font-medium w-full text-base"
                                                value={hrResponse}
                                                onChange={(e) => setHrResponse(e.target.value)}
                                            />
                                            <p className="text-xs text-muted-foreground italic">This response will be sent to the candidate's email.</p>
                                        </div>

                                        <div className="flex items-center space-x-2 bg-primary/5 p-3 rounded-xl border border-primary/10">
                                            <Switch
                                                id="send-email"
                                                checked={sendEmail}
                                                onCheckedChange={setSendEmail}
                                            />
                                            <Label htmlFor="send-email" className="text-sm font-bold text-primary cursor-pointer leading-none">
                                                Send email notification to candidate
                                            </Label>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="space-y-4 min-w-0">
                                        <Separator />
                                        <div className="space-y-2">
                                            <Label className="text-xs uppercase tracking-widest text-muted-foreground font-black">HR Response</Label>
                                            <div className="p-5 bg-primary/5 rounded-xl border border-primary/20 text-primary text-base font-medium break-words">
                                                {selectedTicket.hr_response}
                                            </div>
                                            <div className="flex flex-wrap justify-between items-center gap-2 mt-2">
                                                <span className="text-sm text-muted-foreground flex items-center gap-1.5">
                                                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                                                    Resolved {selectedTicket.resolved_at ? new Date(selectedTicket.resolved_at).toLocaleDateString() : ''}
                                                </span>
                                                {selectedTicket.is_reissue_granted && (
                                                    <Badge className="bg-primary text-primary-foreground font-bold px-3 py-1">Key Re-issued</Badge>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </div>
                            <DialogFooter className="flex flex-col sm:flex-row gap-3 p-6 border-t bg-muted/20">
                                {selectedTicket.status === 'pending' ? (
                                    <div className="flex flex-wrap gap-3 w-full justify-end">
                                        <Button
                                            className="font-bold bg-primary hover:bg-primary/90 shadow-lg shadow-primary/20 rounded-xl h-12 px-8 text-white flex-1 sm:flex-none"
                                            onClick={() => handleResolve(selectedTicket.id, 'reply')}
                                            disabled={isResolving}
                                        >
                                            <Send className="h-4 w-4 mr-2" />
                                            Send Reply
                                        </Button>
                                        <Button
                                            variant="outline"
                                            className="font-bold border-2 hover:bg-destructive/10 hover:text-destructive hover:border-destructive/20 rounded-xl h-12 px-6 flex-1 sm:flex-none"
                                            onClick={() => handleResolve(selectedTicket.id, 'dismissed')}
                                            disabled={isResolving}
                                        >
                                            <XCircle className="h-4 w-4 mr-2" />
                                            Dismiss
                                        </Button>
                                        <Button
                                            variant="outline"
                                            className="font-bold border-2 border-primary/20 hover:border-primary text-primary rounded-xl h-12 px-6 flex-1 sm:flex-none"
                                            onClick={() => handleResolve(selectedTicket.id, 'resolve')}
                                            disabled={isResolving}
                                        >
                                            <CheckCircle2 className="h-4 w-4 mr-2" />
                                            Resolve Only
                                        </Button>
                                        <Button
                                            className="font-bold bg-primary hover:bg-primary/90 shadow-lg shadow-primary/20 rounded-xl h-12 px-8 text-white flex-1 sm:flex-none"
                                            onClick={() => handleResolve(selectedTicket.id, 'reissue_key')}
                                            disabled={isResolving}
                                        >
                                            <RotateCcw className="h-4 w-4 mr-2" />
                                            Re-issue Key & Resolve
                                        </Button>
                                    </div>
                                ) : (
                                    <Button onClick={() => setSelectedTicket(null)} className="w-full font-bold h-12 rounded-xl">Close</Button>
                                )}
                            </DialogFooter>
                        </>
                    )}
                </DialogContent>
            </Dialog>
        </div>
    )
}
