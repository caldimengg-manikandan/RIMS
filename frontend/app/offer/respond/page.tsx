'use client'

import React, { useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { CheckCircle2, XCircle, Loader2, PartyPopper, Building2, ShieldAlert, AlertCircle, FileText, Calendar, Briefcase } from 'lucide-react'

export default function OfferRespondPage() {
    const searchParams = useSearchParams()
    const token = searchParams.get('token')
    const type = searchParams.get('type') // initial intent
    
    const [view, setView] = useState<'loading' | 'preview' | 'success' | 'error'>('loading')
    const [offerData, setOfferData] = useState<any>(null)
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [message, setMessage] = useState('')
    const [finalStatus, setFinalStatus] = useState<'accept' | 'reject' | null>(null)

    useEffect(() => {
        if (!token) {
            setView('error')
            setMessage('Invalid response link. Please contact HR.')
            return
        }
        fetchOfferDetails()
    }, [token])

    const fetchOfferDetails = async () => {
        try {
            const res = await fetch(`/api/onboarding/offer?token=${token}`)
            const data = await res.json()
            if (res.ok) {
                setOfferData(data)
                setView('preview')
            } else {
                setView('error')
                setMessage(data.detail || 'Failed to load offer details')
            }
        } catch (error) {
            setView('error')
            setMessage('Network error while loading offer.')
        }
    }

    const submitResponse = async (decisionType: 'accept' | 'reject') => {
        setIsSubmitting(true)
        try {
            const res = await fetch('/api/onboarding/respond', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token, response_type: decisionType })
            })
            
            const data = await res.json()
            if (res.ok) {
                setFinalStatus(decisionType)
                setView('success')
            } else {
                setView('error')
                setMessage(data.detail || 'Failed to submit response')
            }
        } catch (error) {
            setView('error')
            setMessage('Network error. Please try again.')
        } finally {
            setIsSubmitting(false)
        }
    }

    return (
        <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
            <Card className="max-w-xl w-full shadow-2xl border-none overflow-hidden">
                <div className="h-2 bg-primary w-full" />
                
                {view === 'loading' && (
                    <CardContent className="py-20 text-center">
                        <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto opacity-20" />
                        <p className="mt-4 text-muted-foreground font-medium">Loading your offer...</p>
                    </CardContent>
                )}

                {view === 'preview' && offerData && (
                    <>
                        <CardHeader className="text-center pt-10 pb-6 border-b bg-slate-50/50">
                            <div className="flex justify-center mb-4">
                                <div className="p-3 bg-primary/10 rounded-full">
                                    <FileText className="h-8 w-8 text-primary" />
                                </div>
                            </div>
                            <CardTitle className="text-2xl font-black">{offerData.company_name}</CardTitle>
                            <CardDescription>Official Employment Offer letter</CardDescription>
                        </CardHeader>
                        <CardContent className="py-10 px-10">
                            <div className="space-y-8">
                                <div className="bg-emerald-50 border border-emerald-100 p-6 rounded-2xl">
                                    <h3 className="text-emerald-800 font-bold flex items-center gap-2 mb-4">
                                        <CheckCircle2 className="h-5 w-5" />
                                        Offer Summary
                                    </h3>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                        <div className="space-y-1">
                                            <p className="text-xs text-emerald-600 font-bold uppercase tracking-wider">Candidate Name</p>
                                            <p className="text-lg font-black text-slate-800">{offerData.candidate_name}</p>
                                        </div>
                                        <div className="space-y-1">
                                            <p className="text-xs text-emerald-600 font-bold uppercase tracking-wider">Role</p>
                                            <p className="text-lg font-black text-slate-800">{offerData.job_title}</p>
                                        </div>
                                        <div className="space-y-1">
                                            <p className="text-xs text-emerald-600 font-bold uppercase tracking-wider">Joining Date</p>
                                            <p className="text-lg font-black text-slate-800">
                                                {new Date(offerData.joining_date).toLocaleDateString(undefined, { dateStyle: 'long' })}
                                            </p>
                                        </div>
                                    </div>
                                </div>

                                <div className="text-center space-y-4">
                                    <p className="text-sm text-muted-foreground px-4">
                                        Please review the details above. By clicking **Accept Offer**, you agree to the terms mentioned in the offer letter PDF sent to your email.
                                    </p>
                                    
                                    <div className="flex flex-col md:flex-row gap-3 pt-4">
                                        <Button 
                                            size="lg"
                                            className="flex-1 h-14 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl shadow-lg"
                                            onClick={() => submitResponse('accept')}
                                            disabled={isSubmitting}
                                        >
                                            {isSubmitting ? <Loader2 className="animate-spin h-5 w-5" /> : 'Accept Offer'}
                                        </Button>
                                        <Button 
                                            size="lg"
                                            variant="outline"
                                            className="flex-1 h-14 border-slate-200 hover:bg-red-50 hover:text-red-600 hover:border-red-200 font-bold rounded-xl"
                                            onClick={() => submitResponse('reject')}
                                            disabled={isSubmitting}
                                        >
                                            Decline Offer
                                        </Button>
                                    </div>
                                </div>
                            </div>
                        </CardContent>
                    </>
                )}

                {view === 'success' && (
                    <CardContent className="py-20 px-10 text-center space-y-6">
                        {finalStatus === 'accept' ? (
                            <>
                                <div className="flex justify-center">
                                    <div className="relative">
                                        <CheckCircle2 className="h-24 w-24 text-emerald-500" />
                                        <PartyPopper className="absolute -top-4 -right-4 h-12 w-12 text-amber-500 animate-bounce" />
                                    </div>
                                </div>
                                <h2 className="text-3xl font-black text-slate-800">Welcome Aboard!</h2>
                                <p className="text-muted-foreground text-lg">
                                    You have successfully <strong>Accepted</strong> the offer. 
                                    Our HR team will be in touch shortly to begin your onboarding journey.
                                </p>
                            </>
                        ) : (
                            <>
                                <div className="flex justify-center">
                                    <XCircle className="h-24 w-24 text-slate-300" />
                                </div>
                                <h2 className="text-3xl font-black text-slate-800">Offer Declined</h2>
                                <p className="text-muted-foreground text-lg">
                                    We respect your decision and wish you the very best in your future endeavors.
                                </p>
                            </>
                        )}
                        <div className="pt-8">
                            <Button variant="outline" onClick={() => window.close()} className="w-full h-12 rounded-xl">
                                Close Window
                            </Button>
                        </div>
                    </CardContent>
                )}

                {view === 'error' && (
                    <CardContent className="py-20 px-10 text-center space-y-6">
                        <div className="flex justify-center">
                            <div className="p-6 bg-red-50 rounded-full">
                                <ShieldAlert className="h-12 w-12 text-destructive" />
                            </div>
                        </div>
                        <h2 className="text-2xl font-black text-slate-800">Unable to Proceed</h2>
                        <div className="p-4 bg-red-50 text-red-700 border border-red-100 rounded-xl text-sm font-medium">
                            {message}
                        </div>
                        
                        {!isSubmitting ? (
                            <div className="space-y-4 pt-4 border-t">
                                <p className="text-muted-foreground text-sm font-medium">
                                    Experiencing an issue? Raise a support ticket and our team will get back to you.
                                </p>
                                
                                <div className="space-y-3">
                                    <div className="space-y-1">
                                        <p className="text-[10px] text-muted-foreground font-bold uppercase tracking-wider ml-1">Your Registered Email</p>
                                        <input 
                                            type="email"
                                            className="w-full p-3 text-sm border rounded-xl focus:ring-2 focus:ring-primary outline-none transition-all"
                                            placeholder="Enter the email you applied with..."
                                            value={offerData?.candidate_email || ''}
                                            onChange={(e) => setOfferData(prev => ({ ...prev, candidate_email: e.target.value }))}
                                        />
                                    </div>
                                    <div className="space-y-1">
                                        <p className="text-[10px] text-muted-foreground font-bold uppercase tracking-wider ml-1">Describe the Problem</p>
                                        <textarea 
                                            className="w-full min-h-[100px] p-4 text-sm border rounded-xl focus:ring-2 focus:ring-primary outline-none transition-all"
                                            placeholder="e.g. My joining date is incorrect, or the Accept button is showing an error..."
                                            value={message}
                                            onChange={(e) => setMessage(e.target.value)}
                                        />
                                    </div>
                                </div>

                                <Button 
                                    disabled={!message || !(offerData?.candidate_email)}
                                    onClick={async () => {
                                        setIsSubmitting(true)
                                        const emailToUse = offerData?.candidate_email?.trim()
                                        try {
                                            const res = await fetch('/api/support/ticket', {
                                                method: 'POST',
                                                headers: { 'Content-Type': 'application/json' },
                                                body: JSON.stringify({ 
                                                    email: emailToUse, 
                                                    access_key: token || 'onboarding_error', 
                                                    grievance_type: 'Onboarding Issue', 
                                                    description: message 
                                                })
                                            })
                                            if (res.ok) {
                                                setMessage('')
                                                setOfferData(prev => ({...prev, candidate_email: emailToUse}))
                                                setView('error')
                                                // Reset view with success msg
                                                const d = await res.json()
                                                alert("Ticket #"+d.id+" has been raised successfully. We will contact you at " + emailToUse)
                                            } else {
                                                const d = await res.json()
                                                // If token verification failed, try with magic key automatically
                                                if (res.status === 401 || res.status === 404) {
                                                     const retryRes = await fetch('/api/support/ticket', {
                                                        method: 'POST',
                                                        headers: { 'Content-Type': 'application/json' },
                                                        body: JSON.stringify({ 
                                                            email: emailToUse, 
                                                            access_key: 'onboarding_error', 
                                                            grievance_type: 'Onboarding Issue (Link Error)', 
                                                            description: `[AUTO_FALLBACK_LINK_ERROR]\nOriginal Token: ${token}\nMessage: ${message}` 
                                                        })
                                                     })
                                                     if (retryRes.ok) {
                                                        const d2 = await retryRes.json()
                                                        alert("Ticket #"+d2.id+" raised using onboarding fallback. We found your record.")
                                                        return
                                                     }
                                                }
                                                alert(d.detail || 'Failed to raise ticket.')
                                            }
                                        } catch (e) {
                                            alert('Network error.')
                                        } finally {
                                            setIsSubmitting(false)
                                        }
                                    }} 
                                    className="w-full h-12 rounded-xl font-bold bg-slate-900 hover:bg-slate-800"
                                >
                                    Raise Support Ticket
                                </Button>
                            </div>
                        ) : (
                            <div className="flex justify-center py-4">
                                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                            </div>
                        )}
                    </CardContent>
                )}
            </Card>
        </div>
    )
}
