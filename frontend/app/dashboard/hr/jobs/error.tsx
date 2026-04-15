'use client'

import React, { useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { AlertCircle, RefreshCcw } from 'lucide-react'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    // Log the error to an error reporting service
    console.error('Job Dashboard Error:', error)
  }, [error])

  return (
    <div className="flex h-[calc(100vh-10rem)] items-center justify-center p-4">
      <Card className="max-w-md w-full border-destructive/20 shadow-lg">
        <CardHeader>
          <div className="flex items-center gap-2 text-destructive mb-2">
            <AlertCircle className="h-6 w-6" />
            <CardTitle>Something went wrong</CardTitle>
          </div>
          <CardDescription>
            An error occurred while loading the Job Management dashboard.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="bg-muted p-3 rounded-md text-xs font-mono overflow-auto max-h-[200px] text-muted-foreground border border-border/50">
            {error.message || 'Unknown runtime error'}
          </div>
        </CardContent>
        <CardFooter className="flex gap-3 justify-end pt-2">
          <Button variant="outline" onClick={() => window.location.href = '/dashboard/hr'}>
            Go Back
          </Button>
          <Button onClick={() => reset()} className="gap-2">
            <RefreshCcw className="h-4 w-4" /> Try Again
          </Button>
        </CardFooter>
      </Card>
    </div>
  )
}
