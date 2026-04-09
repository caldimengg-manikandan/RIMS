'use client'

import React, { useState, useEffect, useCallback, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/app/dashboard/lib/utils"
import { AlertCircle, RefreshCcw } from 'lucide-react'
import { Button } from '@/components/ui/button'

/**
 * PRODUCTION LOGGING HELPER
 * Swap this out for Sentry.captureMessage or Axiom as you scale.
 */
const logPerformanceAlert = (componentId: string, path: string) => {
  const message = `[PERF_ALERT] Component ${componentId} exceeded 10s load time at path: ${path}`;
  console.warn(message);
  
  // Example for Sentry integration:
  // if (process.env.NODE_ENV === 'production') {
  //   Sentry.captureMessage(message, { level: 'warning', tags: { componentId, path } });
  // }
}

/**
 * 1. CUSTOM HOOK: useLoadingState
 */
export function useLoadingState(initialState = false, minDuration = 800) {
  const [isLoading, setIsLoading] = useState(initialState)
  const [displayLoading, setDisplayLoading] = useState(initialState)
  const [takeTooLong, setTakeTooLong] = useState(false)
  const [startTime, setStartTime] = useState<number | null>(initialState ? Date.now() : null)
  
  const componentId = useRef<string>(Math.random().toString(36).substring(7))

  const startLoading = useCallback(() => {
    setIsLoading(true)
    setDisplayLoading(true)
    setStartTime(Date.now())
    setTakeTooLong(false)
  }, [])

  const stopLoading = useCallback(() => {
    setIsLoading(false)
    const elapsed = startTime ? Date.now() - startTime : 0
    const remaining = Math.max(0, minDuration - elapsed)

    setTimeout(() => {
      setDisplayLoading(false)
      setStartTime(null)
    }, remaining)
  }, [startTime, minDuration])

  useEffect(() => {
    let timer: NodeJS.Timeout
    if (isLoading) {
      timer = setTimeout(() => {
        setTakeTooLong(true)
        logPerformanceAlert(componentId.current, window.location.pathname)
      }, 10000)
    }
    return () => clearTimeout(timer)
  }, [isLoading])

  return {
    isLoading,
    displayLoading,
    takeTooLong,
    startLoading,
    stopLoading,
  }
}

/**
 * 2. SKELETON LOADERS
 */
export function StatsGridSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 p-1">
      {Array.from({ length: count }).map((_, i) => (
        <div 
          key={i} 
          className="bg-card/50 backdrop-blur-sm border rounded-3xl p-6 space-y-4 animate-in fade-in zoom-in duration-500"
          style={{ animationDelay: `${i * 100}ms` }}
        >
          <div className="flex justify-between items-start">
            <Skeleton className="h-4 w-24 rounded-full" />
            <Skeleton className="h-8 w-8 rounded-xl" />
          </div>
          <div className="space-y-2">
            <Skeleton className="h-10 w-16 rounded-lg" />
            <Skeleton className="h-4 w-32 rounded-full" />
          </div>
          <div className="pt-2">
            <Skeleton className="h-2 w-full rounded-full" />
          </div>
        </div>
      ))}
    </div>
  )
}

