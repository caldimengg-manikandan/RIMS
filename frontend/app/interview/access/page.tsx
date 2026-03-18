'use client'

import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { API_BASE_URL } from '@/lib/config'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export default function InterviewAccessPage() {
    const router = useRouter()
    const [email, setEmail] = useState('')
    const [accessKey, setAccessKey] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [isLinkAccess, setIsLinkAccess] = useState(false)
    const [tokenFromUrl, setTokenFromUrl] = useState<string | null>(null)

    // Capture the optional token query parameter to prepopulate the key
    useEffect(() => {
        const params = new URLSearchParams(window.location.search)
        const tokenParam = params.get('token')
        if (tokenParam) {
            setAccessKey(tokenParam)
            setTokenFromUrl(tokenParam)
            setIsLinkAccess(true)
        }
    }, [])

    const handleAccess = async (e: React.FormEvent) => {
        e.preventDefault()
        setError(null)
        setIsLoading(true)

        try {
            const baseUrl = API_BASE_URL
            const response = await fetch(`${baseUrl}/api/interviews/access`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    email,
                    access_key: accessKey
                })
            })

            const data = await response.json()

            if (!response.ok) {
                throw new Error(data.detail || 'Access denied.')
            }

            // Store the temporary interview session token
            localStorage.setItem('auth_token', data.access_token)


            // Redirect to the interview session
            router.push(`/interview/${data.interview_id}`)

        } catch (err: any) {
            if (err.message === 'Failed to fetch') {
                setError('Unable to connect to the server. Please check your internet connection and try again.')
            } else {
                setError(err.message || 'Failed to access interview.')
            }
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-[#f0f9ff] dark:bg-slate-950 p-4 relative overflow-hidden">
            {/* grid background */}
            <div className="pointer-events-none absolute inset-0 z-0 flex justify-center">
                <div className="absolute inset-0 bg-[linear-gradient(to_right,#8080801a_1px,transparent_1px),linear-gradient(to_bottom,#8080801a_1px,transparent_1px)] bg-[size:40px_40px] dark:bg-[linear-gradient(to_right,#ffffff15_1px,transparent_1px),linear-gradient(to_bottom,#ffffff15_1px,transparent_1px)]" />
            </div>

            <Card className="max-w-md w-full shadow-lg border-2 border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-2xl relative z-10 animate-in fade-in slide-in-from-bottom-8 duration-700 ease-out fill-mode-both">
                <CardHeader className="space-y-3 pb-6 border-b border-border/50 text-center">
                    <div className="flex justify-center mb-2">
                        <div className="w-16 h-16 bg-blue-500/10 rounded-full flex items-center justify-center border border-blue-500/20">
                            <svg className="w-8 h-8 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                            </svg>
                        </div>
                    </div>
                    <CardTitle className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                        Secure Interview Access
                    </CardTitle>
                    <CardDescription className="text-base text-muted-foreground">
                        Please enter your email and the access key provided by your recruiter to enter the interview session.
                    </CardDescription>
                    
                    {isLinkAccess && (
                        <div className="mt-4 inline-flex items-center gap-2 px-3 py-1 bg-green-500/10 text-green-600 dark:text-green-400 rounded-full text-xs font-bold border border-green-500/20 mx-auto">
                            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                            </svg>
                            Secure Link Verified
                        </div>
                    )}
                </CardHeader>
                <CardContent className="pt-8">
                    <form onSubmit={handleAccess} className="space-y-6">
                        {error && (
                            <div className="p-4 bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 rounded-lg text-sm text-center font-medium animate-in fade-in slide-in-from-top-2">
                                {error}
                            </div>
                        )}
                        <div className="space-y-2">
                            <Label htmlFor="email" className="text-sm font-semibold text-foreground">Email Address</Label>
                            <Input
                                id="email"
                                type="email"
                                placeholder="you@example.com"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                required
                                className="h-12 bg-background/50 border-input transition-all duration-300 focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="key" className="text-sm font-semibold text-foreground">Access Key</Label>
                            <Input
                                id="key"
                                type="text"
                                placeholder="Paste your access key here"
                                value={accessKey}
                                onChange={(e) => setAccessKey(e.target.value.trim())}
                                required
                                className="h-12 tracking-widest font-mono text-center text-lg bg-background/50 border-input transition-all duration-300 focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                            />
                        </div>
                        <Button
                            type="submit"
                            className="w-full h-12 text-base font-bold tracking-wide rounded-xl shadow-md bg-blue-600 hover:bg-blue-700 text-white transition-all pt-[2px]"
                            disabled={isLoading || !email || !accessKey}
                        >
                            {isLoading ? (
                                <div className="flex items-center gap-2">
                                    <div className="h-4 w-4 border-2 border-white/50 border-t-white rounded-full animate-spin" />
                                    Verifying...
                                </div>
                            ) : (
                                "Enter Interview"
                            )}
                        </Button>
                        {!isLinkAccess && (
                             <p className="text-[10px] text-center text-muted-foreground uppercase tracking-widest font-bold">
                                Note: Direct links are recommended for a smoother experience
                             </p>
                        )}
                    </form>
                </CardContent>
            </Card>
        </div>
    )
}
