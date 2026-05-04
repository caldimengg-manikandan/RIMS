'use client'

import React, { useState } from "react"
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Mail, ArrowRight, Loader2, ArrowLeft } from 'lucide-react'

export default function ForgotPasswordPage() {
    const [email, setEmail] = useState('')
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [isSent, setIsSent] = useState(false)

    const [error, setError] = useState('')

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setIsSubmitting(true)
        setError('')

        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:10000'}/api/auth/forgot-password`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email }),
            })

            const data = await response.json()

            if (!response.ok) {
                throw new Error(data.error || data.detail || 'Failed to send reset email')
            }

            setIsSent(true)
        } catch (err: any) {
            setError(err.message)
        } finally {
            setIsSubmitting(false)
        }
    }

    return (
        <div className="flex items-center justify-center min-h-screen py-12 px-4">
            <Card className="w-full max-w-md shadow-2xl relative z-10 bg-card rounded-[2rem] border-border/40">
                <CardContent className="p-8">

                    <div className="text-center mb-8">
                        <div className="flex justify-center mb-4 text-primary">
                            <Mail className="h-12 w-12" />
                        </div>
                        <h1 className="text-3xl font-bold text-foreground mb-2">
                            {isSent ? 'Check your email' : 'Forgot password?'}
                        </h1>
                        <p className="text-muted-foreground">
                            {isSent
                                ? `We sent a password reset link to ${email}`
                                : "No worries, we'll send you reset instructions."}
                        </p>
                    </div>

                    {error && (
                        <div className="mb-6 p-4 bg-destructive/10 border border-destructive/20 text-destructive rounded-xl text-sm font-medium">
                            {error}
                        </div>
                    )}

                    {!isSent ? (
                        <form onSubmit={handleSubmit} className="space-y-6">
                            <div className="space-y-2">
                                <label htmlFor="email" className="block text-sm font-medium text-foreground">
                                    Email Address
                                </label>
                                <div className="relative">
                                    <div className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                                        <Mail className="h-4 w-4" />
                                    </div>
                                    <input
                                        id="email"
                                        type="email"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        required
                                        className="w-full pl-10 pr-4 py-3 bg-background/50 border border-input rounded-xl focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all placeholder:text-muted-foreground text-foreground"
                                        placeholder="Enter email"
                                        disabled={isSubmitting}
                                    />
                                </div>
                            </div>

                            <Button
                                type="submit"
                                disabled={isSubmitting}
                                className="w-full bg-primary hover:bg-primary/90 text-primary-foreground py-6 rounded-xl shadow-lg shadow-primary/25 transition-all duration-300 hover:-translate-y-0.5"
                            >
                                {isSubmitting ? (
                                    <>
                                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                        Sending...
                                    </>
                                ) : (
                                    <>
                                        Reset Password
                                        <ArrowRight className="ml-2 h-4 w-4" />
                                    </>
                                )}
                            </Button>
                        </form>
                    ) : (
                        <div className="space-y-4">
                            <Button
                                onClick={() => setIsSent(false)}
                                variant="outline"
                                className="w-full py-6 rounded-xl border-border/60 hover:bg-muted"
                            >
                                Didn't receive the email? Click to retry
                            </Button>
                            <Link href={`/auth/reset-password?email=${encodeURIComponent(email)}`} className="block">
                                <Button className="w-full py-6 rounded-xl bg-primary text-primary-foreground">
                                    Go to reset page
                                    <ArrowRight className="ml-2 h-4 w-4" />
                                </Button>
                            </Link>
                        </div>
                    )}

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
