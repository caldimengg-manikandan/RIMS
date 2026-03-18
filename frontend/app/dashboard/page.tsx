'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/app/dashboard/lib/auth-context'

export default function DashboardRedirect() {
    const { user, isLoading } = useAuth()
    const router = useRouter()

    useEffect(() => {
        if (!isLoading && user) {
            router.push('/dashboard/hr')
        } else if (!isLoading && !user) {
            router.push('/')
        }
    }, [user, isLoading, router])

    return (
        <div className="min-h-screen flex items-center justify-center bg-background">
            <div className="flex flex-col items-center gap-4 animate-in fade-in duration-500">
                <div className="h-10 w-10 border-4 border-primary/20 border-t-primary rounded-full animate-spin" />
                <p className="text-sm font-medium text-muted-foreground tracking-wide">
                    Loading your workspace...
                </p>
            </div>
        </div>
    )
}
