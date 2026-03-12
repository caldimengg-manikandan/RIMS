'use client'

import React from "react"

import { useAuth } from '@/app/dashboard/lib/auth-context'
import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { SidebarProvider } from '@/components/animate-ui/components/radix/sidebar'
import { AppSidebar } from '@/components/app-sidebar'
import { UserNav } from '@/components/user-nav'
import { ToggleTheme } from '@/components/lightswind/toggle-theme'
import { NotificationBell } from '@/components/notification-bell'
import { Search } from 'lucide-react'
import { SWRConfig } from 'swr'
import { fetcher } from '@/app/dashboard/lib/swr-fetcher'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const { isAuthenticated, isLoading } = useAuth()
  const router = useRouter()
  const [isMounted, setIsMounted] = useState(false)

  useEffect(() => {
    setIsMounted(true)
  }, [])

  useEffect(() => {
    if (isMounted && !isLoading && !isAuthenticated) {
      router.push('/')
    }
  }, [isAuthenticated, isLoading, isMounted, router])

  if (!isMounted || isLoading || !isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4" />
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    )
  }

  return (
    <SWRConfig
      value={{
        fetcher,
        revalidateOnFocus: false,
        revalidateOnReconnect: true,
        dedupingInterval: 5000,
        errorRetryCount: 3,
        shouldRetryOnError: true
      }}
    >
      <SidebarProvider>
        <div className="flex min-h-screen w-full bg-transparent relative overflow-hidden">
          {/* subtle inner background for dashboard content */}
          <div className="pointer-events-none absolute inset-0 z-0 opacity-80">
            <div className="absolute inset-0 bg-gradient-to-br from-background/90 via-background/80 to-background/95" />
          </div>

          <AppSidebar />

          <div className="flex-1 flex flex-col min-h-screen relative z-10 transition-all duration-300">

            <div className="flex-1 p-4 md:p-6 lg:p-8 overflow-auto scrollbar-thin scrollbar-thumb-muted-foreground/20 scrollbar-track-transparent">
              <div className="max-w-[1600px] mx-auto w-full h-full">
                {children}
              </div>
            </div>
          </div>
        </div>
      </SidebarProvider>
    </SWRConfig>
  )
}
