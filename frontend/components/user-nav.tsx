'use client'

import { useCallback, useMemo } from 'react'

import {
    Avatar,
    AvatarFallback,
    AvatarImage,
} from '@/components/ui/avatar'
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuGroup,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/app/dashboard/lib/auth-context'
import { useRouter } from 'next/navigation'
import { LogOut, User as UserIcon, Settings, GitFork } from 'lucide-react'

export function UserNav() {
    const { user, logout } = useAuth()
    const router = useRouter()

    const handleLogout = useCallback(() => {
        // Clear all storage before state change to prevent sync flickering
        if (typeof window !== 'undefined') {
            localStorage.removeItem('rims_session_present')
            localStorage.removeItem('rims_offline_cache_v4')
        }
        logout()
        router.push('/calrims/')
    }, [logout, router])

    // Memoized initials for efficiency
    const initials = useMemo(() => {
        if (!user?.full_name) return 'U'
        return user.full_name
            .trim()
            .split(/\s+/)
            .map((n) => n[0])
            .join('')
            .toUpperCase()
            .slice(0, 2)
    }, [user?.full_name])

    const avatarUrl = useMemo(() => {
        return `https://api.dicebear.com/7.x/avataaars/svg?seed=${encodeURIComponent(user?.email || 'default')}`
    }, [user?.email])

    return (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="relative h-10 w-10 rounded-full hover:bg-slate-800/10 transition-all focus-visible:ring-offset-0 focus-visible:ring-0">
                    <Avatar className="h-10 w-10 border border-slate-200/20 shadow-sm">
                        <AvatarImage 
                            src={avatarUrl} 
                            alt={user?.full_name || 'User'} 
                            className="bg-background object-cover"
                        />
                        <AvatarFallback className="bg-primary/10 text-primary font-bold animate-in fade-in duration-500">
                            {initials}
                        </AvatarFallback>
                    </Avatar>
                </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-64" align="end" sideOffset={8} forceMount>
                <DropdownMenuLabel className="font-normal">
                    <div className="flex flex-col space-y-1.5 p-1">
                        <p className="text-sm font-semibold leading-none tracking-tight">{user?.full_name || 'User'}</p>
                        <p className="text-xs leading-none text-muted-foreground/80 truncate">
                            {user?.email || 'user@example.com'}
                        </p>
                    </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator className="opacity-50" />
                <DropdownMenuGroup>
                    <DropdownMenuItem className="cursor-pointer py-2.5 focus:bg-accent/40" onClick={() => router.push('/dashboard/settings')}>
                        <Settings className="mr-3 h-4 w-4 text-muted-foreground" />
                        <span>Settings</span>
                    </DropdownMenuItem>
                    <DropdownMenuItem className="cursor-pointer py-2.5 focus:bg-accent/40" onClick={() => router.push('/dashboard/repository')}>
                        <GitFork className="mr-3 h-4 w-4 text-muted-foreground" />
                        <span>Repository</span>
                    </DropdownMenuItem>
                </DropdownMenuGroup>
                <DropdownMenuSeparator className="opacity-50" />
                <DropdownMenuItem 
                    onClick={handleLogout} 
                    className="text-destructive focus:text-destructive focus:bg-destructive/5 cursor-pointer py-2.5"
                >
                    <LogOut className="mr-3 h-4 w-4" />
                    <span>Log out</span>
                </DropdownMenuItem>
            </DropdownMenuContent>
        </DropdownMenu>
    )
}
