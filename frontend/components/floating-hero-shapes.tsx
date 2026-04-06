'use client'

import React from 'react'

export function FloatingHeroShapes() {
    return (
        <div className="absolute inset-0 overflow-hidden pointer-events-none z-0">
            {/* Outline Circle */}
            <div className="absolute top-[10%] left-[10%] opacity-50 text-indigo-500 motion-safe:animate-[blob_18s_ease-in-out_infinite]">
                <div className="animate-[spin_25s_linear_infinite]">
                    <svg width="60" height="60" viewBox="0 0 60 60" fill="none" stroke="currentColor" strokeWidth="2">
                        <circle cx="30" cy="30" r="28" />
                    </svg>
                </div>
            </div>

            {/* Solid Triangle */}
            <div className="absolute top-[60%] left-[20%] opacity-40 text-blue-500 motion-safe:animate-[blob_22s_ease-in-out_infinite_reverse]">
                <div className="animate-[spin_20s_linear_infinite_reverse]">
                    <svg width="70" height="70" viewBox="0 0 70 70" fill="currentColor">
                        <polygon points="35,0 70,70 0,70" />
                    </svg>
                </div>
            </div>

            {/* Outline Rectangle */}
            <div className="absolute top-[30%] right-[15%] opacity-60 text-purple-500 motion-safe:animate-[blob_16s_ease-in-out_infinite]">
                <div className="animate-[spin_18s_linear_infinite]">
                    <svg width="50" height="50" viewBox="0 0 50 50" fill="none" stroke="currentColor" strokeWidth="2.5">
                        <rect x="2" y="2" width="46" height="46" rx="6" />
                    </svg>
                </div>
            </div>

            {/* Solid Small Circle */}
            <div className="absolute top-[75%] right-[25%] opacity-50 text-sky-500 motion-safe:animate-[blob_25s_ease-in-out_infinite_reverse]">
                <div className="animate-[spin_30s_linear_infinite]">
                    <svg width="30" height="30" viewBox="0 0 30 30" fill="currentColor">
                        <circle cx="15" cy="15" r="15" />
                    </svg>
                </div>
            </div>

            {/* Outline Triangle */}
            <div className="absolute top-[20%] right-[40%] opacity-45 text-rose-400 motion-safe:animate-[blob_19s_ease-in-out_infinite]">
                <div className="animate-[spin_22s_linear_infinite_reverse]">
                    <svg width="40" height="40" viewBox="0 0 40 40" fill="none" stroke="currentColor" strokeWidth="2">
                        <polygon points="20,2 38,38 2,38" />
                    </svg>
                </div>
            </div>
        </div>
    )
}
