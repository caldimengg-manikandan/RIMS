'use client'

import React, { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { APIClient } from '@/app/dashboard/lib/api-client'
import { useAuth } from '@/app/dashboard/lib/auth-context'
import useSWR from 'swr'
import { fetcher } from '@/app/dashboard/lib/swr-fetcher'
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from '@/components/ui/popover'
import { Button } from '@/components/ui/button'
import { Bell, ChevronRight } from 'lucide-react'
import { ScrollArea } from '@/components/ui/scroll-area'

interface Notification {
    id: number
    notification_type: string
    title: string
    message: string
    is_read: boolean
    related_application_id?: number
    created_at: string
}

export function NotificationBell() {
    const { user } = useAuth()
    const router = useRouter()
    const [isOpen, setIsOpen] = useState(false)

    const { data: notifications = [], mutate } = useSWR<Notification[]>(
        user?.role === 'hr' ? '/api/notifications' : null,
        (url: string) => fetcher<Notification[]>(url),
        { refreshInterval: 30000 } // Auto-poll every 30s
    )

    const markAsRead = async (id: number) => {
        try {
            await APIClient.put(`/api/notifications/${id}/read`, {})
            mutate(prev =>
                prev?.map(n => n.id === id ? { ...n, is_read: true } : n),
                false
            )
        } catch {
            // Silently fail
        }
    }

    const unreadCount = notifications.filter(n => !n.is_read).length

    if (user?.role !== 'hr') return null

    return (
        <Popover open={isOpen} onOpenChange={setIsOpen}>
            <PopoverTrigger asChild>
                <Button variant="ghost" size="icon" className="relative h-10 w-10 rounded-full text-slate-200 hover:text-white hover:bg-blue-800/50">
                    <Bell className="h-5 w-5" />
                    {unreadCount > 0 && (
                        <span className="absolute -top-0.5 -right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-destructive text-[10px] font-bold text-destructive-foreground">
                            {unreadCount > 9 ? '9+' : unreadCount}
                        </span>
                    )}
                </Button>
            </PopoverTrigger>
            <PopoverContent className="w-[380px] p-0" align="end">
                <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-muted/30">
                    <h4 className="font-semibold text-sm">Notifications</h4>
                    {unreadCount > 0 && (
                        <span className="text-xs font-medium text-primary bg-primary/10 px-2 py-1 rounded-md">
                            {unreadCount} new
                        </span>
                    )}
                </div>
                <ScrollArea className="max-h-[400px]">
                    {notifications.length === 0 ? (
                        <div className="px-4 py-6 text-center text-sm text-muted-foreground">
                            No notifications yet
                        </div>
                    ) : (
                        <div className="flex flex-col">
                            {notifications.slice(0, 10).map(n => (
                                <button
                                    key={n.id}
                                    onClick={() => {
                                        if (!n.is_read) markAsRead(n.id)
                                        if (n.related_application_id) {
                                            router.push(`/dashboard/hr/applications/${n.related_application_id}`)
                                            setIsOpen(false)
                                        }
                                    }}
                                    className={`w-full text-left p-4 hover:bg-muted/50 transition-all border-l-4 group flex items-start gap-4 border-b border-border last:border-b-0
                                        ${!n.is_read ? 'bg-primary/5 border-l-primary' : 'bg-background border-l-transparent'}
                                    `}
                                >
                                    <div className="flex-1 min-w-0 pr-4 relative">
                                        <div className="flex justify-between items-start mb-1">
                                            <p className={`text-sm truncate pr-2 ${!n.is_read ? 'font-semibold text-foreground' : 'font-medium text-muted-foreground'}`}>
                                                {n.title}
                                            </p>
                                            <span className="text-[10px] text-muted-foreground/60 whitespace-nowrap mt-0.5">
                                                {new Date(n.created_at).toLocaleDateString()}
                                            </span>
                                        </div>
                                        <p className={`text-xs line-clamp-2 ${!n.is_read ? 'text-foreground/80' : 'text-muted-foreground/80'}`}>
                                            {n.message}
                                        </p>

                                        {n.related_application_id && (
                                            <div className={`absolute top-1/2 -translate-y-1/2 -right-2 transition-all duration-200 
                                                ${!n.is_read ? 'opacity-100 translate-x-0 cursor-pointer text-primary' : 'opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 cursor-pointer text-muted-foreground'}
                                            `}>
                                                <ChevronRight className="h-4 w-4" />
                                            </div>
                                        )}
                                    </div>
                                    {!n.is_read && (
                                        <span className="h-2 w-2 rounded-full bg-primary shrink-0 mt-1.5 shadow-sm shadow-primary/40 block" />
                                    )}
                                </button>
                            ))}
                        </div>
                    )}
                </ScrollArea>
            </PopoverContent>
        </Popover>
    )
}
