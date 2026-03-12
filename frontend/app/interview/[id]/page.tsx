'use client'

import React, { useEffect, useState, useRef, useMemo } from 'react'
import { APIClient } from '@/app/dashboard/lib/api-client'
import { useParams, useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import {
    Mic, MicOff, Loader2, ChevronLeft, ChevronRight,
    CheckCircle2, Circle, Brain, BookOpen, AlertTriangle,
    Clock, Target, ListChecks, Lock, Sidebar as SidebarIcon
} from 'lucide-react'
import { IssueReportDialog, FeedbackDialog } from '@/components/interview-support'

interface Question {
    id: number
    question_number: number
    question_text: string
    question_type: string
    question_options?: string // JSON string
    is_answered?: boolean
}

interface InterviewData {
    id: number
    locked_skill: string
    total_questions: number
    status: string
}

export default function InterviewPage() {
    const params = useParams()
    const router = useRouter()
    const interviewId = params.id as string

    const [questions, setQuestions] = useState<Question[]>([])
    const [currentIndex, setCurrentIndex] = useState(0)
    const [answer, setAnswer] = useState('')
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [isLoading, setIsLoading] = useState(true)
    const [interviewStatus, setInterviewStatus] = useState('loading')
    const [interviewData, setInterviewData] = useState<InterviewData | null>(null)
    const [warnings, setWarnings] = useState(0)

    // Support States
    const [showIssueDialog, setShowIssueDialog] = useState(false)
    const [showFeedbackDialog, setShowFeedbackDialog] = useState(false)

    // Refs to always have live values inside event listeners (avoid stale closures)
    const warningsRef = useRef(0)
    const interviewStatusRef = useRef('loading')
    const hiddenSinceRef = useRef<number | null>(null)
    const recognitionRef = useRef<any>(null)

    // Derived Sections
    const aptitudeQuestions = useMemo(() => questions.filter(q => q.question_type === 'aptitude'), [questions])
    const technicalQuestions = useMemo(() => questions.filter(q => q.question_type === 'technical'), [questions])
    const behavioralQuestions = useMemo(() => questions.filter(q => q.question_type === 'behavioral'), [questions])

    const currentQuestion = questions[currentIndex]
    const totalQuestions = questions.length
    const answeredCount = questions.filter(q => q.is_answered).length

    // Keep refs in sync with state so event handlers always see fresh values
    useEffect(() => { warningsRef.current = warnings }, [warnings])
    useEffect(() => { interviewStatusRef.current = interviewStatus }, [interviewStatus])

    useEffect(() => {
        const handleVisibilityChange = async () => {
            if (document.hidden) {
                // Record when we became hidden
                hiddenSinceRef.current = Date.now()
            } else {
                // Document became visible again
                const hiddenSince = hiddenSinceRef.current
                hiddenSinceRef.current = null

                if (hiddenSince === null) return

                const hiddenDurationMs = Date.now() - hiddenSince

                // Only count as a violation if hidden for > 500ms
                // (shorter durations are from browser-native UI: autocomplete, tooltips, enter key, etc.)
                if (hiddenDurationMs < 500) return

                if (interviewStatusRef.current !== 'active') return

                const newWarnings = warningsRef.current + 1
                warningsRef.current = newWarnings
                setWarnings(newWarnings)

                if (newWarnings >= 3) {
                    try {
                        await APIClient.post(`/api/interviews/${interviewId}/end`, {})
                    } catch (error) {
                        console.log("Failed to end interview", error)
                    }
                    setInterviewStatus('completed')
                    setShowIssueDialog(true)
                } else {
                    alert(`Warning ${newWarnings}/2: Switching away from this tab is not allowed. A third violation will terminate your session.`)
                }
            }
        }

        document.addEventListener('visibilitychange', handleVisibilityChange)

        loadData()

        return () => {
            document.removeEventListener('visibilitychange', handleVisibilityChange)
            if (recognitionRef.current) recognitionRef.current.stop()
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [interviewId])

    const loadData = async () => {
        try {
            setIsLoading(true)
            const [data, qs] = await Promise.all([
                APIClient.get<InterviewData>(`/api/interviews/${interviewId}/stage`),
                APIClient.get<Question[]>(`/api/interviews/${interviewId}/questions`)
            ])

            setInterviewData(data)
            setQuestions(qs)

            if (data.status === 'completed') {
                setInterviewStatus('completed')
            } else {
                // Find first unanswered
                const firstUnanswered = qs.findIndex(q => !q.is_answered)
                setCurrentIndex(firstUnanswered !== -1 ? firstUnanswered : 0)
                setInterviewStatus('active')
            }
        } catch (err) {
            console.error("Failed to load interview", err)
            setInterviewStatus('error')
        } finally {
            setIsLoading(false)
        }
    }

    const handleSubmit = async () => {
        if (!answer.trim() || !currentQuestion) return
        setIsSubmitting(true)
        try {
            const res = await APIClient.post<any>(`/api/interviews/${interviewId}/submit-answer`, {
                question_id: currentQuestion.id,
                answer_text: answer
            })

            if (res && res.terminated) {
                // If it was terminated by backend explicitly (like misconduct or low score)
                await finishInterview()
                return
            }

            // Update local state
            const updatedQuestions = questions.map((q, idx) =>
                idx === currentIndex ? { ...q, is_answered: true } : q
            )
            setQuestions(updatedQuestions)
            setAnswer('')

            // Auto-move to next unanswered or just next
            if (currentIndex < totalQuestions - 1) {
                setCurrentIndex(currentIndex + 1)
            } else {
                // Check if ALL are answered
                const isFinished = updatedQuestions.every(q => q.is_answered)
                if (isFinished) {
                    finishInterview()
                }
            }
        } catch (err: any) {
            console.error("Submission error:", err)
            alert(err.message || "Failed to submit answer. Please try again.")
        } finally {
            setIsSubmitting(false)
        }
    }

    const finishInterview = async () => {
        try {
            await APIClient.post(`/api/interviews/${interviewId}/end`, {})
            setInterviewStatus('completed')
            setShowFeedbackDialog(true)
        } catch (err) {
            console.error("Error finishing interview", err)
        }
    }

    if (interviewStatus === 'error') {
        return (
            <div className="min-h-screen bg-[#f8fafc] flex items-center justify-center p-6">
                <div className="max-w-md w-full bg-white rounded-3xl shadow-xl p-10 text-center border border-slate-200">
                    <div className="w-20 h-20 bg-red-50 rounded-full flex items-center justify-center mx-auto mb-6 border border-red-100">
                        <AlertTriangle className="w-10 h-10 text-red-500" />
                    </div>
                    <h1 className="text-2xl font-bold text-slate-900 mb-2">Access Error</h1>
                    <p className="text-slate-500 mb-8">
                        We encountered an issue loading your interview session. This may be due to an expired session or unauthorized access.
                    </p>
                    <Button
                        className="w-full bg-slate-900 hover:bg-slate-800 text-white font-bold h-12 rounded-xl"
                        onClick={() => router.push('/interview/access')}
                    >
                        Try Again / Re-login
                    </Button>
                </div>
            </div>
        )
    }

    if (isLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-[#f8fafc]">
                <div className="text-center">
                    <div className="relative w-20 h-20 mx-auto mb-6">
                        <div className="absolute inset-0 rounded-full border-4 border-blue-500/20 border-t-blue-600 animate-spin"></div>
                    </div>
                    <p className="text-slate-500 font-medium animate-pulse">Initializing Secure Interview Environment...</p>
                </div>
            </div>
        )
    }

    if (interviewStatus === 'completed') {
        return (
            <div className="min-h-screen bg-[#f1f5f9] flex items-center justify-center p-6">
                <div className="max-w-xl w-full bg-white rounded-3xl shadow-2xl p-12 text-center border border-slate-200">
                    <div className="w-24 h-24 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-8 border border-green-200">
                        <CheckCircle2 className="w-12 h-12 text-green-600" />
                    </div>
                    <h1 className="text-4xl font-black text-slate-900 mb-4 tracking-tight">Interview Complete</h1>
                    <p className="text-slate-600 text-lg mb-10 leading-relaxed">
                        Excellent work! Your responses have been captured and are being analyzed by our AI system. Our HR team will review your report shortly.
                    </p>
                    <div className="grid grid-cols-2 gap-4">
                        <Button
                            className="bg-blue-600 hover:bg-blue-700 text-white font-bold h-14 rounded-2xl shadow-lg shadow-blue-500/20"
                            onClick={() => router.push('/jobs')}
                        >
                            Back to Jobs
                        </Button>
                        <Button
                            variant="outline"
                            className="font-bold h-14 rounded-2xl border-2"
                            onClick={() => setShowFeedbackDialog(true)}
                        >
                            Give Feedback
                        </Button>
                    </div>
                </div>
            </div>
        )
    }

    const options = currentQuestion?.question_options ? JSON.parse(currentQuestion.question_options) : []
    const isAptitude = currentQuestion?.question_type === 'aptitude'

    return (
        <div className="min-h-screen bg-[#f8fafc] flex">
            {/* Sidebar */}
            <div className="w-80 bg-white border-r border-slate-200 flex flex-col shadow-sm">
                <div className="p-6 border-b border-slate-100">
                    <h2 className="text-xs font-black text-slate-400 uppercase tracking-[0.2em] mb-4">Interview Sections</h2>

                    {/* Aptitude Section */}
                    <div className="mb-8">
                        <div className="flex items-center justify-between mb-3">
                            <h3 className={`font-bold transition-colors ${isAptitude ? 'text-blue-600' : 'text-slate-700'}`}>Aptitude</h3>
                            <span className="text-xs font-bold text-slate-400 bg-slate-50 px-2 py-1 rounded-md border border-slate-100">
                                {aptitudeQuestions.filter(q => q.is_answered).length}/{aptitudeQuestions.length}
                            </span>
                        </div>
                        <div className="grid grid-cols-5 gap-2">
                            {aptitudeQuestions.map((q, index) => (
                                <button
                                    key={q.id}
                                    onClick={() => {
                                        const idx = questions.findIndex(item => item.id === q.id)
                                        setCurrentIndex(idx)
                                        setAnswer('')
                                    }}
                                    className={`w-9 h-9 rounded-full text-xs font-bold transition-all border-2 flex items-center justify-center
                                        ${currentIndex === questions.findIndex(item => item.id === q.id)
                                            ? 'bg-blue-600 border-blue-600 text-white shadow-lg shadow-blue-500/30 scale-110 z-10'
                                            : q.is_answered
                                                ? 'bg-blue-50 border-blue-200 text-blue-600'
                                                : 'bg-white border-slate-100 text-slate-400 hover:border-slate-300'
                                        }`}
                                >
                                    {index + 1}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Technical Section */}
                    <div className="mb-8">
                        <div className="flex items-center justify-between mb-3">
                            <h3 className={`font-bold transition-colors ${currentQuestion?.question_type === 'technical' ? 'text-blue-600' : 'text-slate-700'}`}>Technical</h3>
                            <span className="text-xs font-bold text-slate-400 bg-slate-50 px-2 py-1 rounded-md border border-slate-100">
                                {technicalQuestions.filter(q => q.is_answered).length}/{technicalQuestions.length}
                            </span>
                        </div>
                        <div className="grid grid-cols-5 gap-2">
                            {technicalQuestions.map((q, index) => (
                                <button
                                    key={q.id}
                                    onClick={() => {
                                        const idx = questions.findIndex(item => item.id === q.id)
                                        setCurrentIndex(idx)
                                        setAnswer('')
                                    }}
                                    className={`w-9 h-9 rounded-full text-xs font-bold transition-all border-2 flex items-center justify-center
                                        ${currentIndex === questions.findIndex(item => item.id === q.id)
                                            ? 'bg-blue-600 border-blue-600 text-white shadow-lg shadow-blue-500/30 scale-110 z-10'
                                            : q.is_answered
                                                ? 'bg-blue-50 border-blue-200 text-blue-600'
                                                : 'bg-white border-slate-100 text-slate-400 hover:border-slate-300'
                                        }`}
                                >
                                    {index + 1}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Behavioral Section */}
                    <div>
                        <div className="flex items-center justify-between mb-3">
                            <h3 className={`font-bold transition-colors ${currentQuestion?.question_type === 'behavioral' ? 'text-blue-600' : 'text-slate-700'}`}>Behavioral</h3>
                            <span className="text-xs font-bold text-slate-400 bg-slate-50 px-2 py-1 rounded-md border border-slate-100">
                                {behavioralQuestions.filter(q => q.is_answered).length}/{behavioralQuestions.length}
                            </span>
                        </div>
                        <div className="grid grid-cols-5 gap-2">
                            {behavioralQuestions.map((q, index) => (
                                <button
                                    key={q.id}
                                    onClick={() => {
                                        const idx = questions.findIndex(item => item.id === q.id)
                                        setCurrentIndex(idx)
                                        setAnswer('')
                                    }}
                                    className={`w-9 h-9 rounded-full text-xs font-bold transition-all border-2 flex items-center justify-center
                                        ${currentIndex === questions.findIndex(item => item.id === q.id)
                                            ? 'bg-blue-600 border-blue-600 text-white shadow-lg shadow-blue-500/30 scale-110 z-10'
                                            : q.is_answered
                                                ? 'bg-blue-50 border-blue-200 text-blue-600'
                                                : 'bg-white border-slate-100 text-slate-400 hover:border-slate-300'
                                        }`}
                                >
                                    {index + 1}
                                </button>
                            ))}
                        </div>
                    </div>
                </div>

                <div className="mt-auto p-6 border-t border-slate-100">
                    <button
                        onClick={() => setShowIssueDialog(true)}
                        className="w-full flex items-center justify-center gap-2 p-3 rounded-xl border-2 border-slate-100 text-slate-500 font-bold text-sm hover:bg-slate-50 hover:text-slate-700 transition-colors"
                    >
                        <AlertTriangle className="w-4 h-4" />
                        Report an Issue
                    </button>
                </div>
            </div>

            {/* Main Wrapper */}
            <div className="flex-1 flex flex-col relative overflow-hidden">
                {/* Background Grid */}
                <div className="absolute inset-0 bg-[linear-gradient(to_right,#e2e8f0_1px,transparent_1px),linear-gradient(to_bottom,#e2e8f0_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] pointer-events-none opacity-[0.4]"></div>

                {/* Header */}
                <header className="h-24 bg-white/80 backdrop-blur-md border-b border-slate-200 px-10 flex items-center justify-between sticky top-0 z-20">
                    <div className="flex items-center gap-6">
                        <h1 className="text-2xl font-black text-slate-900 tracking-tight">AI Interview Assistant</h1>
                        {interviewData?.locked_skill && (
                            <div className="bg-slate-900 text-white px-5 py-2 rounded-full flex items-center gap-2 shadow-lg shadow-slate-900/20">
                                <span className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Skill:</span>
                                <span className="text-xs font-bold tracking-wider">{interviewData.locked_skill.toUpperCase()}</span>
                                <Lock className="w-3 h-3 text-amber-400" />
                            </div>
                        )}
                    </div>

                    <div className="flex items-center gap-4">
                        <div className="bg-white border border-slate-200 px-4 py-2 rounded-2xl shadow-sm text-slate-600 font-bold text-sm">
                            Q {
                                isAptitude
                                    ? (aptitudeQuestions.findIndex(q => q.id === currentQuestion?.id) + 1)
                                    : currentQuestion?.question_type === 'technical'
                                        ? (technicalQuestions.findIndex(q => q.id === currentQuestion?.id) + 1)
                                        : (behavioralQuestions.findIndex(q => q.id === currentQuestion?.id) + 1)
                            } / {
                                isAptitude ? aptitudeQuestions.length :
                                    currentQuestion?.question_type === 'technical' ? technicalQuestions.length : behavioralQuestions.length
                            }
                        </div>
                        <div className="bg-green-500 text-white px-5 py-2 rounded-2xl shadow-lg shadow-green-500/20 font-bold text-sm">
                            {answeredCount}/{totalQuestions} total answered
                        </div>
                    </div>
                </header>

                {/* Question Area */}
                <main className="flex-1 overflow-y-auto p-12">
                    <div className="max-w-4xl mx-auto space-y-8">

                        {/* Question Card */}
                        <div className="bg-white rounded-[2.5rem] shadow-2xl shadow-blue-900/5 border border-slate-200 p-12 relative overflow-hidden">
                            <div className="absolute top-0 left-0 w-2 h-full bg-blue-600"></div>

                            <div className="flex items-center justify-between mb-8">
                                <div className="flex items-center gap-3">
                                    <div className="w-3 h-3 rounded-full bg-blue-600 animate-pulse"></div>
                                    <span className="text-sm font-black text-blue-600 uppercase tracking-widest">Current Question</span>
                                </div>
                                <div className="bg-purple-100 text-purple-700 px-4 py-1.5 rounded-full text-[10px] font-black uppercase tracking-[0.15em] border border-purple-200">
                                    {currentQuestion?.question_type.replace('_', ' ')} ROUND
                                </div>
                            </div>

                            <h2 className="text-4xl font-bold text-slate-900 leading-[1.2] mb-4">
                                <span className="text-blue-600 mr-2">
                                    {
                                        isAptitude
                                            ? (aptitudeQuestions.findIndex(q => q.id === currentQuestion?.id) + 1)
                                            : currentQuestion?.question_type === 'technical'
                                                ? (technicalQuestions.findIndex(q => q.id === currentQuestion?.id) + 1)
                                                : (behavioralQuestions.findIndex(q => q.id === currentQuestion?.id) + 1)
                                    }.
                                </span>
                                {currentQuestion?.question_text}
                            </h2>

                            {/* Decorative Icon */}
                            <div className="absolute -top-10 -right-10 opacity-[0.03] rotate-12 pointer-events-none">
                                <Brain style={{ width: '300px', height: '300px' }} />
                            </div>
                        </div>

                        {/* Answer Options / Textarea */}
                        <div className="bg-white rounded-[2.5rem] shadow-xl border border-slate-200 p-12">
                            <h3 className="text-sm font-black text-slate-400 uppercase tracking-widest mb-8">Select One Option</h3>

                            {isAptitude && options.length > 0 ? (
                                <div className="grid grid-cols-2 gap-6">
                                    {options.map((opt: string, i: number) => (
                                        <button
                                            key={i}
                                            onClick={() => setAnswer(i.toString())}
                                            className={`p-8 rounded-3xl border-2 text-left transition-all duration-300 group relative
                                                ${answer === i.toString()
                                                    ? 'bg-blue-600 border-blue-600 text-white shadow-xl shadow-blue-500/30 -translate-y-1'
                                                    : 'bg-white border-slate-100 text-slate-700 hover:border-blue-200 hover:bg-slate-50'}`}
                                        >
                                            <div className="flex items-center gap-6">
                                                <div className={`w-12 h-12 rounded-2xl flex items-center justify-center font-black text-lg border-2 transition-colors
                                                    ${answer === i.toString() ? 'bg-white/20 border-white text-white' : 'bg-slate-50 border-slate-100 text-slate-400 group-hover:border-blue-200 group-hover:text-blue-600'}`}>
                                                    {String.fromCharCode(65 + i)}
                                                </div>
                                                <span className="text-lg font-bold">{opt}</span>
                                            </div>
                                        </button>
                                    ))}
                                </div>
                            ) : (
                                <div className="space-y-4">
                                    <textarea
                                        value={answer}
                                        onChange={(e) => setAnswer(e.target.value)}
                                        className="w-full h-48 bg-slate-50 border-2 border-slate-100 rounded-3xl p-8 text-lg font-medium text-slate-900 focus:bg-white focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 transition-all outline-none resize-none"
                                        placeholder="Type your detailed response here..."
                                    />
                                    <div className="flex justify-between items-center px-4">
                                        <div className="flex items-center gap-2">
                                            <div className={`w-2 h-2 rounded-full animate-pulse ${isSubmitting ? 'bg-amber-500' : 'bg-green-500'}`}></div>
                                            <span className="text-xs font-bold text-slate-400">AI Analysis Active</span>
                                        </div>
                                        <Button
                                            variant="ghost"
                                            className="text-slate-400 hover:text-blue-600 font-bold"
                                            onClick={() => { }} // Handle Voice transcription here if needed
                                        >
                                            <Mic className="w-5 h-5 mr-2" />
                                            Use Voice
                                        </Button>
                                    </div>
                                </div>
                            )}

                            {/* Footer Actions */}
                            <div className="mt-12 pt-10 border-t border-slate-100 flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <Button
                                        variant="ghost"
                                        className="h-12 px-6 rounded-2xl text-slate-400 font-bold hover:bg-slate-50 hover:text-slate-900"
                                        onClick={() => currentIndex > 0 && setCurrentIndex(currentIndex - 1)}
                                        disabled={currentIndex === 0}
                                    >
                                        <ChevronLeft className="w-5 h-5 mr-2" />
                                        Prev
                                    </Button>
                                    <Button
                                        variant="ghost"
                                        className="h-12 px-6 rounded-2xl text-slate-900 font-bold hover:bg-slate-50"
                                        onClick={() => currentIndex < totalQuestions - 1 && setCurrentIndex(currentIndex + 1)}
                                        disabled={currentIndex === totalQuestions - 1}
                                    >
                                        Next
                                        <ChevronRight className="w-5 h-5 ml-2" />
                                    </Button>
                                </div>

                                <p className="text-xs font-bold text-slate-400 italic">Answer each question and submit to move forward</p>

                                <Button
                                    disabled={!answer.trim() || isSubmitting || currentQuestion?.is_answered}
                                    onClick={handleSubmit}
                                    className="h-16 px-10 rounded-[1.25rem] bg-blue-600 hover:bg-blue-700 text-white font-black text-lg shadow-2xl shadow-blue-500/30 transition-all hover:-translate-y-1 active:scale-[0.98] disabled:opacity-30"
                                >
                                    {isSubmitting ? (
                                        <Loader2 className="w-6 h-6 animate-spin" />
                                    ) : (
                                        <>
                                            Submit Answer
                                            <ChevronRight className="w-6 h-6 ml-1" />
                                        </>
                                    )}
                                </Button>
                            </div>
                        </div>

                    </div>
                </main>
            </div>

            {/* Dialogs */}
            <IssueReportDialog
                open={showIssueDialog}
                onOpenChange={setShowIssueDialog}
                interviewId={interviewId}
            />
            <FeedbackDialog
                open={showFeedbackDialog}
                onOpenChange={setShowFeedbackDialog}
                interviewId={interviewId}
            />
        </div>
    )
}
