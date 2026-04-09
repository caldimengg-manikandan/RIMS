'use client'

import React, { useState } from 'react'
import useSWR from 'swr'
import { fetcher } from '@/app/dashboard/lib/swr-fetcher'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { 
    Users, 
    Send, 
    CheckCircle2, 
    Download, 
    RefreshCcw, 
    UserPlus,
    Calendar,
    Search as SearchIcon,
    FileText,
    ShieldAlert,
    Camera,
    ShieldCheck,
    CreditCard,
    AlertTriangle,
    Eye,
    RefreshCw
} from 'lucide-react'
import { SendOfferDialog } from '@/components/send-offer-dialog'
import { CapturePhotoDialog } from '@/components/capture-photo-dialog'
import { APIClient } from '@/app/dashboard/lib/api-client'
import { useToast } from "@/components/ui/use-toast"
import { Input } from "@/components/ui/input"
import { 
    Dialog, 
    DialogContent, 
    DialogHeader, 
    DialogTitle, 
    DialogDescription,
    DialogFooter
} from "@/components/ui/dialog"
import { useAuth } from '@/app/dashboard/lib/auth-context'
import { useRouter } from 'next/navigation'

export default function OnboardingPage() {
    const { user } = useAuth()
    const router = useRouter()
    const { toast } = useToast()
    const { data: candidates, isLoading, mutate } = useSWR<any[]>('/api/onboarding/candidates', fetcher)
    const [search, setSearch] = useState('')

    if (user && user.role !== 'hr' && user.role !== 'super_admin') {
        return (
            <div className="flex flex-col items-center justify-center p-20 gap-4 text-center">
                <ShieldAlert className="h-16 w-16 text-destructive opacity-20" />
                <h2 className="text-2xl font-black">Access Denied</h2>
                <p className="text-muted-foreground">This page is restricted to HR and Administrators only.</p>
                <Button onClick={() => router.push('/dashboard/hr')}>Return to Dashboard</Button>
            </div>
        )
    }

    const filteredCandidates = candidates?.filter(c => 
        c.candidate_name.toLowerCase().includes(search.toLowerCase()) ||
        c.candidate_email.toLowerCase().includes(search.toLowerCase())
    )

    const [approvingCandidate, setApprovingCandidate] = useState<any>(null)
    const [isApproveOpen, setIsApproveOpen] = useState(false)
    const [isCaptureOpen, setIsCaptureOpen] = useState(false)
    const [activeCaptureId, setActiveCaptureId] = useState<number | null>(null)

    const handleApprove = async (candidate: any) => {
        try {
            await APIClient.post(`/api/onboarding/applications/${candidate.id}/approve-offer`, {})
            toast({ title: "Approved", description: "Offer letter approved and sent to candidate" })
            mutate()
            setIsApproveOpen(false)
        } catch (error) {
            toast({ title: "Error", description: "Only Super Admin can approve offer letters", variant: "destructive" })
        }
    }

    const handleComplete = async (id: number) => {
        try {
            await APIClient.post(`/api/onboarding/applications/${id}/onboard`, {})
            toast({ title: "Completed", description: "Candidate marked as onboarded" })
            mutate()
        } catch (error) {
            toast({ title: "Error", description: "Failed to complete onboarding", variant: "destructive" })
        }
    }

    const handleGenerateID = async (id: number) => {
        try {
            const res = await APIClient.post(`/api/onboarding/applications/${id}/generate-id-card`, {}) as any
            toast({ title: "Success", description: `ID Card generated. Employee ID: ${res.employee_id}` })
            mutate()
        } catch (error) {
            toast({ title: "Error", description: "Failed to generate ID card", variant: "destructive" })
        }
    }

    const exportToCSV = () => {
        if (!candidates || candidates.length === 0) return
        
        const headers = ["Name,Email,Job,Status,Joining Date,Approval"]
        const rows = candidates.map(c => 
            `"${c.candidate_name}","${c.candidate_email}","${c.job?.title || ''}","${c.status}","${c.joining_date || ''}","${c.onboarding_approval_status}"`
        )
        
        const csvContent = "data:text/csv;charset=utf-8," + headers.concat(rows).join("\n")
        const encodedUri = encodeURI(csvContent)
        const link = document.createElement("a")
        link.setAttribute("href", encodedUri)
        link.setAttribute("download", "onboarding_candidates.csv")
        document.body.appendChild(link)
        link.click()
    }

    return (
        <div className="p-6 space-y-8 animate-in fade-in duration-700">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h1 className="text-3xl font-black tracking-tight flex items-center gap-3">
                        Onboarding Pipeline
                        <Badge variant="outline" className="h-6 bg-primary/5 text-primary border-primary/20">
                            {candidates?.length || 0} Candidates
                        </Badge>
                    </h1>
                    <p className="text-muted-foreground mt-1">Track and manage newly hired candidates</p>
                </div>
                <div className="flex items-center gap-3">
                    <Button variant="outline" className="gap-2" onClick={exportToCSV}>
                        <Download className="h-4 w-4" />
                        Export Data
                    </Button>
                    <Button className="gap-2" onClick={() => mutate()}>
                        <RefreshCcw className="h-4 w-4" />
                        Refresh
                    </Button>
                </div>
            </div>

            <Card className="border-border/50 shadow-sm overflow-hidden">
                <CardHeader className="bg-muted/30 border-b p-4">
                    <div className="flex items-center gap-4">
                        <div className="relative flex-1 max-w-sm">
                            <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                            <Input 
                                placeholder="Search candidates..." 
                                className="pl-10 h-9"
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                            />
                        </div>
                    </div>
                </CardHeader>
                <CardContent className="p-0">
                    <Table>
                        <TableHeader>
                            <TableRow className="bg-muted/20 hover:bg-muted/20">
                                <TableHead className="font-bold py-4">Candidate</TableHead>
                                <TableHead className="font-bold">Joining Date</TableHead>
                                <TableHead className="font-bold text-center">Approval</TableHead>
                                <TableHead className="font-bold text-center">Email Status</TableHead>
                                <TableHead className="font-bold text-center">Response</TableHead>
                                <TableHead className="font-bold text-right pr-6">Action</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {isLoading ? (
                                <TableRow>
                                    <TableCell colSpan={6} className="h-32 text-center">
                                        <div className="flex justify-center items-center gap-2">
                                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary"></div>
                                            Loading candidates...
                                        </div>
                                    </TableCell>
                                </TableRow>
                            ) : filteredCandidates?.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={6} className="h-32 text-center text-muted-foreground">
                                        No candidates found in onboarding phase.
                                    </TableCell>
                                </TableRow>
                            ) : (
                                filteredCandidates?.map((candidate) => (
                                    <TableRow key={candidate.id} className="hover:bg-primary/5 transition-colors group">
                                        <TableCell className="py-4">
                                            <div className="flex items-center gap-3">
                                                <Avatar className="h-9 w-9 shrink-0 border border-border">
                                                    <AvatarFallback className="bg-primary/10 text-primary font-bold text-xs uppercase">
                                                        {candidate.candidate_name[0]}
                                                    </AvatarFallback>
                                                </Avatar>
                                                <div>
                                                    <div className="font-bold text-sm text-foreground">{candidate.candidate_name}</div>
                                                    <Badge variant="outline" className="text-[10px] h-4 font-normal mt-1 opacity-70">
                                                        {candidate.job?.title || 'Unknown Role'}
                                                    </Badge>
                                                </div>
                                            </div>
                                        </TableCell>
                                        <TableCell>
                                            {candidate.joining_date ? (
                                                <div className="flex items-center gap-2 text-sm font-medium">
                                                    <Calendar className="h-3.5 w-3.5 text-primary opacity-60" />
                                                    {new Date(candidate.joining_date).toLocaleDateString()}
                                                </div>
                                            ) : (
                                                <span className="text-xs text-muted-foreground italic">Not Set</span>
                                            )}
                                        </TableCell>
                                        <TableCell className="text-center">
                                            <Badge 
                                                variant="outline"
                                                className={`text-[10px] uppercase font-bold tracking-tighter ${
                                                    candidate.offer_approval_status === 'approved' 
                                                        ? 'bg-emerald-50 text-emerald-600 border-emerald-200' 
                                                        : candidate.status === 'pending_approval'
                                                            ? 'bg-amber-50 text-amber-600 border-amber-200'
                                                            : 'bg-slate-50 text-slate-400'
                                                }`}
                                            >
                                                {candidate.offer_approval_status || 'pending'}
                                            </Badge>
                                        </TableCell>
                                        <TableCell className="text-center">
                                            {(() => {
                                                const isExpired = candidate.offer_token_expiry && new Date(candidate.offer_token_expiry) < new Date();
                                                if (isExpired && candidate.offer_response_status === 'pending') {
                                                    return <Badge variant="destructive" className="text-[10px] uppercase font-bold tracking-tighter bg-red-600">Expired</Badge>;
                                                }
                                                if (candidate.offer_email_status === 'sent') {
                                                    return <Badge className="bg-blue-500 text-[10px] uppercase font-bold tracking-tighter">Sent</Badge>;
                                                }
                                                if (candidate.offer_email_status === 'failed') {
                                                    return (
                                                        <div className="flex flex-col items-center gap-1">
                                                            <Badge variant="destructive" className="text-[10px] uppercase font-bold tracking-tighter">Failed</Badge>
                                                            {candidate.offer_email_retry_count > 0 && (
                                                                <span className="text-[9px] text-amber-600 font-bold uppercase">Retry #{candidate.offer_email_retry_count}</span>
                                                            )}
                                                        </div>
                                                    );
                                                }
                                                return <span className="text-[10px] text-muted-foreground">-</span>;
                                            })()}
                                        </TableCell>
                                        <TableCell className="text-center">
                                            <div className="flex flex-col items-center gap-1">
                                                <Badge 
                                                    variant="outline"
                                                    className={`text-[10px] uppercase font-bold tracking-tighter ${
                                                        candidate.offer_response_status === 'accepted' 
                                                            ? 'bg-emerald-500 text-white border-none' 
                                                            : candidate.offer_response_status === 'rejected'
                                                                ? 'bg-destructive text-white border-none'
                                                                : 'bg-slate-100 text-slate-400'
                                                    }`}
                                                >
                                                    {candidate.offer_response_status || 'pending'}
                                                </Badge>
                                                {candidate.offer_token_used && candidate.offer_response_status !== 'pending' && (
                                                    <span className="text-[9px] text-emerald-600 font-bold uppercase">Response Verified</span>
                                                )}
                                            </div>
                                        </TableCell>
                                        <TableCell className="text-right pr-6">
                                            <div className="flex items-center justify-end gap-2">
                                                {candidate.status === 'hired' && (
                                                    <SendOfferDialog 
                                                        applicationId={candidate.id}
                                                        candidateName={candidate.candidate_name}
                                                        onSuccess={() => mutate()}
                                                        trigger={
                                                            <Button size="sm" variant="outline" className="h-8 gap-1.5 text-xs border-primary text-primary hover:bg-primary/10">
                                                                <Send className="h-3.5 w-3.5" />
                                                                Request Offer
                                                            </Button>
                                                        }
                                                    />
                                                )}
                                                {candidate.status === 'pending_approval' && user?.role === 'super_admin' && (
                                                    <Button 
                                                        size="sm" 
                                                        variant="outline" 
                                                        className="h-8 gap-1.5 text-xs text-amber-600 border-amber-500 hover:bg-amber-50"
                                                        onClick={() => {
                                                            setApprovingCandidate(candidate)
                                                            setIsApproveOpen(true)
                                                        }}
                                                    >
                                                        <ShieldAlert className="h-3.5 w-3.5" />
                                                        Approve Offer
                                                    </Button>
                                                )}
                                                {candidate.status === 'accepted' && (
                                                    <Button 
                                                        size="sm" 
                                                        className="h-8 gap-1.5 text-xs bg-emerald-600 hover:bg-emerald-700"
                                                        onClick={() => handleComplete(candidate.id)}
                                                    >
                                                        <UserPlus className="h-3.5 w-3.5" />
                                                        Finalize Join
                                                    </Button>
                                                )}
                                                {candidate.status === 'onboarded' && (
                                                    <div className="flex items-center gap-2">
                                                        {!candidate.photo_url ? (
                                                            <Button 
                                                                size="sm" 
                                                                variant="outline" 
                                                                className="h-8 gap-1.5 text-xs text-blue-600 border-blue-500 hover:bg-blue-50"
                                                                onClick={() => {
                                                                    setActiveCaptureId(candidate.id)
                                                                    setIsCaptureOpen(true)
                                                                }}
                                                            >
                                                                <Camera className="h-3.5 w-3.5" />
                                                                Capture Photo
                                                            </Button>
                                                        ) : !candidate.id_card_url ? (
                                                            <Button size="sm" variant="outline" className="h-8 gap-1.5 text-xs text-amber-600 border-amber-500 hover:bg-amber-50" onClick={() => handleGenerateID(candidate.id)}>
                                                                <CreditCard className="h-3.5 w-3.5" />
                                                                Generate ID
                                                            </Button>
                                                        ) : (
                                                            <Button size="sm" variant="outline" className="h-8 gap-1.5 text-xs text-emerald-600 border-emerald-500 hover:bg-emerald-50" onClick={() => window.open(`${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:10000'}/${candidate.id_card_url}`, '_blank')}>
                                                                <Download className="h-3.5 w-3.5" />
                                                                Download ID
                                                            </Button>
                                                        )}
                                                        <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200">
                                                            Onboarded
                                                        </Badge>
                                                    </div>
                                                )}
                                            </div>
                                        </TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <Card className="border-border/50 bg-gradient-to-br from-blue-500/5 to-primary/5">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-bold flex items-center gap-2">
                            <FileText className="h-4 w-4 text-blue-500" />
                            Pending Offers
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-black">{candidates?.filter(c => !c.offer_sent).length || 0}</div>
                        <p className="text-xs text-muted-foreground">Action required: send letters</p>
                    </CardContent>
                </Card>
                <Card className="border-border/50 bg-gradient-to-br from-amber-500/5 to-amber-600/5">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-bold flex items-center gap-2">
                            <Calendar className="h-4 w-4 text-amber-500" />
                            Upcoming Joinings (7d)
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-black">
                            {candidates?.filter(c => {
                                if (!c.joining_date) return false
                                const jDate = new Date(c.joining_date)
                                const now = new Date()
                                const diff = jDate.getTime() - now.getTime()
                                return diff > 0 && diff < 7 * 24 * 60 * 60 * 1000
                            }).length || 0}
                        </div>
                        <p className="text-xs text-muted-foreground">Reminders sent automatically</p>
                    </CardContent>
                </Card>
                <Card className="border-border/50 bg-gradient-to-br from-emerald-500/5 to-emerald-600/5">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-bold flex items-center gap-2">
                            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                            Onboarded This Month
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-black">
                            {candidates?.filter(c => c.status === 'onboarded').length || 0}
                        </div>
                        <p className="text-xs text-muted-foreground">Successfully closed hires</p>
                    </CardContent>
                </Card>
            </div>

            {activeCaptureId && (
                <CapturePhotoDialog 
                    isOpen={isCaptureOpen}
                    onOpenChange={setIsCaptureOpen}
                    applicationId={activeCaptureId}
                    onSuccess={() => mutate()}
                />
            )}
        </div>
    )
}
