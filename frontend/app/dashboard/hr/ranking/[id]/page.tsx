'use client'

import React from 'react'
import { useParams } from 'next/navigation'
import useSWR from 'swr'
import { fetcher } from '@/app/dashboard/lib/swr-fetcher'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Trophy, Medal, Award, User, ArrowLeft, Users } from 'lucide-react'
import { useRouter } from 'next/navigation'

interface RankedCandidate {
    rank: number
    id: number
    candidate_name: string
    composite_score: number
    recommendation: string
    status: string
}

export default function LeaderboardPage() {
    const router = useRouter()
    const params = useParams()
    const jobId = params.id
    const { data: ranked = [], isLoading } = useSWR<RankedCandidate[]>(`/api/applications/ranking/${jobId}`, fetcher)

    if (isLoading) return <div className="p-8 text-center text-muted-foreground">Loading ranking...</div>

    const getRankIcon = (rank: number) => {
        if (rank === 1) return <Trophy className="h-5 w-5 text-yellow-500" />
        if (rank === 2) return <Medal className="h-5 w-5 text-slate-400" />
        if (rank === 3) return <Award className="h-5 w-5 text-amber-600" />
        return <span className="text-sm font-mono text-muted-foreground ml-1.5">{rank}</span>
    }

    const getRecommendationBadge = (rec: string) => {
        if (rec === 'Strong Hire') return <Badge className="bg-green-600 hover:bg-green-700 text-white border-0">Strong Hire</Badge>
        if (rec === 'Hire') return <Badge className="bg-emerald-500 hover:bg-emerald-600 text-white border-0">Hire</Badge>
        if (rec === 'Borderline') return <Badge variant="outline" className="text-amber-600 border-amber-200 bg-amber-50">Borderline</Badge>
        if (rec === 'Reject') return <Badge variant="destructive" className="border-0">Reject</Badge>
        return <Badge variant="secondary">N/A</Badge>
    }

    return (
        <div className="space-y-6">
            <div className="flex flex-col gap-4">
                <Button 
                    variant="ghost" 
                    onClick={() => router.push('/dashboard/hr/jobs')} 
                    className="gap-2 text-muted-foreground hover:text-foreground h-auto p-0 flex items-center transition-colors group w-fit"
                >
                    <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-1" />
                    <span className="text-sm font-bold">Back to Jobs</span>
                </Button>
                <div className="flex justify-between items-center">
                    <div>
                        <h1 className="text-3xl font-extrabold tracking-tight uppercase">AI Candidate Ranking</h1>
                        <p className="text-xs font-bold text-muted-foreground mt-2 uppercase tracking-widest opacity-60">Weighted composite score: 40% Resume + 30% Aptitude + 30% AI Interview</p>
                    </div>
                </div>
            </div>

            <Card className="border-border/60 shadow-lg bg-card">
                <CardHeader className="bg-muted/30 pb-4">
                    <CardTitle className="text-lg flex items-center gap-2">
                        <Users className="h-5 w-5 text-primary" />
                        Job Leaderboard
                    </CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                    <Table>
                        <TableHeader>
                            <TableRow className="hover:bg-transparent bg-muted/10 border-border/60">
                                <TableHead className="w-[100px] font-bold text-foreground">Rank</TableHead>
                                <TableHead className="font-bold text-foreground">Candidate Name</TableHead>
                                <TableHead className="font-bold text-foreground">Status</TableHead>
                                <TableHead className="font-bold text-foreground text-center">Composite Score</TableHead>
                                <TableHead className="font-bold text-foreground text-center">AI Recommendation</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {ranked.map((cand) => (
                                <TableRow key={cand.id} className="hover:bg-muted/20 transition-colors border-border/40 py-4 h-16">
                                    <TableCell className="font-medium align-middle">
                                        <div className="flex items-center gap-3 pl-2">
                                            {getRankIcon(cand.rank)}
                                        </div>
                                    </TableCell>
                                    <TableCell className="align-middle">
                                        <div className="flex items-center gap-3">
                                            <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                                                <User className="h-4 w-4 text-primary" />
                                            </div>
                                            <span className="font-semibold text-foreground">{cand.candidate_name}</span>
                                        </div>
                                    </TableCell>
                                    <TableCell className="align-middle capitalize text-muted-foreground font-medium">
                                        {cand.status.replace(/_/g, ' ')}
                                    </TableCell>
                                    <TableCell className="text-center align-middle">
                                        <div className="inline-flex items-center justify-center p-2 rounded-lg bg-primary/10 text-primary font-mono font-black text-lg min-w-[60px] border border-primary/20 shadow-sm">
                                            {cand.composite_score || 0}
                                        </div>
                                    </TableCell>
                                    <TableCell className="text-center align-middle">
                                        {getRecommendationBadge(cand.recommendation)}
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>
        </div>
    )
}
