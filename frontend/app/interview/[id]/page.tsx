'use client'

import React, { useEffect, useState, useRef, useMemo } from 'react'
import { APIClient } from '@/app/dashboard/lib/api-client'
import { useParams, useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'

// Face Detection Imports
import * as tf from '@tensorflow/tfjs-core';
import '@tensorflow/tfjs-backend-webgl';
import * as blazeface from '@tensorflow-models/blazeface';

import {
    Mic, MicOff, Loader2, ChevronLeft, ChevronRight,
    CheckCircle2, Circle, Brain, BookOpen, AlertTriangle,
    Clock, Target, ListChecks, Lock, Sidebar as SidebarIcon,
    Camera, CameraOff, Video
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
    started_at: string
    duration_minutes: number
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
    const [timeLeft, setTimeLeft] = useState<number | null>(null)
    const [visitedIds, setVisitedIds] = useState<Set<number>>(new Set())
    const [isListening, setIsListening] = useState(false)
    const [isTranscribing, setIsTranscribing] = useState(false)
    const [isFaceDetected, setIsFaceDetected] = useState(true)
    const [isCameraActive, setIsCameraActive] = useState(false)

    // Support States
    const [showIssueDialog, setShowIssueDialog] = useState(false)
    const [showFeedbackDialog, setShowFeedbackDialog] = useState(false)
    const [sectionMessage, setSectionMessage] = useState<string | null>(null)
    const [lastSection, setLastSection] = useState<string | null>(null)
    const [isFullscreen, setIsFullscreen] = useState(false)

    // Refs to always have live values inside event listeners (avoid stale closures)
    const warningsRef = useRef(0)
    const interviewStatusRef = useRef('loading')
    const hiddenSinceRef = useRef<number | null>(null)
    const mediaRecorderRef = useRef<any>(null)
    const audioChunksRef = useRef<any[]>([])

    // Overall Video Recording Refs
    const videoRef = useRef<HTMLVideoElement>(null)
    const streamRef = useRef<MediaStream | null>(null)
    const overallMediaRecorderRef = useRef<MediaRecorder | null>(null)
    const overallVideoChunksRef = useRef<Blob[]>([])
    const detectorRef = useRef<any>(null)
    const faceCheckIntervalRef = useRef<NodeJS.Timeout | null>(null)

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

    // Track visited questions and section transitions
    useEffect(() => {
        // No auto-init for MediaRecorder, we start it on click
        return () => {
            if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
                mediaRecorderRef.current.stop()
            }
        }
    }, [])

    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
            
            // Try to use a standard mime type, but fallback to whatever the browser supports
            const options = { mimeType: 'audio/webm' }
            let mediaRecorder: MediaRecorder
            
            if (MediaRecorder.isTypeSupported('audio/webm')) {
                mediaRecorder = new MediaRecorder(stream, options)
            } else {
                mediaRecorder = new MediaRecorder(stream)
            }

            mediaRecorderRef.current = mediaRecorder
            audioChunksRef.current = []

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunksRef.current.push(event.data)
                }
            }

            mediaRecorder.onstop = async () => {
                const mimeType = mediaRecorder.mimeType || 'audio/webm'
                const audioBlob = new Blob(audioChunksRef.current, { type: mimeType })
                if (audioBlob.size > 0) {
                    await handleTranscribe(audioBlob)
                }
                // Clean up stream
                stream.getTracks().forEach(track => track.stop())
            }

            mediaRecorder.start()
            setIsListening(true)
        } catch (err) {
            console.error("Mic access failed", err)
            alert("Could not access microphone. Please check permissions.")
        }
    }

    const stopRecording = () => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
            mediaRecorderRef.current.stop()
            setIsListening(false)
        }
    }

    const handleTranscribe = async (audioBlob: Blob) => {
        setIsTranscribing(true)
        try {
            const formData = new FormData()
            // Ensure filename extension matches mime type if possible
            const ext = audioBlob.type.includes('ogg') ? 'ogg' : 'webm'
            formData.append('file', audioBlob, `recording.${ext}`)
            
            const res = await APIClient.postMultipart<{ text: string }>(`/api/interviews/${interviewId}/transcribe`, formData)
            if (res.text) {
                setAnswer(prev => {
                    const trimmedPrev = prev.trim()
                    return trimmedPrev ? `${trimmedPrev} ${res.text.trim()}` : res.text.trim()
                })
            }
        } catch (err: any) {
            console.error("Transcription failed", err)
            const detail = err.message || "Please check your microphone and internet connection.";
            alert(`Voice transcription failed: ${detail}. You can still type your answer manually.`)
        } finally {
            setIsTranscribing(false)
        }
    }

    const initOverallRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 }, audio: true })
            streamRef.current = stream
            setIsCameraActive(true)

            // Standard Video Recording
            const mediaRecorder = new MediaRecorder(stream, { mimeType: 'video/webm' })
            overallMediaRecorderRef.current = mediaRecorder
            overallVideoChunksRef.current = []

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    overallVideoChunksRef.current.push(event.data)
                }
            }

            mediaRecorder.start(1000) // Capture in 1s chunks to avoid large data loss

            // Start Face Detection
            await startFaceDetection()
        } catch (err) {
            console.error("Overall recording failed", err)
            alert("Could not access camera/mic for recording. Please ensure permissions are granted.")
        }
    }

    const startFaceDetection = async () => {
        try {
            await tf.ready();
            const model = await blazeface.load();
            detectorRef.current = model;

            faceCheckIntervalRef.current = setInterval(async () => {
                if (videoRef.current && detectorRef.current && interviewStatusRef.current === 'active' && videoRef.current.readyState === 4) {
                    try {
                        const returnTensors = false;
                        const predictions = await detectorRef.current.estimateFaces(videoRef.current, returnTensors);
                        setIsFaceDetected(predictions.length > 0);
                    } catch (e) {
                        console.error("Detection error", e);
                    }
                }
            }, 3000); // Check every 3 seconds
        } catch (err) {
            console.error("Face detection init failed", err);
        }
    }

    const stopOverallRecording = async () => {
        if (faceCheckIntervalRef.current) {
            clearInterval(faceCheckIntervalRef.current);
        }

        return new Promise<void>((resolve) => {
            if (overallMediaRecorderRef.current && overallMediaRecorderRef.current.state !== 'inactive') {
                overallMediaRecorderRef.current.onstop = async () => {
                    const videoBlob = new Blob(overallVideoChunksRef.current, { type: 'video/webm' });
                    await uploadOverallVideo(videoBlob);
                    resolve();
                }
                overallMediaRecorderRef.current.stop();
            } else {
                resolve();
            }

            // Stop camera stream
            if (videoRef.current && videoRef.current.srcObject) {
                const stream = videoRef.current.srcObject as MediaStream;
                stream.getTracks().forEach(track => track.stop());
                setIsCameraActive(false);
            }
        });
    }

    const uploadOverallVideo = async (videoBlob: Blob) => {
        try {
            const formData = new FormData()
            formData.append('file', videoBlob, `interview_${interviewId}.webm`)
            await APIClient.postMultipart(`/api/interviews/${interviewId}/upload-video`, formData)
            console.log("Overall video uploaded successfully")
        } catch (err) {
            console.error("Video upload failed", err)
        }
    }

    useEffect(() => {
        if (questions.length > 0 && questions[currentIndex]) {
            const currentQ = questions[currentIndex]
            setVisitedIds(prev => new Set(prev).add(currentQ.id))

            // Stop listening when moving between questions
            if (isListening) {
                stopRecording()
            }

            if (lastSection && lastSection !== currentQ.question_type) {
                setSectionMessage(`${lastSection.replace('_', ' ')} round completed. Moving to ${currentQ.question_type.replace('_', ' ')} round.`)
                setTimeout(() => setSectionMessage(null), 5000)
            }
            setLastSection(currentQ.question_type)
        }
    }, [currentIndex, questions])

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
            if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
                mediaRecorderRef.current.stop()
            }
            stopOverallRecording()
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [interviewId])

    useEffect(() => {
        if (isCameraActive && streamRef.current && videoRef.current) {
            videoRef.current.srcObject = streamRef.current
        }
    }, [isCameraActive])

    useEffect(() => {
        if (interviewStatus === 'active') {
            initOverallRecording()
        } else if (interviewStatus === 'completed') {
            stopOverallRecording()
        }
    }, [interviewStatus])

    useEffect(() => {
        if (!interviewData?.started_at || interviewStatus !== 'active') return

        const dateStr = interviewData.started_at.includes('Z')
            ? interviewData.started_at
            : (interviewData.started_at.replace(' ', 'T') + (interviewData.started_at.includes('T') ? 'Z' : 'Z'))

        const startTime = new Date(dateStr).getTime()
        const durationMs = (interviewData.duration_minutes || 60) * 60 * 1000
        const endTime = startTime + durationMs

        const updateTimer = () => {
            const now = Date.now()
            const diff = endTime - now
            const remaining = Math.max(0, Math.floor(diff / 1000))
            setTimeLeft(remaining)

            if (remaining <= 0 && interviewStatusRef.current === 'active') {
                console.log("Time is up! Auto-finishing interview.")
                finishInterview()
            }
        }

        updateTimer()
        const timerInterval = setInterval(updateTimer, 1000)

        return () => clearInterval(timerInterval)
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [interviewData, interviewStatus])

    // Fullscreen and Tab Management
    useEffect(() => {
        if (interviewStatus === 'active') {
            const handleFullscreenChange = () => {
                setIsFullscreen(!!document.fullscreenElement)
            }

            document.addEventListener('fullscreenchange', handleFullscreenChange)

            // Initial check
            setIsFullscreen(!!document.fullscreenElement)

            const enterFullscreen = async () => {
                try {
                    if (!document.fullscreenElement) {
                        await document.documentElement.requestFullscreen()
                    }
                } catch (err) {
                    console.error("Fullscreen failed:", err)
                }
            }
            enterFullscreen()

            return () => document.removeEventListener('fullscreenchange', handleFullscreenChange)
        }
    }, [interviewStatus])

    const formatTime = (seconds: number | null) => {
        if (seconds === null) return '--:--'
        const h = Math.floor(seconds / 3600)
        const m = Math.floor((seconds % 3600) / 60)
        const s = seconds % 60
        return `${h > 0 ? h + ':' : ''}${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
    }

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
                const startIdx = firstUnanswered !== -1 ? firstUnanswered : 0
                setCurrentIndex(startIdx)
                setVisitedIds(new Set([qs[startIdx].id]))
                setInterviewStatus('active')
            }
        } catch (err: any) {
            console.error("Failed to load interview", err)
            // If unauthorized or forbidden, redirect to access page
            if (err.message.includes('401') || err.message.includes('403') || err.message.includes('Unauthorized') || err.message.includes('denied')) {
                localStorage.removeItem('auth_token')
                router.push('/interview/access')
            } else {
                setInterviewStatus('error')
            }
        } finally {
            setIsLoading(false)
        }
    }

    const handleSubmit = async () => {
        if (!answer.trim() || !currentQuestion) return
        setIsSubmitting(true)

        // Stop listening on submit
        if (isListening) {
            stopRecording()
        }

        try {
            const res = await APIClient.post<any>(`/api/interviews/${interviewId}/submit-answer`, {
                question_id: currentQuestion.id,
                answer_text: answer
            })


            if (res.terminated) {
                alert(res.message || "This interview session has been terminated.");
                setInterviewStatus('completed');
                return;
            }

            // Update local state
            const updatedQuestions = questions.map((q, idx) =>
                idx === currentIndex ? { ...q, is_answered: true } : q
            )
            setQuestions(updatedQuestions)
            setAnswer('')

            // Auto-move to next unanswered or just next
            const nextUnanswered = updatedQuestions.findIndex((q, idx) => !q.is_answered && idx > currentIndex)
            if (nextUnanswered !== -1) {
                setCurrentIndex(nextUnanswered)
            } else {
                // If no more unanswered after this one, check ALL earlier questions
                const earlierUnanswered = updatedQuestions.findIndex(q => !q.is_answered)
                if (earlierUnanswered !== -1) {
                    setCurrentIndex(earlierUnanswered)
                } else {
                    finishInterview(updatedQuestions)
                }
            }
        } catch (err: any) {
            console.error("Submission error:", err)
            alert(err.message || "Failed to submit answer. Please try again.")
        } finally {
            setIsSubmitting(false)
        }
    }

    const finishInterview = async (manualQuestions?: Question[]) => {
        const qsToUse = manualQuestions || questions
        // Double check all questions are answered
        const unansweredCount = qsToUse.filter(q => !q.is_answered).length
        if (unansweredCount > 0) {
            alert(`Please answer all questions before finishing. You have ${unansweredCount} unanswered question(s).`)
            // Find first unanswered and jump to it
            const firstUnanswered = qsToUse.findIndex(q => !q.is_answered)
            if (firstUnanswered !== -1) {
                setCurrentIndex(firstUnanswered)
            }
            return
        }

        try {
            setIsSubmitting(true)
            await stopOverallRecording()
            await APIClient.post(`/api/interviews/${interviewId}/end`, {})
            setInterviewStatus('completed')
            setShowFeedbackDialog(true)
        } catch (err: any) {
            console.error("Error finishing interview", err)
            alert(err.message || "Failed to complete interview. Please try again.")
        } finally {
            setIsSubmitting(false)
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
                                                ? 'bg-green-500 border-green-600 text-white shadow-sm'
                                                : visitedIds.has(q.id)
                                                    ? 'bg-red-500 border-red-600 text-white shadow-sm'
                                                    : 'bg-blue-50 border-blue-200 text-blue-600'
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
                                                ? 'bg-green-500 border-green-600 text-white shadow-sm'
                                                : visitedIds.has(q.id)
                                                    ? 'bg-red-500 border-red-600 text-white shadow-sm'
                                                    : 'bg-blue-50 border-blue-200 text-blue-600'
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
                                                ? 'bg-green-500 border-green-600 text-white shadow-sm'
                                                : visitedIds.has(q.id)
                                                    ? 'bg-red-500 border-red-600 text-white shadow-sm'
                                                    : 'bg-blue-50 border-blue-200 text-blue-600'
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

                {/* Section Transition Popup (Smaller) */}
                {sectionMessage && (
                    <div className="fixed top-8 left-1/2 -translate-x-1/2 z-[200] animate-in slide-in-from-top-4 fade-in duration-500">
                        <div className="bg-white/90 backdrop-blur-md px-8 py-4 rounded-[2rem] shadow-2xl border border-blue-100 flex items-center gap-4 min-w-[300px]">
                            <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center shrink-0">
                                <ListChecks className="w-5 h-5 text-blue-600" />
                            </div>
                            <div className="text-left">
                                <h4 className="text-[10px] font-black text-blue-600 uppercase tracking-widest leading-none mb-1">Round Completed</h4>
                                <p className="text-slate-600 font-bold text-sm leading-tight">
                                    {sectionMessage}
                                </p>
                            </div>
                        </div>
                    </div>
                )}

                {/* Mandatory Fullscreen Warning */}
                {!isFullscreen && interviewStatus === 'active' && (
                    <div className="fixed inset-0 z-[300] bg-slate-900/90 backdrop-blur-xl flex items-center justify-center p-6 text-center">
                        <div className="max-w-md w-full bg-white rounded-[3rem] p-12 shadow-2xl border border-blue-100 flex flex-col items-center">
                            <div className="w-20 h-20 bg-blue-50 rounded-full flex items-center justify-center mb-6 border border-blue-100 animate-pulse">
                                <AlertTriangle className="w-10 h-10 text-amber-500" />
                            </div>
                            <h2 className="text-2xl font-black text-slate-900 mb-4 uppercase tracking-tight">Fullscreen Required</h2>
                            <p className="text-slate-600 font-bold mb-8 leading-relaxed">
                                To ensure interview integrity, you must be in fullscreen mode to continue the test.
                            </p>
                            <Button
                                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-black h-14 rounded-2xl shadow-xl shadow-blue-500/30 transition-all hover:scale-105"
                                onClick={async () => {
                                    try {
                                        if (!document.fullscreenElement) {
                                            await document.documentElement.requestFullscreen()
                                        }
                                    } catch (e) {
                                        alert("Please enable fullscreen manually to continue (F11 or Browser menu).")
                                    }
                                }}
                            >
                                Re-enable Fullscreen
                            </Button>
                        </div>
                    </div>
                )}

                {/* Face Detection Warning */}
                {!isFaceDetected && interviewStatus === 'active' && (
                    <div className="fixed inset-0 z-[400] bg-red-950/40 backdrop-blur-sm flex items-center justify-center p-6 pointer-events-none">
                        <div className="max-w-sm w-full bg-white rounded-3xl p-8 shadow-2xl border-4 border-red-500 animate-bounce flex flex-col items-center pointer-events-auto">
                            <div className="w-16 h-16 bg-red-50 rounded-full flex items-center justify-center mb-4 border border-red-100">
                                <CameraOff className="w-8 h-8 text-red-500" />
                            </div>
                            <h2 className="text-xl font-black text-red-600 mb-2 uppercase tracking-tight text-center">Face Not Detected</h2>
                            <p className="text-slate-600 font-bold text-center text-sm">
                                Please ensure your face is clearly visible in the camera frame to avoid session termination.
                            </p>
                        </div>
                    </div>
                )}

                {/* Fixed Camera Preview */}
                {isCameraActive && (
                    <div className="fixed bottom-6 right-6 z-[100] w-48 h-36 rounded-2xl overflow-hidden shadow-2xl border-2 border-white/20 bg-slate-900 group transition-all hover:scale-110">
                        <video
                            ref={videoRef}
                            autoPlay
                            muted
                            playsInline
                            onLoadedMetadata={(e) => (e.target as HTMLVideoElement).play()}
                            className="w-full h-full object-cover"
                        />
                        <div className="absolute top-2 right-2 flex gap-1">
                            <div className={`w-2 h-2 rounded-full ${isFaceDetected ? 'bg-green-500' : 'bg-red-500'} shadow-sm animate-pulse`}></div>
                        </div>
                        <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end p-2">
                            <span className="text-[8px] font-black text-white uppercase tracking-wider flex items-center gap-1">
                                <Video className="w-2 h-2" /> Live Proctoring
                            </span>
                        </div>
                    </div>
                )}

                {/* Question Info Bar (Replacing Header) */}
                <div className="h-20 flex items-center justify-between px-10 relative z-20">
                    <div className="flex items-center gap-4">
                        <div className="bg-slate-900 text-white px-5 py-2 rounded-full flex items-center gap-2 shadow-lg">
                            <span className="text-[10px] font-black uppercase tracking-wider text-slate-400">Locked:</span>
                            <span className="text-xs font-bold tracking-wider">{interviewData?.locked_skill?.toUpperCase() || 'GENERAL'}</span>
                        </div>
                    </div>

                    <div className="flex items-center gap-4">
                        <div className={`px-5 py-2 rounded-2xl shadow-xl font-black text-sm flex items-center gap-2 transition-all duration-500 border-2 ${timeLeft && timeLeft < 300 ? 'bg-red-500 border-red-400 text-white animate-pulse' : 'bg-white border-slate-100 text-slate-600'}`}>
                            <Clock className={`w-4 h-4 ${timeLeft && timeLeft < 300 ? 'animate-spin-slow' : ''}`} />
                            <span className="tabular-nums">{formatTime(timeLeft)}</span>
                        </div>
                        <div className="bg-white border-2 border-slate-100 px-4 py-2 rounded-2xl text-slate-400 font-bold text-xs">
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
                    </div>
                </div>
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
                                    {currentQuestion?.question_type?.replace('_', ' ')} ROUND
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
                                            disabled={isTranscribing}
                                            className={`font-bold transition-all duration-300 ${isListening ? 'text-red-500 animate-pulse' : 'text-slate-400 hover:text-blue-600'}`}
                                            onClick={() => {
                                                if (isListening) {
                                                    stopRecording()
                                                } else {
                                                    startRecording()
                                                }
                                            }}
                                        >
                                            {isTranscribing ? <Loader2 className="w-5 h-5 mr-2 animate-spin" /> : (isListening ? <MicOff className="w-5 h-5 mr-2" /> : <Mic className="w-5 h-5 mr-2" />)}
                                            {isTranscribing ? 'Converting to Text...' : (isListening ? 'Stop & Convert' : 'Use Voice (High Accuracy)')}
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
