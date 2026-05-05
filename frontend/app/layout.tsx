import React, { Suspense } from "react"
import type { Metadata } from 'next'
import { AuthProvider } from '@/app/dashboard/lib/auth-context'
import { ThemeProvider } from '@/components/theme-provider'
import './globals.css'
import { Toaster } from '@/components/ui/sonner'
import { SWRProvider } from '@/app/dashboard/lib/swr-provider';
import { ErrorBoundary } from '@/components/error-boundary';
import { TooltipProvider } from "@/components/ui/tooltip"

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_FRONTEND_URL || 'http://localhost:3000'),
  title: 'CAL-RIMS - AI-Powered Recruitment Intelligence System',
  description: 'CAL-RIMS is an AI-powered automated recruitment platform for seamless hiring, empowering teams to find, evaluate, and hire top-tier talent efficiently.',
  openGraph: {
    title: 'CALRIMS - AI-Powered Recruitment Intelligence System',
    description: 'CALRIMS is an AI-powered automated recruitment platform for seamless hiring, empowering teams to find, evaluate, and hire top-tier talent efficiently.',
    images: ['/calrims/og-image.jpg'],
    type: 'website',
  },
  alternates: {
    canonical: 'https://caldimproducts.com/calrims',
  },
  generator: 'Caldim Engineering',
}

import { GlobalNavbar } from '@/components/global-navbar'
import { NavigationProgress } from '@/components/navigation-progress'

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" suppressHydrationWarning data-scroll-behavior="smooth">
      <body className="app-shell font-sans" suppressHydrationWarning>
        <SWRProvider>
          {/* Stable container to mitigate hydration issues from browser extensions */}
          <div className="relative flex flex-col h-screen overflow-hidden">
            {/* Global grid background for all pages */}
            <div className="app-shell-grid" />
            <div className="app-shell-watermark" />

            <AuthProvider>
              <ThemeProvider
                attribute="class"
                defaultTheme="system"
                enableSystem
                disableTransitionOnChange
              >
                <div className="app-shell-content flex flex-col h-full flex-1" suppressHydrationWarning>
                  <TooltipProvider delayDuration={300}>
                    <Suspense fallback={null}>
                      <NavigationProgress />
                    </Suspense>
                    <header className="shrink-0 flex flex-col sticky top-0 z-[100]">
                      <GlobalNavbar />
                    </header>
                    <main className="flex-1 min-h-0 overflow-y-auto w-full flex flex-col">
                      <ErrorBoundary>
                        <div className="h-full flex flex-col">
                          {children}
                        </div>
                      </ErrorBoundary>
                    </main>
                    <Toaster richColors position="top-right" />
                  </TooltipProvider>
                </div>
              </ThemeProvider>
            </AuthProvider>
          </div>
        </SWRProvider>
      </body>
    </html>
  )
}
