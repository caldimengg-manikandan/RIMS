'use client'

import React from 'react'

interface MetricCardProps {
    title: string
    score: number
}

const MetricCardImpl = ({ title, score }: MetricCardProps) => (
    <div className="flex flex-col items-center justify-center p-3 bg-primary/5 rounded-xl border border-primary/20 shadow-inner">
        <div className="text-xs font-bold uppercase tracking-widest text-primary mb-1 text-center">{title}</div>
        <div className="flex items-baseline gap-1">
            <span className="text-3xl font-black text-primary">
                {score.toFixed(1)}
            </span>
            <span className="text-base font-bold text-primary/50">/10</span>
        </div>
    </div>
);

export const MetricCard = React.memo(MetricCardImpl);
