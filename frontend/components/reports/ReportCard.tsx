'use client'

import React from 'react'
import { CheckCircle2, AlertCircle, XCircle } from 'lucide-react'
import { isInterviewNotCompleted } from '@/components/reports/interviewIncomplete'

interface ReportCardProps {
    report: any
    onClick: () => void
}

const ReportCardImpl = ({ report, onClick }: ReportCardProps) => {
  const notCompleted = isInterviewNotCompleted(report)
  return (
    <div
        className="bg-card border rounded-lg px-4 py-4 shadow-sm hover:shadow-md transition-all cursor-pointer border-border group"
        onClick={onClick}
    >
        <div className="flex flex-col md:flex-row md:items-center justify-between w-full pr-4 gap-4">
            <div className="flex flex-col items-start gap-1">
                <div className="font-semibold text-lg flex items-center gap-2 group-hover:text-primary transition-colors">
                    {report?.candidate_profile?.candidate_name || report?.display_date_short || "Anonymous"}
                    {report?.status === 'Selected' && <CheckCircle2 className="h-5 w-5 text-emerald-500" />}
                    {report?.status === 'Hold' && <AlertCircle className="h-5 w-5 text-amber-500" />}
                    {report?.status === 'Rejected' && <XCircle className="h-5 w-5 text-red-500" />}
                </div>
                <div className="text-sm text-slate-500 dark:text-slate-400">
                    {report?.candidate_profile?.applied_role || report?.filename || "Unspecified Role"}
                </div>
            </div>

            <div className="flex gap-4 items-center">
                <div className="text-right w-24">
                    <div className="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-widest">Score</div>
                    <div className="font-bold text-2xl text-primary">{(report?.overall_score || 0).toFixed(1)}</div>
                </div>
                <div className="text-right w-24 hidden md:block">
                    <div className="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-widest">Aptitude</div>
                    <div className="font-bold text-xl text-slate-700 dark:text-slate-300">
                        {typeof report?.aptitude_score === 'number' ? report.aptitude_score.toFixed(1) : '-'}
                    </div>
                </div>
                <div className="text-right w-28 hidden md:block">
                    <div className="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-widest">Behavioral</div>
                    <div className="font-bold text-xl text-slate-700 dark:text-slate-300">
                        {typeof report?.behavioral_score === 'number' ? report.behavioral_score.toFixed(1) : '-'}
                    </div>
                </div>

                <div className="text-right w-28">
                    <div className="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-widest">Suggestion</div>
                    <div
                        className={`w-full justify-center font-bold text-xl
                          ${report.termination_reason ? 'text-red-600 dark:text-red-400' : ''}
                          ${!report.termination_reason && notCompleted ? 'text-orange-600 dark:text-orange-400' : ''}
                          ${!report.termination_reason && !notCompleted && report.overall_score > 6 ? 'text-primary' : ''}
                          ${!report.termination_reason && !notCompleted && report.overall_score <= 4 ? 'text-destructive' : ''}
                          ${!report.termination_reason && !notCompleted && report.overall_score > 4 && report.overall_score <= 6 ? 'text-amber-600 dark:text-amber-400' : ''}
                        `}
                    >
                        {(() => {
                            const score = Number(report?.overall_score || 0)
                            if (report.termination_reason) return 'Terminated'
                            if (notCompleted) return 'Not Completed'
                            if (score > 6) return 'Select'
                            if (score > 4) return 'Consider'
                            return 'Reject'
                        })()}
                    </div>
                </div>
            </div>
        </div>
    </div>
  )
}

export const ReportCard = React.memo(ReportCardImpl);
