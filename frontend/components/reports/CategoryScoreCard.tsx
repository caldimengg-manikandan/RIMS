'use client'

import React from 'react'
import { Card, CardContent } from "@/components/ui/card"

interface CategoryScoreCardProps {
    title: string
    score?: number
    /** Muted N/A without /10 (e.g. interview not completed) */
    showNotAvailable?: boolean
}

const CategoryScoreCardImpl = ({ title, score, showNotAvailable }: CategoryScoreCardProps) => (
    <Card className="h-28 bg-card border shadow-sm">
        <CardContent className="h-full flex flex-col justify-center p-4">
            <div className="text-xs text-slate-500 dark:text-slate-400 font-bold uppercase tracking-wider mb-2">{title}</div>
            {showNotAvailable ? (
                <div className="text-3xl font-semibold text-muted-foreground">N/A</div>
            ) : (
                <div className="text-3xl font-bold text-slate-900 dark:text-slate-50">
                    {score !== undefined && score !== null ? score.toFixed(1) : 'N/A'}
                    <span className="text-base font-normal text-slate-500 dark:text-slate-400 ml-1">/10</span>
                </div>
            )}
        </CardContent>
    </Card>
)

export const CategoryScoreCard = React.memo(CategoryScoreCardImpl);