export function DataTableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="w-full space-y-4 animate-in fade-in duration-700">
      <div className="flex items-center gap-4 px-4 py-3 bg-muted/30 rounded-2xl border-b border-muted">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className={cn("h-4", i === 0 ? "w-40" : "flex-1", "rounded-full")} />
        ))}
      </div>
      <div className="space-y-3">
        {Array.from({ length: rows }).map((_, i) => (
          <div 
            key={i} 
            className="flex items-center gap-4 px-4 py-4 border rounded-2xl bg-card/40 border-slate-100 dark:border-slate-800"
            style={{ opacity: 1 - (i * 0.15) }}
          >
            <div className="flex items-center gap-3 w-40">
              <Skeleton className="h-10 w-10 rounded-full shrink-0" />
              <div className="space-y-2 flex-1">
                <Skeleton className="h-3 w-full rounded-full" />
                <Skeleton className="h-2 w-2/3 rounded-full opacity-60" />
              </div>
            </div>
            {Array.from({ length: 4 }).map((_, j) => (
              <Skeleton key={j} className="h-3 flex-1 rounded-full" />
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

/**
 * 3. GLOBAL PROGRESS (SLIM LOADER)
 */
export function SlimProgress({ loading }: { loading: boolean }) {
  return (
    <div className="fixed top-0 left-0 right-0 h-0 z-[45] pointer-events-none" aria-hidden="true">
      <AnimatePresence>
        {loading && (
          <motion.div
            initial={{ scaleX: 0, opacity: 0 }}
            animate={{ scaleX: 1, opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5, ease: "circOut" }}
            className="h-1 bg-primary w-full origin-left shadow-[0_0_12px_rgba(var(--primary),0.6)]"
          />
        )}
      </AnimatePresence>
    </div>
  )
}

/**
 * 4. REFINED LOADING WRAPPER
 */
export interface LoadingWrapperProps {
  isLoading: boolean
  error?: Error | null | string
  onRetry?: () => void
  children: React.ReactNode
  fallback?: React.ReactNode
  minDuration?: number
  loadingMessage?: string // CHERRY-ON-TOP: Custom loading micro-copy
}

export function LoadingWrapper({ 
  isLoading, 
  error,
  onRetry,
  children, 
  fallback, 
  minDuration = 800,
  loadingMessage = "Still working on it... Optimization in progress."
}: LoadingWrapperProps) {
  const { displayLoading, takeTooLong } = useLoadingState(isLoading, minDuration)
  const errorRef = useRef<HTMLDivElement>(null)

  // CHERRY-ON-TOP: Focus management for error state
  useEffect(() => {
    if (error && errorRef.current) {
      errorRef.current.focus()
    }
  }, [error])

  return (
    <div className="relative w-full">
      <AnimatePresence mode="popLayout">
        {error ? (
          <motion.div
            key="error"
            ref={errorRef}
            tabIndex={-1} // Make div focusable for keyboard users
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            className="w-full py-16 flex flex-col items-center justify-center text-center space-y-4 bg-red-50/30 dark:bg-red-950/10 rounded-3xl border border-red-100 dark:border-red-900/30 focus:outline-none"
            role="alert"
          >
            <div className="p-4 bg-red-100 dark:bg-red-900/30 rounded-full text-red-600 dark:text-red-400">
              <AlertCircle className="h-8 w-8" />
            </div>
            <div className="space-y-1">
              <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">Fetch Failed</h3>
              <p className="text-sm text-slate-500 dark:text-slate-400 max-w-xs mx-auto">
                {typeof error === 'string' ? error : error?.message || "We encountered an error while securing your data. Please try again."}
              </p>
            </div>
            {onRetry && (
              <Button 
                variant="outline" 
                onClick={onRetry}
                className="gap-2 rounded-full border-red-200 hover:bg-red-50 text-red-700 dark:text-red-400 dark:border-red-800"
              >
                <RefreshCcw className="h-4 w-4" /> Retry Connection
              </Button>
            )}
          </motion.div>
        ) : displayLoading ? (
          <motion.div
            key="loader"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="w-full py-12 flex flex-col items-center justify-center space-y-6"
            aria-busy="true"
            aria-live="polite"
          >
            {fallback || <StatsGridSkeleton />}
            
            <AnimatePresence>
              {takeTooLong && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="bg-amber-50 dark:bg-amber-950/20 text-amber-600 dark:text-amber-400 px-4 py-2 rounded-full text-sm font-medium border border-amber-200 dark:border-amber-800 flex items-center gap-2"
                >
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
                  </span>
                  {loadingMessage}
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        ) : (
          <motion.div
            key="content"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: "easeOut" }}
          >
            {children}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

/**
 * 5. PAGE LOADER
 */
interface PageLoaderProps extends LoadingWrapperProps {
  isEmpty?: boolean
  isRefreshing?: boolean
  emptyMessage?: string
  emptyAction?: React.ReactNode
}

export function PageLoader({ 
  isLoading, 
  isRefreshing,
  error, 
  onRetry, 
  isEmpty, 
  emptyMessage = "No records found.", 
  emptyAction,
  children, 
  fallback = <DataTableSkeleton />,
  ...props 
}: PageLoaderProps) {
  const useSoftLoading = isRefreshing && !isEmpty;

  return (
    <>
      <SlimProgress loading={Boolean(useSoftLoading && isLoading)} />
      <LoadingWrapper 
        isLoading={isLoading && !useSoftLoading} 
        error={error} 
        onRetry={onRetry} 
        fallback={fallback}
        {...props}
      >
        {isEmpty && !isLoading ? (
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col items-center justify-center py-20 text-center space-y-4"
          >
            <div className="bg-slate-100 dark:bg-slate-800 p-4 rounded-full text-slate-400">
              <RefreshCcw className="h-10 w-10 opacity-20" />
            </div>
            <p className="text-slate-500 font-medium">{emptyMessage}</p>
            {emptyAction}
          </motion.div>
        ) : (
          children
        )}
      </LoadingWrapper>
    </>
  )
}
