'use client'
import React, { useRef, useEffect } from 'react'

export function InteractiveFeatureBg({ children }: { children: React.ReactNode }) {
    const containerRef = useRef<HTMLElement>(null)

    useEffect(() => {
        const container = containerRef.current
        if (!container) return

        const handleMouseMove = (e: MouseEvent) => {
            const rect = container.getBoundingClientRect()
            const x = e.clientX - rect.left
            const y = e.clientY - rect.top
            container.style.setProperty('--mouse-x', `${x}px`)
            container.style.setProperty('--mouse-y', `${y}px`)
        }

        container.addEventListener('mousemove', handleMouseMove)
        return () => container.removeEventListener('mousemove', handleMouseMove)
    }, [])

    return (
        <section
            ref={containerRef}
            className="py-24 relative z-10 overflow-hidden group"
        >
            {/* Background Interactive Elements */}
            <div className="absolute inset-0 pointer-events-none z-0">
                <div
                    className="absolute inset-0 transition-opacity duration-300 opacity-0 group-hover:opacity-100"
                    style={{
                        background: `radial-gradient(800px circle at var(--mouse-x, 50%) var(--mouse-y, 50%), rgba(255, 255, 255, 0.06), transparent 40%)`
                    }}
                />
                <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:30px_30px] opacity-60" />
            </div>

            {/* Dynamic Floating Orbs for the section */}
            <div className="absolute top-[10%] left-[5%] w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl animate-[blob_8s_infinite] pointer-events-none -z-10" />
            <div className="absolute bottom-[10%] right-[10%] w-72 h-72 bg-sky-500/10 rounded-full blur-3xl animate-[blob_10s_infinite_reverse] pointer-events-none -z-10" />

            {/* Content Wrapped via children */}
            <div className="relative z-10">
                {children}
            </div>
        </section>
    )
}
