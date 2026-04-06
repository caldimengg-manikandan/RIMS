'use client'

import React, { useState, useEffect } from "react"
import { useAuth } from '@/app/dashboard/lib/auth-context'
import { useRouter, useSearchParams } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Loader2, ArrowRight, KeyRound } from 'lucide-react'

export default function VerifyPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { verify, login } = useAuth()

  const [email, setEmail] = useState('')
  const [otp, setOtp] = useState('')

  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    const emailParam = searchParams.get('email')

    if (emailParam) setEmail(emailParam)

    if (!emailParam) {
      setError('No email provided. Please go back and register again.')
    }
  }, [searchParams])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (otp.length !== 6) {
      setError('OTP must be exactly 6 digits')
      return
    }

    setIsSubmitting(true)

    try {
      await verify(email, otp)
      setSuccess(true)

      // Auto-redirect to login after just a moment
      setTimeout(() => {
        router.push('/auth/login')
      }, 2000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Verification failed')
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
              <KeyRound className="h-12 w-12" />
            </div>
            <h1 className="text-3xl font-bold text-foreground mb-2">Verify Account</h1>
            <p className="text-muted-foreground">We sent a 6-digit code to <br /> <span className="font-semibold text-foreground">{email || 'your email'}</span></p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg text-destructive text-sm backdrop-blur-sm">
                {error}
              </div>
            )}

            {success && (
              <div className="p-3 bg-primary/10 border border-primary/20 rounded-lg text-primary text-sm backdrop-blur-sm">
                Account verified successfully! It now awaits Super Admin approval before you can login.
              </div>
            )}

            <div className="space-y-2">
              <label htmlFor="otp" className="block text-sm font-medium text-foreground text-center">
                One-Time Password (OTP)
              </label>
              <div className="relative">
                <input
                  id="otp"
                  type="text"
                  maxLength={6}
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))} // only allow numbers
                  required
                  className="w-full text-center tracking-[0.5em] text-2xl font-bold pr-4 py-4 bg-background/50 border border-input rounded-xl focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all placeholder:text-muted-foreground/30 text-foreground"
                  placeholder="000000"
                  disabled={isSubmitting || success}
                />
              </div>
            </div>

            <Button
              type="submit"
              disabled={isSubmitting || success}
              className="w-full bg-primary hover:bg-primary/90 text-primary-foreground py-6 rounded-xl shadow-lg shadow-primary/25 transition-all duration-300 hover:-translate-y-0.5"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Verifying...
                </>
              ) : (
                <>
                  Verify Account
                  <ArrowRight className="ml-2 h-4 w-4" />
                </>
              )}
            </Button>
          </form>

        </CardContent>
      </Card>
    </div>
  )
}
