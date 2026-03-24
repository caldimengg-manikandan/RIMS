import React from "react"
import type { Metadata } from 'next'
import { Analytics } from '@vercel/analytics/next'
import { AuthProvider } from '@/app/dashboard/lib/auth-context'
import { ThemeProvider } from '@/components/theme-provider'
import './globals.css'
import { Toaster } from '@/components/ui/sonner'

export const metadata: Metadata = {
  title: 'CALRIMS | AI-Powered Recruitment',
  description: 'AI-powered automated recruitment platform for seamless hiring',
  generator: 'Caldim Engineering',
}

import { GlobalNavbar } from '@/components/global-navbar'

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="app-shell font-sans" suppressHydrationWarning>
        {/* Global grid background for all pages */}
        <div className="app-shell-grid" />
        <div className="app-shell-watermark" />

        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <AuthProvider>
            <div className="app-shell-content flex flex-col min-h-screen" suppressHydrationWarning>
              <GlobalNavbar />
              <div className="flex-1 w-full flex flex-col">
                {children}
              </div>
            </div>
          </AuthProvider>
          <Analytics />
          <Toaster />
        </ThemeProvider>
      </body>
    </html>
  )
}
