'use client'

import React, { useState, useEffect } from "react"
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Lock, ArrowRight, Loader2, ArrowLeft, KeyRound } from 'lucide-react'

export default function ResetPasswordPage() {
    const router = useRouter()
    const searchParams = useSearchParams()
    const [email, setEmail] = useState('')
    const [otp, setOtp] = useState('')
    const [newPassword, setNewPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [error, setError] = useState('')
    const [success, setSuccess] = useState(false)

    useEffect(() => {
        const emailParam = searchParams.get('email')
        if (emailParam) {
            setEmail(emailParam)
        }
        const otpParam = searchParams.get('otp')
        if (otpParam) {
            setOtp(otpParam)
        }
    }, [searchParams])

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')

        if (newPassword !== confirmPassword) {
            setError("Passwords do not match")
            return
        }

        if (newPassword.length < 8) {
            setError("Password must be at least 8 characters long")
            return
        }

        setIsSubmitting(true)

        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:10000'}/api/auth/reset-password`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, otp, new_password: newPassword }),
            })

            const data = await response.json()

            if (!response.ok) {
                throw new Error(data.error || data.detail || 'Failed to reset password')
            }

            setSuccess(true)
            setTimeout(() => {
                router.push('/auth/login')
            }, 3000)
        } catch (err: any) {
            setError(err.message)
        } finally {
            setIsSubmitting(false)
        }
    }

    if (success) {
        return (
            <div className="flex items-center justify-center min-h-screen py-12 px-4">
                <Card className="w-full max-w-md shadow-2xl relative z-10 bg-card rounded-[2rem] border-border/40 text-center p-8">
                    <div className="flex justify-center mb-4 text-green-500">
                        <Lock className="h-12 w-12" />
                    </div>
                    <h1 className="text-3xl font-bold text-foreground mb-2">Password Reset!</h1>
                    <p className="text-muted-foreground mb-6">Your password has been successfully updated. Redirecting to login...</p>
                    <Link href="/auth/login" className="text-primary font-bold hover:underline">
                        Go to login now
                    </Link>
                </Card>
            </div>
        )
    }

    return (
        <div className="flex items-center justify-center min-h-screen py-12 px-4">
            <Card className="w-full max-w-md shadow-2xl relative z-10 bg-card rounded-[2rem] border-border/40">
                <CardContent className="p-8">
                    <div className="text-center mb-8">
                        <div className="flex justify-center mb-4 text-primary">
                            <KeyRound className="h-12 w-12" />
                        </div>
                        <h1 className="text-3xl font-bold text-foreground mb-2">Reset Password</h1>
                        <p className="text-muted-foreground">Enter the OTP sent to your email and your new password.</p>
                    </div>

                    {error && (
                        <div className="mb-6 p-4 bg-destructive/10 border border-destructive/20 text-destructive rounded-xl text-sm font-medium">
                            {error}
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div className="space-y-2">
                            <label className="block text-sm font-medium text-foreground">Email Address</label>
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                required
                                className="w-full px-4 py-3 bg-background/50 border border-input rounded-xl focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all placeholder:text-muted-foreground text-foreground"
                                placeholder="Email"
                                disabled={!!searchParams.get('email') || isSubmitting}
                            />
                        </div>

                        <div className="space-y-2">
                            <label className="block text-sm font-medium text-foreground">OTP Code</label>
                            <input
                                type="text"
                                value={otp}
                                onChange={(e) => setOtp(e.target.value)}
                                required
                                className="w-full px-4 py-3 bg-background/50 border border-input rounded-xl focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all placeholder:text-muted-foreground text-foreground text-center tracking-[0.5em] font-mono text-xl"
                                placeholder="000000"
                                maxLength={6}
                                disabled={isSubmitting}
                            />
                        </div>

                        <div className="space-y-2">
                            <label className="block text-sm font-medium text-foreground">New Password</label>
                            <input
                                type="password"
                                value={newPassword}
                                onChange={(e) => setNewPassword(e.target.value)}
                                required
                                className="w-full px-4 py-3 bg-background/50 border border-input rounded-xl focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all placeholder:text-muted-foreground text-foreground"
                                placeholder="••••••••"
                                disabled={isSubmitting}
                            />
                        </div>

                        <div className="space-y-2">
                            <label className="block text-sm font-medium text-foreground">Confirm New Password</label>
                            <input
                                type="password"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                required
                                className="w-full px-4 py-3 bg-background/50 border border-input rounded-xl focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all placeholder:text-muted-foreground text-foreground"
                                placeholder="••••••••"
                                disabled={isSubmitting}
                            />
                        </div>

                        <Button
                            type="submit"
                            disabled={isSubmitting}
                            className="w-full bg-primary hover:bg-primary/90 text-primary-foreground py-6 rounded-xl shadow-lg shadow-primary/25 transition-all duration-300 hover:-translate-y-0.5 mt-4"
                        >
                            {isSubmitting ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    Resetting...
                                </>
                            ) : (
                                <>
                                    Update Password
                                    <ArrowRight className="ml-2 h-4 w-4" />
                                </>
                            )}
                        </Button>
                    </form>

                    <div className="mt-8 text-center">
                        <Link href="/auth/login" className="inline-flex items-center text-primary hover:text-primary/80 font-bold hover:underline gap-2">
                            <ArrowLeft className="h-4 w-4" />
                            Back to login
                        </Link>
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}
