'use client'

import React from 'react'
import { usePathname } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/app/dashboard/lib/auth-context'
import { ChevronRight } from 'lucide-react'
import { UserNav } from '@/components/user-nav'
import { NotificationBell } from '@/components/notification-bell'
import { ThemeTogglerButton } from '@/components/animate-ui/components/buttons/theme-toggler'

export function GlobalNavbar() {
  const pathname = usePathname()
  const { isAuthenticated } = useAuth()

  const isDashboard = pathname?.startsWith('/dashboard')
  const isAuth = pathname?.startsWith('/auth')

  return (
    <nav className="sticky top-0 w-full z-50 bg-[#0a1a3c]/90 backdrop-blur-xl border-b border-white/5 shadow-2xl h-16 flex items-center shrink-0">
      <div className="w-full px-4 md:px-8 flex items-center justify-between">
        
        {/* Left: Logo and Title */}
        <Link href="/" className="flex items-center gap-2 group">
          <div className="bg-primary/20 p-1.5 rounded-lg group-hover:scale-110 transition-transform border border-primary/20">
             <img src="/logo-dark.png" alt="Logo" className="h-5 w-auto brightness-200" />
          </div>
          <span className="text-xl font-bold tracking-tight text-white hidden md:block">
            CALRIMS - Recruitment Intelligence & Management System
          </span>
        </Link>

        {/* Right: Dynamic Actions */}
        <div className="flex items-center gap-2 md:gap-4">
          <ThemeTogglerButton variant="ghost" className="rounded-full text-white/70 hover:text-white hover:bg-white/10" />
          
          {isDashboard ? (
            <>
              <NotificationBell />
              <UserNav />
            </>
          ) : isAuth ? (
            <Link href={pathname === '/auth/login' ? '/auth/register' : '/auth/login'}>
              <Button variant="outline" className="rounded-full border-white/20 text-white hover:bg-white/10 transition-colors font-semibold">
                {pathname === '/auth/login' ? 'Create Account' : 'Sign In'}
              </Button>
            </Link>
          ) : (
            !isAuthenticated ? (
              <>
                <Link href="/auth/login" className="hidden sm:block">
                  <Button
                    variant="ghost"
                    className="text-white/80 hover:text-white hover:bg-white/10 font-semibold"
                  >
                    Log in
                  </Button>
                </Link>
                <Link href="/auth/register">
                  <Button className="rounded-full px-6 bg-primary text-primary-foreground hover:bg-primary/90 font-bold transition-all hover:scale-105 active:scale-95 shadow-lg shadow-primary/20">
                    Get Started <ChevronRight className="ml-1 h-4 w-4" />
                  </Button>
                </Link>
              </>
            ) : (
              <Link href="/dashboard/hr">
                <Button className="rounded-full px-6 bg-primary text-primary-foreground hover:bg-primary/90 font-bold transition-all shadow-lg shadow-primary/20">
                  Go to Dashboard <ChevronRight className="ml-1 h-4 w-4" />
                </Button>
              </Link>
            )
          )}
        </div>
      </div>
    </nav>
  )
}
