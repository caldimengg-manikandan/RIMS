'use client'

import React from 'react'
import { LucideIcon } from 'lucide-react'
import { cn } from '@/app/dashboard/lib/utils'

interface PageHeaderProps {
  title: string
  description?: string
  icon: LucideIcon
  className?: string
  children?: React.ReactNode
}

export function PageHeader({ 
  title, 
  description, 
  icon: Icon, 
  className,
  children 
}: PageHeaderProps) {
  return (
    <div className={cn("flex flex-col sm:flex-row sm:items-center justify-between gap-6 mb-10", className)}>
      <div className="flex items-center gap-5">
        <div className="h-14 w-14 rounded-2xl bg-primary/10 flex items-center justify-center shrink-0 shadow-sm border border-primary/20 transition-all duration-300 hover:scale-105 hover:bg-primary/15 group">
          <Icon className="h-7 w-7 text-primary transition-transform duration-300 group-hover:rotate-3" />
        </div>
        <div className="space-y-1">
          <h1 className="text-4xl font-black text-foreground tracking-tight">
            {title}
          </h1>
          {description && (
            <p className="text-muted-foreground font-medium text-lg leading-tight opacity-80">
              {description}
            </p>
          )}
        </div>
      </div>
      {children && (
        <div className="flex items-center gap-4">
          {children}
        </div>
      )}
    </div>
  )
}
