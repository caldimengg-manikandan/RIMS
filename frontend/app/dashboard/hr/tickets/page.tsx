'use client'

import React, { useState, useEffect } from 'react'
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
    Send
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
import { Textarea } from "@/components/ui/textarea"
import { toast } from "sonner"

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

import useSWR from 'swr'
import { performMutation } from '@/app/dashboard/lib/swr-utils'

export default function HRTicketsPage() {
    const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(null)
    const [hrResponse, setHrResponse] = useState('')
    const [isResolving, setIsResolving] = useState(false)
    const [filter, setFilter] = useState<'pending' | 'all'>('pending')
    const [sendEmail, setSendEmail] = useState(true)

    const { data: tickets = [], isLoading, mutate } = useSWR<Ticket[]>(
        `/api/tickets?status=${filter}`
    )


    const handleResolve = async (ticketId: number, action: 'reissue_key' | 'resolve' | 'dismissed' | 'reply') => {
        if (!hrResponse.trim() && action !== 'dismissed') {
            toast.error("Please provide a response for the candidate")
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
            await performMutation<Ticket[]>(
                `/api/tickets?status=${filter}`,
                mutate,
                actionFn,
                {
                    lockKey: `ticket-${ticketId}`,
                    optimisticData: (current) => 
                        filter === 'pending' 
                            ? (current || []).filter(t => t.id !== ticketId)
                            : (current || []).map(t => t.id === ticketId ? {
                                ...t,
                                status: (action === 'dismissed' ? 'dismissed' : action === 'reply' ? 'pending' : 'resolved') as const,
                                hr_response: hrResponse || t.hr_response,
                            } : t),
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
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-4xl font-black text-foreground tracking-tight flex items-center gap-3">
                        <LifeBuoy className="h-10 w-10 text-primary" />
                        Support Tickets
                    </h1>
                    <p className="text-muted-foreground mt-2">Manage candidate issues and interruption reports.</p>
                </div>
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
                </div>
            </div>

            {isLoading ? (
                <div className="flex justify-center py-20">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
                </div>
            ) : tickets.length === 0 ? (
                <Card className="border-dashed py-20 bg-card/50">
                    <CardContent className="flex flex-col items-center justify-center text-center space-y-4">
                        <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center">
                            <CheckCircle2 className="h-8 w-8 text-primary" />
                        </div>
                        <div className="space-y-1">
                            <h3 className="text-xl font-bold">All clear!</h3>
                            <p className="text-muted-foreground">No pending support tickets at the moment.</p>
                        </div>
                    </CardContent>
                </Card>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {tickets.map((ticket) => (
                        <Card
                            key={ticket.id}
                            className="group hover:shadow-xl transition-all duration-300 border-border hover:border-primary/50 cursor-pointer overflow-hidden flex flex-col"
                            onClick={() => setSelectedTicket(ticket)}
                        >
                            <div className="h-1.5 w-full bg-gradient-to-r from-primary/50 to-primary group-hover:from-primary group-hover:to-accent transition-all"></div>
                            <CardHeader className="pb-3">
                                <div className="flex justify-between items-start">
                                    <Badge variant="outline" className={`capitalize font-bold ${getIssueTypeBadge(ticket.issue_type)}`}>
                                        {ticket.issue_type.replace('_', ' ')}
                                    </Badge>
                                    <span className="text-[10px] text-muted-foreground flex items-center gap-1 font-medium">
                                        <Clock className="h-3 w-3" />
                                        {new Date(ticket.created_at).toLocaleDateString()}
                                    </span>
                                </div>
                                <CardTitle className="text-xl mt-3 line-clamp-1">{ticket.candidate_name}</CardTitle>
                                <CardDescription className="flex items-center gap-1.5">
                                    <Mail className="h-3 w-3" />
                                    {ticket.candidate_email}
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="flex-1">
                                <p className="text-sm text-muted-foreground line-clamp-3 leading-relaxed">
                                    "{ticket.description}"
                                </p>
                            </CardContent>
                            <Separator />



                            <div className="p-4 bg-muted/30 flex justify-between items-center">
                                <div className="flex items-center gap-2">
                                    {ticket.status === 'pending' ? (
                                        <Badge variant="secondary" className="bg-amber-100 text-amber-700 animate-pulse border-amber-200">Pending</Badge>
                                    ) : (
                                        <Badge variant="secondary" className="bg-green-100 text-green-700 border-green-200">Resolved</Badge>
                                    )}
                                </div>
                                <Button variant="ghost" size="sm" className="text-xs font-bold hover:text-primary transition-colors">
                                    VIEW DETAILS →
                                </Button>
                            </div>
                        </Card>
                    ))}
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
                                        <Label className="text-[10px] uppercase tracking-widest text-muted-foreground font-black">Candidate</Label>
                                        <div className="flex items-center gap-2 font-bold text-lg truncate">
                                            <User className="h-5 w-5 text-primary flex-shrink-0" />
                                            <span className="truncate">{selectedTicket.candidate_name}</span>
                                        </div>
                                        <div className="text-xs text-muted-foreground flex items-center gap-1.5 mt-1 overflow-hidden">
                                            <Badge variant="secondary" className="px-1.5 py-0 text-[10px] font-bold flex-shrink-0">CANDIDATE ID: {selectedTicket.test_id || 'N/A'}</Badge>
                                            <span className="flex items-center gap-1 truncate">
                                                <Mail className="h-3 w-3 flex-shrink-0" />
                                                <span className="truncate">{selectedTicket.candidate_email}</span>
                                            </span>
                                        </div>
                                    </div>
                                    <div className="space-y-1 min-w-0">
                                        <Label className="text-[10px] uppercase tracking-widest text-muted-foreground font-black">Position & Timing</Label>
                                        <div className="flex items-center gap-2 font-bold text-lg text-foreground truncate">
                                            <Link href={`/dashboard/hr/jobs/${selectedTicket.job_id}`} className="max-w-full">
                                                <Badge variant="outline" className="border-primary/30 text-primary hover:bg-primary/5 transition-colors cursor-pointer font-black px-2 py-0.5 truncate max-w-full">JOB ID: {selectedTicket.job_identifier || 'N/A'}</Badge>
                                            </Link>
                                        </div>
                                        <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-medium mt-1 truncate">
                                            <Clock className="h-3.5 w-3.5 text-primary/70 flex-shrink-0" />
                                            {new Date(selectedTicket.created_at).toLocaleString()}
                                        </div>
                                    </div>
                                </div>

                                <div className="space-y-3 min-w-0">
                                    <Label className="text-[10px] uppercase tracking-widest text-muted-foreground font-black flex items-center gap-2">
                                        <AlertCircle className="h-3 w-3 text-destructive" />
                                        Issue Description
                                    </Label>
                                    <div className="p-5 bg-card rounded-2xl border-2 border-border/50 italic text-foreground leading-relaxed shadow-sm max-w-full overflow-hidden break-words">
                                        "{selectedTicket.description}"
                                    </div>
                                </div>

                                {selectedTicket.status === 'pending' ? (
                                    <div className="space-y-4 min-w-0">
                                        <Separator />
                                        <div className="space-y-2">
                                            <Label className="text-sm font-bold flex items-center gap-2">
                                                <MessageSquare className="h-4 w-4 text-primary" />
                                                Your Response
                                            </Label>
                                            <Textarea
                                                placeholder="Explain the resolution or why the appeal was rejected..."
                                                className="min-h-[120px] rounded-xl border-2 focus:ring-primary/20 transition-all font-medium w-full"
                                                value={hrResponse}
                                                onChange={(e) => setHrResponse(e.target.value)}
                                            />
                                            <p className="text-[10px] text-muted-foreground italic">This response will be sent to the candidate's email.</p>
                                        </div>

                                        <div className="flex items-center space-x-2 bg-primary/5 p-3 rounded-xl border border-primary/10">
                                            <Switch
                                                id="send-email"
                                                checked={sendEmail}
                                                onCheckedChange={setSendEmail}
                                            />
                                            <Label htmlFor="send-email" className="text-xs font-bold text-primary cursor-pointer leading-none">
                                                Send email notification to candidate
                                            </Label>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="space-y-4 min-w-0">
                                        <Separator />
                                        <div className="space-y-2">
                                            <Label className="text-[10px] uppercase tracking-widest text-muted-foreground font-black">HR Response</Label>
                                            <div className="p-4 bg-primary/5 rounded-xl border border-primary/20 text-primary font-medium break-words">
                                                {selectedTicket.hr_response}
                                            </div>
                                            <div className="flex flex-wrap justify-between items-center gap-2 mt-2">
                                                <span className="text-xs text-muted-foreground flex items-center gap-1">
                                                    <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
                                                    Resolved {selectedTicket.resolved_at ? new Date(selectedTicket.resolved_at).toLocaleDateString() : ''}
                                                </span>
                                                {selectedTicket.is_reissue_granted && (
                                                    <Badge className="bg-primary text-primary-foreground font-bold">Key Re-issued</Badge>
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
