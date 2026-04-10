'use client'

import React, { useEffect, useState } from 'react'
import { usePathname, useSearchParams } from 'next/navigation'
import { SlimProgress } from './shared-loaders'

/**
 * Automatically triggers the SlimProgress bar on any route or search parameter change.
 * This provides immediate feedback for sidebar navigation and filtering.
 */
export function NavigationProgress() {
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    // When the path or query changes, the transition to the new view has finished
    // (in Next.js App Router context, this is the most reliable event we have).
    // We briefly show the loader if we wanted to capture the 'start' phase,
    // but Next.js doesn't provide an easy way to hook into the START of navigation.
    
    // Workaround: We listen for any click on a link in the document
    const handleClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement
      const link = target.closest('a')
      
      if (link && 
          link.href && 
          link.href.startsWith(window.location.origin) && 
          link.target !== '_blank' &&
          link.href !== window.location.href) {
        setLoading(true)
      }
    }

    document.addEventListener('click', handleClick, { capture: true })
    return () => document.removeEventListener('click', handleClick, { capture: true })
  }, [])

  useEffect(() => {
    // Stop loading once the route actually changes
    setLoading(false)
  }, [pathname, searchParams])

  return <SlimProgress loading={loading} />
}
