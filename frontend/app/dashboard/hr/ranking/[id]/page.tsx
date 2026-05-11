'use client'

import React from 'react'
import { useParams } from 'next/navigation'
import useSWR from 'swr'
import { fetcher } from '@/app/dashboard/lib/swr-fetcher'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ArrowLeft, User, Award, Users, Trophy, Medal, GitBranch } from 'lucide-react'
import { PageHeader } from '@/components/page-header'
import { useRouter } from 'next/navigation'
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import { ChevronLeft, ChevronRight } from 'lucide-react'

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

    const [rankingPage, setRankingPage] = React.useState(1)
    const [pageSize, setPageSize] = React.useState(10)

    const sortedRanked = React.useMemo(() => {
        return [...ranked].sort((a, b) => (b.composite_score || 0) - (a.composite_score || 0))
    }, [ranked])

    const totalPages = Math.ceil(sortedRanked.length / pageSize)
    const paginatedRanked = React.useMemo(() => {
        const start = (rankingPage - 1) * pageSize
        return sortedRanked.slice(start, start + pageSize)
    }, [sortedRanked, rankingPage, pageSize])

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
        <div className="flex flex-col lg:h-[calc(100vh-7.5rem)] gap-6 overflow-hidden">
            <div className="flex flex-col gap-4 shrink-0 px-4 pt-4">
                <Button 
                    variant="ghost" 
                    onClick={() => router.push('/dashboard/hr/pipeline')} 
                    className="gap-2 text-muted-foreground hover:text-foreground h-auto p-0 flex items-center transition-colors group w-fit"
                >
                    <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-1" />
                    <span className="text-sm font-bold">Back to Pipeline</span>
                </Button>
                <div className="flex items-center justify-between gap-0">
                    <PageHeader
                        title="AI Candidate Ranking"
                        description="Weighted composite score: 40% Resume + 30% Aptitude + 30% AI Interview"
                        icon={Award}
                    />

                    <div className="inline-flex items-center rounded-xl border border-border/60 bg-muted/30 p-1">
                        <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => router.push(`/dashboard/hr/pipelines/${jobId}`)}
                            className="rounded-lg h-8 px-3 text-muted-foreground"
                        >
                            <GitBranch className="h-4 w-4 mr-1.5" />
                            Pipeline View
                        </Button>
                        <Button
                            size="sm"
                            className="rounded-lg h-8 px-3"
                        >
                            <Trophy className="h-4 w-4 mr-1.5" />
                            Candidate Ranking
                        </Button>
                    </div>
                </div>
            </div>

            <Card className="flex-1 min-h-0 flex flex-col border-border/60 shadow-lg bg-card overflow-hidden mx-4">
                <CardHeader className="bg-muted/30 pb-4 shrink-0">
                    <CardTitle className="text-lg flex items-center gap-2">
                        <Users className="h-5 w-5 text-primary" />
                        Job Leaderboard
                    </CardTitle>
                </CardHeader>
                <CardContent className="flex-1 overflow-auto p-0">
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
                            {paginatedRanked.map((cand, index) => {
                                const actualRank = (rankingPage - 1) * pageSize + index + 1
                                return (
                                    <TableRow key={cand.id} className="hover:bg-muted/20 transition-colors border-border/40 py-4 h-16">
                                        <TableCell className="font-medium align-middle">
                                            <div className="flex items-center gap-3 pl-2">
                                                {getRankIcon(actualRank)}
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
                                )
                            })}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>

            {/* Pagination Controls */}
            <div className="shrink-0 bg-background/80 backdrop-blur-xl border-t border-border p-4 z-30 shadow-[0_-4px_12px_-4px_rgba(0,0,0,0.1)]">
                <div className="flex flex-col sm:flex-row items-center justify-between gap-4 max-w-[1600px] mx-auto px-6">
                    <div className="flex items-center gap-3">
                        <Button
                            variant="outline"
                            size="lg"
                            onClick={() => setRankingPage(prev => Math.max(1, prev - 1))}
                            disabled={rankingPage <= 1 || isLoading}
                            className="h-11 px-6 rounded-xl font-bold bg-background dark:bg-muted hover:bg-accent border-border transition-all shadow-sm active:scale-95 disabled:opacity-50"
                        >
                            <ChevronLeft className="mr-2 h-5 w-5" /> Previous
                        </Button>

                        <div className="px-4 py-2 bg-slate-100 dark:bg-slate-800 rounded-lg text-sm font-bold text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700">
                            Page {rankingPage} {totalPages > 0 ? `of ${totalPages}` : ''}
                        </div>

                        <Button
                            variant="outline"
                            size="lg"
                            onClick={() => setRankingPage(prev => Math.min(totalPages, prev + 1))}
                            disabled={rankingPage >= totalPages || isLoading}
                            className="h-11 px-6 rounded-xl font-bold bg-background dark:bg-muted hover:bg-accent border-border transition-all shadow-sm active:scale-95 disabled:opacity-50"
                        >
                            Next <ChevronRight className="ml-2 h-5 w-5" />
                        </Button>
                    </div>

                    <div className="flex items-center gap-2">
                        <span className="text-sm font-bold text-muted-foreground">Show</span>
                        <Select
                            value={String(pageSize)}
                            onValueChange={(val) => {
                                setPageSize(Number(val));
                                setRankingPage(1);
                            }}
                        >
                            <SelectTrigger className="h-10 w-[85px] rounded-xl border-border bg-background font-bold shadow-none focus:ring-0">
                                <SelectValue placeholder="10" />
                            </SelectTrigger>
                            <SelectContent className="min-w-[70px]">
                                {[5, 10, 20, 50, 100].map((size) => (
                                    <SelectItem key={size} value={String(size)} className="font-bold">
                                        {size}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                        <span className="text-sm font-bold text-muted-foreground">per page</span>
                    </div>
                </div>
            </div>
        </div>
    )
}
