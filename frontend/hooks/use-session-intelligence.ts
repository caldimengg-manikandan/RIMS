'use client'

import { useEffect, useMemo, useCallback, useRef } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import {
  getSessionData,
  recordPageVisit,
  recordFileOpen,
  recordTimeSpent,
  recordTransition,
  evaluatePredictionAccuracy,
  clearSession,
  getSessionDuration,
  getMostVisitedPages,
  getMostOpenedFiles,
  getPredictedNextPages,
  type SessionData,
  type PredictionWithConfidence,
} from '@/lib/session-store'

// Safe requestIdleCallback fallback
const requestIdle = typeof window !== 'undefined' && window.requestIdleCallback 
  ? window.requestIdleCallback 
  : (cb: Function) => setTimeout(cb, 50);

const DEBUG = process.env.NODE_ENV === 'development';

export function useSessionIntelligence() {
  const pathname = usePathname()
  const router = useRouter()
  
  const startTimeRef = useRef<number>(typeof window !== 'undefined' ? Date.now() : 0)
  const lastPathRef = useRef<string>(pathname || '')

  useEffect(() => {
    if (typeof window === 'undefined') return

    if (lastPathRef.current !== pathname) {
      const timeSpent = Date.now() - startTimeRef.current
      const prevPath = lastPathRef.current
      
      if (timeSpent > 500 && prevPath && pathname) {
        // v4: Test how accurate our prediction was before recording the new transition
        evaluatePredictionAccuracy(pathname, prevPath)
        
        recordTransition(prevPath, pathname)
        recordTimeSpent(prevPath, timeSpent)
      }
      
      startTimeRef.current = Date.now()
      lastPathRef.current = pathname || ''
      
      if (pathname?.startsWith('/dashboard')) {
        recordPageVisit(pathname)
      }
    }
  }, [pathname])

  useEffect(() => {
    if (typeof window === 'undefined') return
    
    const handleVisibilityChange = () => {
      if (document.hidden) {
        const timeSpent = Date.now() - startTimeRef.current
        if (timeSpent > 1000) recordTimeSpent(lastPathRef.current, timeSpent)
      } else {
        startTimeRef.current = Date.now()
      }
    }
    
    document.addEventListener('visibilitychange', handleVisibilityChange)
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      const timeSpent = Date.now() - startTimeRef.current
      if (timeSpent > 1000) recordTimeSpent(lastPathRef.current, timeSpent)
    }
  }, [])

  const session = useMemo<SessionData>(() => getSessionData(), [pathname])

  const trackFileOpen = useCallback((name: string, path: string) => {
    recordFileOpen(name, path)
  }, [])

  /** v4: Confidence-Gated Preloading */
  const preloadHints = useCallback((predictions: PredictionWithConfidence[]) => {
    if (typeof window === 'undefined') return;

    // Filter by confidence threshold to prevent wasteful loading
    const highConfidence = predictions.filter(p => p.confidence > 0.6).map(p => p.path);
    if (highConfidence.length === 0) return;

    if (navigator && (navigator as any).connection) {
      const conn = (navigator as any).connection;
      if (conn.saveData || conn.effectiveType?.includes('2g') || conn.effectiveType?.includes('3g')) {
        if (DEBUG) console.debug('[Session v4] Preloading aborted to save bandwidth.');
        return;
      }
    }

    requestIdle(() => {
      highConfidence.forEach(p => {
        if (typeof router.prefetch === 'function') {
          router.prefetch(p);
          if (DEBUG) console.debug(`[Session v4] Prefetching ${p} (Confidence > 0.6)`);
        }
      })
    })
  }, [router])

  /** Console helper for Admins/Devs to observe intelligence layer */
  const debugDashboard = useCallback(() => {
    if (typeof window === 'undefined') return;
    const s = getSessionData();
    console.groupCollapsed('🧠 RIMS Session Intelligence v4 Dashboard');
    console.table({
      version: s.version,
      predictionsHits: s.predictionsMeta.hits,
      predictionsMisses: s.predictionsMeta.misses,
      hitRate: s.predictionsMeta.hits + s.predictionsMeta.misses > 0 
        ? ((s.predictionsMeta.hits / (s.predictionsMeta.hits + s.predictionsMeta.misses)) * 100).toFixed(1) + '%' 
        : 'N/A',
      weightFrequency: s.weights.frequency.toFixed(2),
      weightTransition: s.weights.transition.toFixed(2),
    });
    const currentPreds = getPredictedNextPages(pathname || s.lastVisitedPage, s);
    if (currentPreds.length > 0) {
      console.log('🔮 Current Route Predictions:');
      console.table(currentPreds);
    }
    console.groupEnd();
  }, [pathname])

  return {
    lastVisitedPage: session.lastVisitedPage,
    recentPages: session.recentPages,
    lastOpenedFile: session.lastOpenedFile,
    sessionStartedAt: session.sessionStartedAt,
    sessionDuration: getSessionDuration(),
    
    mostVisitedPages: getMostVisitedPages(session),
    mostOpenedFiles: getMostOpenedFiles(session),
    
    predictedNextPages: getPredictedNextPages(pathname || session.lastVisitedPage, session),
    
    recordFileOpen: trackFileOpen,
    preloadHints,
    debugDashboard,
    clearSession,
  }
}
