'use client'

import React from 'react'
import { CheckCircle2, AlertCircle, XCircle } from 'lucide-react'

interface ReportCardProps {
    report: any
    onClick: () => void
}

const ReportCardImpl = ({ report, onClick }: ReportCardProps) => (
    <div
        className="bg-card border rounded-lg px-4 py-4 shadow-sm hover:shadow-md transition-all cursor-pointer border-border group"
        onClick={onClick}
    >
        <div className="flex flex-col md:flex-row md:items-center justify-between w-full pr-4 gap-4">
            <div className="flex flex-col items-start gap-1">
                <div className="font-semibold text-lg flex items-center gap-2 group-hover:text-primary transition-colors">
                    {report.candidate_profile.candidate_name || report.display_date_short}
                    {report.status === 'Selected' && <CheckCircle2 className="h-5 w-5 text-emerald-500" />}
                    {report.status === 'Hold' && <AlertCircle className="h-5 w-5 text-amber-500" />}
                    {report.status === 'Rejected' && <XCircle className="h-5 w-5 text-red-500" />}
                </div>
                <div className="text-sm text-slate-500 dark:text-slate-400">
                    {report.candidate_profile.applied_role || report.filename}
                </div>
            </div>

            <div className="flex gap-4 items-center">
                <div className="text-right w-16">
                    <div className="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-widest">Score</div>
                    <div className="font-bold text-2xl text-primary">{report.overall_score.toFixed(1)}</div>
                </div>
                <div className="text-right w-16 hidden md:block">
                    <div className="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-widest">Aptitude</div>
                    <div className="font-bold text-xl text-slate-700 dark:text-slate-300">
                        {report.aptitude_score !== undefined && report.aptitude_score !== null ? report.aptitude_score.toFixed(1) : '-'}
                    </div>
                </div>
                <div className="text-right w-16 hidden md:block">
                    <div className="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-widest">Behavioral</div>
                    <div className="font-bold text-xl text-slate-700 dark:text-slate-300">
                        {report.behavioral_score !== undefined && report.behavioral_score !== null ? report.behavioral_score.toFixed(1) : '-'}
                    </div>
                </div>

                <div className="text-right w-16">
                    <div className="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-widest">Suggestion</div>
                    <div className={`w-full justify-center font-bold text-xl
                                          ${(['selected', 'hired', 'hire'].includes(report.status?.toLowerCase())) ? 'text-primary' : ''}
                                          ${(['rejected', 'reject'].includes(report.status?.toLowerCase())) ? 'text-destructive' : ''}
                                          ${(['hold', 'on hold', 'review_later'].includes(report.status?.toLowerCase())) ? 'text-amber-600 dark:text-amber-400' : ''}
                                      `}>
                        {(() => {
                            const s = (report.status || '').toLowerCase();
                            if (['selected', 'hired', 'hire'].includes(s)) return 'Select';
                            if (['rejected', 'reject'].includes(s)) return 'Reject';
                            if (['hold', 'on hold', 'review_later'].includes(s)) return 'Hold';
                            if (s.includes('completed') || s.includes('interview')) return 'Review';
                            return s.charAt(0).toUpperCase() + s.slice(1);
                        })()}
                    </div>
                </div>
            </div>
        </div>
    </div>
)

export const ReportCard = React.memo(ReportCardImpl);
