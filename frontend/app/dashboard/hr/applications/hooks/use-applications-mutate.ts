import { useSWRConfig } from 'swr'
import { useCallback } from 'react'

/** 
 * Centralized Guardrail for Application State Mutations.
 * Ensures that ANY change to an application status invalidates all relevant cache keys.
 */
export function useApplicationsMutate() {
  const { mutate } = useSWRConfig()

  const invalidateApplications = useCallback(async (appId?: number) => {
    const keysToInvalidate = [
      '/api/applications',         // Standard list
      '/api/search/candidates',    // Magic search list
      '/api/analytics/dashboard',  // Metrics
    ]

    if (appId) {
      keysToInvalidate.push(`/api/applications/${appId}`)
    }

    // Use a pattern-based invalidation for SWR
    const promises = keysToInvalidate.map(key => 
      mutate(
        (cacheKey: any) => typeof cacheKey === 'string' && cacheKey.startsWith(key),
        undefined,
        { revalidate: true }
      )
    )

    await Promise.all(promises)
    console.log(`[Revalidation Guard] Invalidated ${keysToInvalidate.length} keys for App ${appId || 'ALL'}`)
  }, [mutate])

  return { invalidateApplications }
}
