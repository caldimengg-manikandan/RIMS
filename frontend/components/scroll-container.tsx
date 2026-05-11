'use client'

import React from 'react'
import { usePathname } from 'next/navigation'
import { ErrorBoundary } from '@/components/error-boundary'

interface ScrollContainerProps {
  children: React.ReactNode
}

/**
 * ScrollContainer is the single scroll authority for non-dashboard pages.
 * On dashboard pages this is overflow-hidden; the dashboard layout owns scrolling.
 * On all other pages this is overflow-y-auto so content can scroll naturally.
 *
 * The inner wrapper div is removed intentionally — it was creating a second
 * flex/height context that triggered a native OS-level scrollbar alongside
 * the styled one.
 */
export function ScrollContainer({ children }: ScrollContainerProps) {
  const pathname = usePathname()
  const isDashboard = pathname?.includes('/dashboard')

  return (
    <main
      className={`flex-1 min-h-0 w-full flex flex-col ${
        isDashboard ? 'overflow-hidden' : 'overflow-y-auto'
      }`}
    >
      <ErrorBoundary>{children}</ErrorBoundary>
    </main>
  )
}
