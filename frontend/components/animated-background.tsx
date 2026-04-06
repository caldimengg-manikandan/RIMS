'use client'

import React from 'react'

export function AnimatedBackground() {
  return (
    <div className="fixed inset-0 -z-50 h-full w-full bg-background overflow-hidden pointer-events-none transition-colors duration-300">
        {/* Subtle grid pattern for texture */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808008_1px,transparent_1px),linear-gradient(to_bottom,#80808008_1px,transparent_1px)] bg-[size:24px_24px] "></div>
        
        {/* Moving Blobs - Made more vibrant */}
        <div className="absolute top-0 -left-4 w-96 h-96 bg-primary/20 rounded-full mix-blend-multiply filter blur-[96px] opacity-90 animate-blob"></div>
        <div className="absolute top-0 -right-4 w-96 h-96 bg-accent/30 rounded-full mix-blend-multiply filter blur-[96px] opacity-90 animate-blob animation-delay-2000"></div>
        <div className="absolute -bottom-8 left-20 w-96 h-96 bg-primary/20 rounded-full mix-blend-multiply filter blur-[96px] opacity-90 animate-blob animation-delay-4000"></div>
        
        {/* Center blob */}
         <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-accent/20 rounded-full mix-blend-multiply filter blur-[96px] opacity-40 animate-blob animation-delay-2000"></div>
    </div>
  )
}
