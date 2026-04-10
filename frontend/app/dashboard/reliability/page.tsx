'use client'

import React from 'react'
import useSWR from 'swr'
import { fetcher } from '@/app/dashboard/lib/swr-fetcher'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { APIClient } from '@/app/dashboard/lib/api-client'
import { toast } from "sonner"
import { 
    AlertTriangle, 
    RefreshCw, 
    ShieldAlert, 
    Activity, 
    Clock, 
    CheckCircle2 
} from 'lucide-react'
import { useAuth } from '@/app/dashboard/lib/auth-context'
import { useRouter } from 'next/navigation'

export default function ReliabilityPage() {
    const { user } = useAuth()
    const router = useRouter()
    const { data: failures, isLoading, mutate } = useSWR<any[]>('/api/applications/failures', fetcher)

    if (user && user.role !== 'super_admin') {
        return (
            <div className="flex flex-col items-center justify-center p-20 gap-4 text-center">
                <ShieldAlert className="h-16 w-16 text-destructive opacity-20" />
                <h2 className="text-2xl font-black">Access Denied</h2>
                <p className="text-muted-foreground">This page is restricted to Super Administrators only.</p>
                <Button onClick={() => router.push('/dashboard/hr')}>Return to Dashboard</Button>
            </div>
        )
    }

    const handleRetry = async (id: number) => {
        try {
            await APIClient.post(`/api/applications/retry-resume-parsing`, { application_id: id })
            toast.success("Retry Triggered", { description: "Background process restarted." })
            mutate()
        } catch (error) {
            toast.error("Failed to trigger retry")
        }
    }

    return (
        <div className="p-6 space-y-8 animate-in fade-in duration-700">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h1 className="text-3xl font-black tracking-tight flex items-center gap-3">
                        Reliability Monitoring
                        <Badge variant="outline" className="h-6 bg-destructive/5 text-destructive border-destructive/20 uppercase tracking-widest text-[10px]">
                            {failures?.length || 0} Critical Issues
                        </Badge>
                    </h1>
                    <p className="text-muted-foreground mt-1">System failures requiring administrator attention</p>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <Card className="border-border/50 bg-gradient-to-br from-destructive/5 to-red-500/5">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-bold flex items-center gap-2">
                            <Activity className="h-4 w-4 text-destructive" />
                            Active Failures
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-black">{failures?.length || 0}</div>
                        <p className="text-xs text-muted-foreground">Resume parsing errors</p>
                    </CardContent>
                </Card>
                <Card className="border-border/50">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-bold flex items-center gap-2">
                            <Clock className="h-4 w-4 text-amber-500" />
                            Avg. Recovery Time
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-black">12.4m</div>
                        <p className="text-xs text-muted-foreground">From failure to manual retry</p>
                    </CardContent>
                </Card>
                <Card className="border-border/50 bg-gradient-to-br from-emerald-500/5 to-primary/5">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-bold flex items-center gap-2">
                            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                            Success Rate
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-black">98.2%</div>
                        <p className="text-xs text-muted-foreground">Parsing pipeline health</p>
                    </CardContent>
                </Card>
            </div>

            <Card className="border-destructive/20 bg-destructive/5 overflow-hidden">
                <CardHeader className="bg-destructive/10 border-b flex flex-row items-center justify-between py-3">
                    <div className="flex items-center gap-2">
                        <AlertTriangle className="h-5 w-5 text-destructive" />
                        <div>
                            <CardTitle className="text-sm font-black text-destructive uppercase tracking-widest">Failure Queue</CardTitle>
                            <CardDescription className="text-[10px] text-destructive/60">Applications stalled due to internal processing errors</CardDescription>
                        </div>
                    </div>
                </CardHeader>
                <CardContent className="p-0">
                    <Table>
                        <TableHeader className="bg-destructive/5">
                            <TableRow>
                                <TableHead className="text-xs font-bold py-3 pl-6">Candidate</TableHead>
                                <TableHead className="text-xs font-bold">Retry Status</TableHead>
                                <TableHead className="text-xs font-bold">Detailed Error Message</TableHead>
                                <TableHead className="text-xs font-bold text-right pr-6">Recovery Action</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {isLoading ? (
                                <TableRow>
                                    <TableCell colSpan={4} className="h-32 text-center text-xs text-muted-foreground italic">
                                        Scanning for system issues...
                                    </TableCell>
                                </TableRow>
                            ) : !failures || failures.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={4} className="h-32 text-center text-xs text-muted-foreground italic">
                                        No active failures detected. System is operational.
                                    </TableCell>
                                </TableRow>
                            ) : (
                                failures.map((fail) => (
                                    <TableRow key={fail.id} className="hover:bg-destructive/10 transition-colors">
                                        <TableCell className="py-4 pl-6 text-sm font-bold">{fail.candidate_name}</TableCell>
                                        <TableCell>
                                            <Badge variant="outline" className={`text-[10px] uppercase font-bold ${fail.retry_count >= 3 ? 'bg-red-500 text-white border-none' : 'text-destructive border-destructive/20'}`}>
                                                {fail.retry_count} / 3 Attempts
                                            </Badge>
                                        </TableCell>
                                        <TableCell className="max-w-[400px]">
                                            <div className="text-[11px] text-destructive/80 font-mono leading-relaxed" title={fail.failure_reason}>
                                                {fail.failure_reason || 'Unknown internal processing error'}
                                            </div>
                                        </TableCell>
                                        <TableCell className="text-right pr-6">
                                            <Button 
                                                size="sm" 
                                                variant="outline" 
                                                className="h-8 text-xs font-bold text-destructive border-destructive/20 hover:bg-destructive hover:text-white gap-2 transition-all" 
                                                onClick={() => handleRetry(fail.id)}
                                            >
                                                <RefreshCw className="h-3.5 w-3.5" />
                                                Force Retry
                                            </Button>
                                        </TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>
        </div>
    )
}
