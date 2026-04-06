'use client'

import React, { useState, useRef, useEffect } from 'react'
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { APIClient } from '@/app/dashboard/lib/api-client'
import { toast } from "sonner"
import { Star, AlertTriangle, Send, CheckCircle2 } from 'lucide-react'

interface IssueReportDialogProps {
    open: boolean
    onOpenChange: (open: boolean) => void
    interviewId: string | number
    onSubmitted?: () => void
}

export function IssueReportDialog({ open, onOpenChange, interviewId, onSubmitted }: IssueReportDialogProps) {
    const [issueType, setIssueType] = useState('interruption')
    const [description, setDescription] = useState('')
    const [isSubmitting, setIsSubmitting] = useState(false)

    const handleSubmit = async () => {
        if (!description.trim()) {
            toast.error("Please provide details about what happened")
            return
        }

        try {
            setIsSubmitting(true)
            await APIClient.post('/api/tickets', {
                interview_id: Number(interviewId),
                issue_type: issueType,
                description: description
            })
            toast.success("Issue reported successfully. HR will review it.")
            onOpenChange(false)
            onSubmitted?.()
        } catch (err) {
            console.error("Failed to report issue:", err)
            toast.error("Failed to submit report. Please try again.")
        } finally {
            setIsSubmitting(false)
        }
    }

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[500px] bg-card border-border">
                <DialogHeader>
                    <DialogTitle className="text-2xl font-black flex items-center gap-2">
                        <AlertTriangle className="text-amber-500 h-6 w-6" />
                        Report an Issue
                    </DialogTitle>
                    <DialogDescription className="text-base">
                        Was your interview interrupted? Let us know what happened so HR can review your session.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-6 py-4">
                    <div className="space-y-3">
                        <Label className="text-sm font-bold">What kind of issue did you face?</Label>
                        <RadioGroup value={issueType} onValueChange={setIssueType} className="grid grid-cols-1 gap-3">
                            <div className="flex items-center space-x-3 p-3 rounded-xl border border-border hover:bg-muted/50 transition-colors cursor-pointer">
                                <RadioGroupItem value="interruption" id="interruption" />
                                <Label htmlFor="interruption" className="flex-1 font-semibold cursor-pointer">
                                    Unexpected Interruption (Tab switch/browser crash)
                                </Label>
                            </div>
                            <div className="flex items-center space-x-3 p-3 rounded-xl border border-border hover:bg-muted/50 transition-colors cursor-pointer">
                                <RadioGroupItem value="technical" id="technical" />
                                <Label htmlFor="technical" className="flex-1 font-semibold cursor-pointer">
                                    Technical Glitch (Audio/Video/UI issues)
                                </Label>
                            </div>
                            <div className="flex items-center space-x-3 p-3 rounded-xl border border-border hover:bg-muted/50 transition-colors cursor-pointer">
                                <RadioGroupItem value="misconduct_appeal" id="misconduct_appeal" />
                                <Label htmlFor="misconduct_appeal" className="flex-1 font-semibold cursor-pointer">
                                    Appeal Misconduct Warning
                                </Label>
                            </div>
                        </RadioGroup>
                    </div>

                    <div className="space-y-3">
                        <Label htmlFor="description" className="text-sm font-bold">Please describe in detail:</Label>
                        <Textarea
                            id="description"
                            placeholder="I switched tabs by mistake because of a notification..."
                            className="min-h-[120px] rounded-xl border-2 focus:ring-primary/20"
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                        />
                    </div>
                </div>

                <DialogFooter>
                    <Button variant="ghost" onClick={() => onOpenChange(false)} disabled={isSubmitting}>Cancel</Button>
                    <Button
                        className="bg-primary hover:bg-primary/90 font-bold px-8 shadow-lg shadow-primary/20"
                        onClick={handleSubmit}
                        disabled={isSubmitting}
                    >
                        {isSubmitting ? "Submitting..." : "Submit Report"}
                        <Send className="ml-2 h-4 w-4" />
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    )
}

interface FeedbackDialogProps {
    open: boolean
    onOpenChange: (open: boolean) => void
    interviewId: string | number
}

