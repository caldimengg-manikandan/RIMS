'use client'

import React, { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { APIClient } from '@/app/dashboard/lib/api-client'
import { toast } from "sonner"
import { AlertTriangle, Send, CheckCircle2, ChevronLeft } from 'lucide-react'
import { useRouter } from 'next/navigation'

export default function SupportPage() {
    const router = useRouter()
    const [email, setEmail] = useState('')
    const [accessKey, setAccessKey] = useState('')
    const [issueType, setIssueType] = useState('technical')
    const [description, setDescription] = useState('')
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [isSubmitted, setIsSubmitted] = useState(false)

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()

        if (!email.trim() || !accessKey.trim() || !description.trim()) {
            toast.error("Please fill in all fields")
            return
        }

        try {
            setIsSubmitting(true)
            await APIClient.post('/api/tickets/grievance', {
                email: email,
                access_key: accessKey,
                issue_type: issueType,
                description: description
            })
            setIsSubmitted(true)
            toast.success("Grievance reported successfully")
        } catch (err: any) {
            console.error("Failed to report grievance:", err)
            toast.error(err.message || "Failed to submit report. Ensure your email and access key are correct.")
        } finally {
            setIsSubmitting(false)
        }
    }

    if (isSubmitted) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-muted/30 p-4">
                <Card className="max-w-md w-full border-none shadow-2xl bg-card animate-in fade-in zoom-in duration-500">
                    <CardHeader className="text-center pb-2">
                        <div className="mx-auto w-20 h-20 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center text-green-600 dark:text-green-400 mb-4 ring-8 ring-green-50 dark:ring-green-900/10">
                            <CheckCircle2 className="h-10 w-10" />
                        </div>
                        <CardTitle className="text-3xl font-black">Report Received</CardTitle>
                        <CardDescription className="text-lg pt-2 leading-relaxed">
                            Thank you for reaching out. Your grievance has been logged and sent to our HR team for review.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="text-center text-muted-foreground pb-8">
                        <p>We will review your submission and get back to you at <strong>{email}</strong> if any further action is needed.</p>
                    </CardContent>
                    <CardFooter className="flex justify-center border-t pt-6 bg-muted/30">
                        <Button variant="outline" onClick={() => router.push('/')} className="rounded-xl font-bold px-8">
                            Return to Home
                        </Button>
                    </CardFooter>
                </Card>
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-muted/30 flex flex-col items-center justify-center p-4 py-12">
            <div className="w-full max-w-2xl">
                <Button
                    variant="ghost"
                    onClick={() => router.back()}
                    className="mb-6 hover:bg-background/80 text-muted-foreground group font-semibold"
                >
                    <ChevronLeft className="mr-2 h-4 w-4 transition-transform group-hover:-translate-x-1" /> Back
                </Button>

                <Card className="border-none shadow-2xl bg-card overflow-hidden rounded-3xl animate-in slide-in-from-bottom-8 duration-700 ease-out fill-mode-both">
                    <div className="h-2 bg-gradient-to-r from-blue-600 to-indigo-600"></div>
                    <CardHeader className="space-y-4 p-8 md:p-12 pb-6">
                        <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900/30 rounded-2xl flex items-center justify-center text-blue-600 dark:text-blue-400 mb-2 rotate-3 transform-gpu transition-transform hover:rotate-0">
                            <AlertTriangle className="h-8 w-8" />
                        </div>
                        <div>
                            <CardTitle className="text-4xl font-black tracking-tight">Candidate Support</CardTitle>
                            <CardDescription className="text-lg mt-2 font-medium leading-relaxed">
                                Face an issue with your interview or have a technical grievance?
                                Report it here and our HR team will look into it.
                            </CardDescription>
                        </div>
                    </CardHeader>

                    <CardContent className="p-8 md:p-12 pt-0">
                        <form onSubmit={handleSubmit} className="space-y-8">
                            <div className="space-y-3">
                                <Label htmlFor="email" className="text-base font-bold flex items-center gap-2">
                                    Your Registered Email
                                </Label>
                                <Input
                                    id="email"
                                    type="email"
                                    placeholder="email@example.com"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    className="h-14 px-5 rounded-2xl border-2 focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 text-lg transition-all"
                                    required
                                />
                                <p className="text-sm text-muted-foreground">Please use the same email address you used for your job application.</p>
                            </div>

                            <div className="space-y-3">
                                <Label htmlFor="accessKey" className="text-base font-bold flex items-center gap-2">
                                    Interview Access Key
                                </Label>
                                <Input
                                    id="accessKey"
                                    type="text"
                                    placeholder="Paste your access key here"
                                    value={accessKey}
                                    onChange={(e) => setAccessKey(e.target.value.trim())}
                                    className="h-14 px-5 rounded-2xl border-2 tracking-widest font-mono focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 text-lg transition-all"
                                    required
                                />
                                <p className="text-sm text-muted-foreground">Find this in the invitation email sent by the recruiter.</p>
                            </div>

                            <div className="space-y-4">
                                <Label className="text-base font-bold">Nature of Grievance</Label>
                                <RadioGroup value={issueType} onValueChange={setIssueType} className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {[
                                        { id: 'technical', label: 'Technical Glitch', desc: 'Login issues, Audio/Video, etc.' },
                                        { id: 'interruption', label: 'Unexpected Termination', desc: 'Tab switch or browser crash' },
                                        { id: 'misconduct', label: 'Misconduct Appeal', desc: 'Appeal against a warning' },
                                        { id: 'other', label: 'Other Grievance', desc: 'Process or scheduling issues' }
                                    ].map((opt) => (
                                        <label key={opt.id} htmlFor={opt.id} className={`relative flex flex-col p-4 rounded-2xl border-2 transition-all cursor-pointer group ${issueType === opt.id
                                            ? 'border-blue-600 bg-blue-50/10 ring-4 ring-blue-500/5'
                                            : 'border-border hover:border-blue-300 hover:bg-muted/30'
                                            }`}>
                                            <div className="flex items-center justify-between mb-1">
                                                <span className="font-bold text-lg">{opt.label}</span>
                                                <RadioGroupItem value={opt.id} id={opt.id} className="sr-only" />
                                                <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${issueType === opt.id ? 'border-blue-600 bg-blue-600' : 'border-muted-foreground/30'
                                                    }`}>
                                                    {issueType === opt.id && <div className="w-2 h-2 rounded-full bg-white" />}
                                                </div>
                                            </div>
                                            <span className="text-sm text-muted-foreground font-medium">{opt.desc}</span>
                                        </label>
                                    ))}
                                </RadioGroup>
                            </div>

                            <div className="space-y-3">
                                <Label htmlFor="description" className="text-base font-bold">Detailed Description</Label>
                                <Textarea
                                    id="description"
                                    placeholder="Please provide as much detail as possible..."
                                    className="min-h-[160px] p-5 rounded-2xl border-2 focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 text-lg transition-all resize-none shadow-sm"
                                    value={description}
                                    onChange={(e) => setDescription(e.target.value)}
                                    required
                                />
                                <p className="text-xs text-muted-foreground italic">Your IP address and session data will be correlated for verification.</p>
                            </div>

                            <Button
                                type="submit"
                                className="w-full h-16 rounded-2xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-black text-xl shadow-xl shadow-blue-500/20 active:scale-[0.98] transition-all disabled:opacity-50"
                                disabled={isSubmitting}
                            >
                                {isSubmitting ? (
                                    <>Processing...</>
                                ) : (
                                    <>
                                        Submit Grievance <Send className="ml-3 h-6 w-6" />
                                    </>
                                )}
                            </Button>
                        </form>
                    </CardContent>
                </Card>

                <div className="mt-12 text-center pb-8 animate-in fade-in duration-1000 delay-500">
                    <p className="text-muted-foreground font-medium">
                        Secure AI Interview System • Support Portal
                    </p>
                    <p className="text-xs text-muted-foreground/60 mt-2">
                        For immediate technical assistance, please contact caldiminternship@gmail.com

                    </p>
                </div>
            </div>
        </div>
    )
}
