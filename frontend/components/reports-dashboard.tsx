"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { APIClient } from '@/app/dashboard/lib/api-client'

export default function ReportsDashboard() {
    const [reports, setReports] = useState<any[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        const fetchReports = async () => {
            try {
                const data = await APIClient.get<any[]>('/api/analytics/reports')
                setReports(data)
            } catch (err: any) {
                setError(err.message || "Failed to load reports.")
            } finally {
                setLoading(false)
            }
        }

        fetchReports()
    }, [])

    if (loading) return <div>Loading reports...</div>
    if (error) return <div className="text-destructive font-semibold">{error}</div>
    if (reports.length === 0) return <div>No candidate reports generated yet.</div>

    return (
        <div className="flex flex-col gap-4 p-4">
            <h2 className="text-2xl font-bold mb-4">Interview Reports</h2>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {reports.map((report, idx) => {

                    const {
                        candidate_profile,
                        status,
                        status_color,
                        final_score,
                        aptitude_score,
                        first_level_score,
                        hiring_comments,
                        display_date_short
                    } = report

                    const isJunior = candidate_profile?.experience_level?.toLowerCase() === "junior"

                    return (
                        <Card key={idx} className="flex flex-col shadow-sm transition-all hover:shadow-md border-border/60">
                            <CardHeader className="pb-2">
                                <div className="flex justify-between items-start">
                                    <div className="flex items-center gap-3">
                                        <Avatar className="h-10 w-10 border bg-muted/50">
                                            <AvatarFallback className="font-bold text-primary bg-primary/10">
                                                {candidate_profile?.candidate_name?.charAt(0) || "U"}
                                            </AvatarFallback>
                                        </Avatar>
                                        <div>
                                            <CardTitle className="text-lg">{candidate_profile?.candidate_name}</CardTitle>
                                            <CardDescription className="text-xs">{candidate_profile?.applied_role} • {candidate_profile?.experience_level}</CardDescription>
                                        </div>
                                    </div>
                                    <Badge variant={status_color === "success" ? "default" : status_color === "error" ? "destructive" : "secondary"}>
                                        {status}
                                    </Badge>
                                </div>
                            </CardHeader>

                            <CardContent className="pt-2 flex-grow flex flex-col gap-3">
                                <div className="grid grid-cols-2 gap-2 text-sm">
                                    {isJunior && (
                                        <div className="flex flex-col p-2 bg-muted/40 rounded-md border border-border/40">
                                            <span className="text-xs text-muted-foreground font-semibold uppercase tracking-wider">Aptitude Score</span>
                                            <span className="text-lg font-bold">{aptitude_score !== null && aptitude_score !== undefined ? aptitude_score.toFixed(1) : "N/A"}</span>
                                        </div>
                                    )}

                                    <div className="flex flex-col p-2 bg-muted/40 rounded-md border border-border/40">
                                        <span className="text-xs text-muted-foreground font-semibold uppercase tracking-wider">First Level Score</span>
                                        <span className="text-lg font-bold">{first_level_score !== null && first_level_score !== undefined ? first_level_score.toFixed(1) : "N/A"}</span>
                                    </div>
                                </div>

                                <div className="flex flex-col p-2 bg-primary/5 rounded-md border border-primary/10 mt-1">
                                    <span className="text-xs text-primary/80 font-semibold uppercase tracking-wider">Final Average</span>
                                    <span className="text-xl font-bold text-primary">{final_score ? final_score.toFixed(1) : "0.0"}</span>
                                </div>

                                {hiring_comments && (
                                    <div className="mt-2 text-sm bg-accent/20 border border-accent/30 p-2 rounded-md italic">
                                        <span className="block text-xs font-semibold not-italic mb-1 opacity-70">HR Remarks:</span>
                                        "{hiring_comments}"
                                    </div>
                                )}

                                <div className="mt-auto pt-4 text-xs text-muted-foreground text-right">
                                    Completed: {display_date_short}
                                </div>
                            </CardContent>
                        </Card>
                    )
                })}
            </div>
        </div>
    )
}