export function FeedbackDialog({ open, onOpenChange, interviewId }: FeedbackDialogProps) {
    const [rating, setRating] = useState(0)
    const [hoverRating, setHoverRating] = useState(0)
    const [feedback, setFeedback] = useState('')
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [isSubmitted, setIsSubmitted] = useState(false)
    const closeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

    useEffect(() => {
        return () => {
            if (closeTimerRef.current) clearTimeout(closeTimerRef.current)
        }
    }, [])

    const handleSubmit = async () => {
        if (rating === 0) {
            toast.error("Please select a rating")
            return
        }

        try {
            setIsSubmitting(true)
            await APIClient.post('/api/tickets/feedback', {
                interview_id: Number(interviewId),
                ui_ux_rating: rating,
                feedback_text: feedback
            })
            setIsSubmitted(true)
            toast.success("Thank you for your feedback!")
            if (closeTimerRef.current) clearTimeout(closeTimerRef.current)
            closeTimerRef.current = setTimeout(() => onOpenChange(false), 2000)
        } catch (err) {
            console.error("Failed to submit feedback:", err)
            // Even if it fails (e.g. duplicate), we don't want to annoy the user
            onOpenChange(false)
        } finally {
            setIsSubmitting(false)
        }
    }

    if (isSubmitted) {
        return (
            <Dialog open={open} onOpenChange={onOpenChange}>
                <DialogContent className="sm:max-w-[400px] text-center py-12 bg-card border-border">
                    <div className="flex flex-col items-center gap-4">
                        <div className="h-20 w-20 rounded-full bg-green-100 flex items-center justify-center text-green-600 mb-2">
                            <CheckCircle2 className="h-10 w-10" />
                        </div>
                        <h2 className="text-2xl font-black">Feedback Received!</h2>
                        <p className="text-muted-foreground">We appreciate your input to help us improve the experience.</p>
                    </div>
                </DialogContent>
            </Dialog>
        )
    }

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[450px] bg-card border-border">
                <DialogHeader>
                    <DialogTitle className="text-2xl font-black">How was your experience?</DialogTitle>
                    <DialogDescription className="text-base">
                        Your feedback helps us make the interview process smoother for everyone.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-8 py-6">
                    <div className="flex flex-col items-center gap-3">
                        <Label className="text-sm font-bold uppercase tracking-widest text-muted-foreground">UI / UX Rating</Label>
                        <div className="flex gap-1">
                            {[1, 2, 3, 4, 5].map((star) => (
                                <button
                                    key={star}
                                    className="p-1 transition-transform active:scale-90"
                                    onMouseEnter={() => setHoverRating(star)}
                                    onMouseLeave={() => setHoverRating(0)}
                                    onClick={() => setRating(star)}
                                >
                                    <Star
                                        className={`h-10 w-10 transition-colors ${(hoverRating || rating) >= star
                                                ? "fill-primary text-primary"
                                                : "text-muted-foreground/30"
                                            }`}
                                    />
                                </button>
                            ))}
                        </div>
                        <p className="text-xs font-medium text-muted-foreground">
                            {rating === 5 ? "Excellent!" : rating === 4 ? "Very Good" : rating === 3 ? "Good" : rating === 2 ? "Fair" : rating === 1 ? "Poor" : "Select a rating"}
                        </p>
                    </div>

                    <div className="space-y-3">
                        <Label htmlFor="feedback" className="text-sm font-bold">Any specific comments or suggestions?</Label>
                        <Textarea
                            id="feedback"
                            placeholder="The voice recognition worked great, but..."
                            className="min-h-[100px] rounded-xl border-2 focus:ring-primary/20"
                            value={feedback}
                            onChange={(e) => setFeedback(e.target.value)}
                        />
                    </div>
                </div>

                <DialogFooter>
                    <Button variant="ghost" onClick={() => onOpenChange(false)} disabled={isSubmitting}>Skip</Button>
                    <Button
                        className="bg-primary hover:bg-primary/90 font-bold px-8 shadow-lg shadow-primary/20"
                        onClick={handleSubmit}
                        disabled={isSubmitting || rating === 0}
                    >
                        {isSubmitting ? "Sending..." : "Submit Feedback"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    )
}
