'use client'

import React, { useState, useMemo } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Slider } from "@/components/ui/slider"
import { Calendar } from "@/components/ui/calendar"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import useSWR, { mutate } from 'swr'
import { fetcher } from '@/app/dashboard/lib/swr-fetcher'
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer
} from 'recharts'
import { Download, FileText, Filter, Search, AlertCircle, CheckCircle2, XCircle, RotateCcw, Activity } from 'lucide-react'

import { CategoryScoreCard } from '@/components/reports/CategoryScoreCard'
import { StatusChart, DetailedMetricsChart, SkillProficiencyChart } from '@/components/reports/Charts'
import { MetricCard } from '@/components/reports/MetricCard'
import { ReportCard } from '@/components/reports/ReportCard'

// Constants
const SKILL_CATEGORIES = [
  "backend", "frontend", "fullstack", "devops", "networking",
  "data", "mobile", "aec_bim", "hr", "qa_testing", "ui_ux", "cybersecurity"
]

// Types
interface Evaluation {
  overall?: number
  relevance?: number
  action_impact?: number
  communication?: number
  coherence?: number
  empathy?: number
  situational_handling?: number
  self_awareness?: number
  technical_accuracy?: number
  completeness?: number
  clarity?: number
  depth?: number
  practicality?: number
  strengths?: string[]
  weaknesses?: string[]
}

interface QuestionEvaluation {
  question: string
  answer: string
  evaluation: Evaluation
  question_number?: number
  question_type?: 'technical' | 'behavioral' | 'aptitude'
  correct?: boolean
}

interface CandidateProfile {
  candidate_name?: string
  candidate_email?: string
  applied_role?: string
  experience_level?: string
  primary_skill?: string
  confidence?: string
  communication?: string
  skills?: string[]
}

interface Report {
  filename: string
  timestamp: string
  display_date: string
  display_date_short: string
  status: string
  status_color: string
  overall_score: number
  final_score: number
  total_questions_answered: number
  question_evaluations: QuestionEvaluation[]
  candidate_profile: CandidateProfile
  tech_score?: number
  comm_score?: number
  evaluated_skills?: string | null
  aptitude_score?: number | null
  behavioral_score?: number | null
  technical_score?: number | null
  first_level_score?: number | null
  aptitude_question_evaluations?: QuestionEvaluation[]
  aptitude_questions_answered?: number
}

// Helper to clean question text that may be stored as JSON array strings
function cleanQuestionText(text: string): string {
  if (!text) return '';
  let cleaned = text.trim();
  // Strip JSON array brackets: ["question text"] → question text
  if (cleaned.startsWith('[') && cleaned.endsWith(']')) {
    try {
      const parsed = JSON.parse(cleaned);
      if (Array.isArray(parsed) && parsed.length > 0) {
        cleaned = parsed[0];
      }
    } catch {
      // Not valid JSON array, try manual strip
      cleaned = cleaned.slice(1, -1).trim();
    }
  }
  // Strip surrounding quotes
  if ((cleaned.startsWith('"') && cleaned.endsWith('"')) ||
    (cleaned.startsWith("'") && cleaned.endsWith("'"))) {
    cleaned = cleaned.slice(1, -1);
  }
  return cleaned.trim();
}

export default function ReportsPage() {
  const { data: rawReports = [], error: fetchError, isLoading: isSWRDashboardLoading } = useSWR<Report[]>('/api/analytics/reports', (url: string) => fetcher<Report[]>(url))

  const reports = useMemo(() => {
    return rawReports.map(report => {
      let techSum = 0;
      let commSum = 0;
      let techCount = 0;
      let commCount = 0;

      report.question_evaluations?.forEach(q => {
        if (q.evaluation?.technical_accuracy !== undefined) {
          techSum += q.evaluation.technical_accuracy;
          techCount++;
        }
        if (q.evaluation?.clarity !== undefined) {
          commSum += q.evaluation.clarity;
          commCount++;
        }
      });

      return {
        ...report,
        tech_score: techCount > 0 ? techSum / techCount : report.tech_score,
        comm_score: commCount > 0 ? commSum / commCount : report.comm_score,
      };
    });
  }, [rawReports])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'hired': return 'bg-primary/10 text-primary border-primary/20'
      case 'rejected': return 'bg-destructive/10 text-destructive border-destructive/20'
      case 'review_later': return 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20'
      case 'interview_scheduled':
      case 'approved_for_interview': return 'bg-accent/10 text-accent border-accent/20'
      case 'interview_completed': return 'bg-secondary/10 text-secondary border-secondary/20'
      default: return 'bg-muted text-muted-foreground border-border'
    }
  }

  const getStatusLabel = (status: string) => {
    return status?.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ') || status
  }

  const isLoading = isSWRDashboardLoading && reports.length === 0
  const [errorState, setError] = useState<string | null>(null) // renamed to avoid conflict with error from useSWR

  const [selectedQuestion, setSelectedQuestion] = useState<QuestionEvaluation | null>(null)
  const [viewingReport, setViewingReport] = useState<Report | null>(null)
  const [reportView, setReportView] = useState<'technical' | 'aptitude' | 'behavioral'>('technical');


  // Filters
  const [statusFilter, setStatusFilter] = useState('All')
  const [skillFilter, setSkillFilter] = useState('All') // New
  const [dateFilter, setDateFilter] = useState<Date | undefined>(undefined) // New
  const [scoreRange, setScoreRange] = useState([0, 10])
  const [experienceFilter, setExperienceFilter] = useState('All')
  const [selectedSkills, setSelectedSkills] = useState<string[]>([])
  const [searchQuery, setSearchQuery] = useState('')

  // Derived Data for Filters
  const uniqueExperiences = useMemo(() => Array.from(new Set(reports.map(r => r.candidate_profile.experience_level || 'N/A'))).sort(), [reports])
  const uniqueSkills = useMemo(() => Array.from(new Set(reports.map(r => r.candidate_profile.primary_skill || 'N/A'))).sort(), [reports])

  // Derived Interview Counts for Calendar Heatmap
  const interviewCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    reports.forEach(r => {
      const date = new Date(r.timestamp)
      if (!isNaN(date.getTime())) {
        const dateStr = date.toDateString()
        counts[dateStr] = (counts[dateStr] || 0) + 1
      }
    })
    return counts
  }, [reports])

  // Filter Logic
  const filteredReports = useMemo(() => {
    return reports.filter(report => {
      const matchesStatus = statusFilter === 'All' || report.status === statusFilter
      const matchesScore = report.overall_score >= scoreRange[0] && report.overall_score <= scoreRange[1]
      const matchesExp = experienceFilter === 'All' || report.candidate_profile.experience_level === experienceFilter

      // Skill Filter Logic (Partial Match)
      const matchesSkillFilter = skillFilter === 'All' ||
        (report.candidate_profile.primary_skill?.toLowerCase() || '').includes(skillFilter.toLowerCase()) ||
        (report.candidate_profile.skills?.some(s => s.toLowerCase().includes(skillFilter.toLowerCase())) || false)

      // Date Filter Logic
      const reportDate = new Date(report.timestamp)
      const matchesDate = !dateFilter || (
        reportDate.getDate() === dateFilter.getDate() &&
        reportDate.getMonth() === dateFilter.getMonth() &&
        reportDate.getFullYear() === dateFilter.getFullYear()
      )

      // Basic search
      const matchesSearch = searchQuery === '' ||
        report.filename.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (report.candidate_profile.primary_skill || '').toLowerCase().includes(searchQuery.toLowerCase())

      return matchesStatus && matchesScore && matchesExp && matchesSearch && matchesSkillFilter && matchesDate
    })
  }, [reports, statusFilter, scoreRange, experienceFilter, skillFilter, dateFilter, searchQuery])

  // Metrics
  const metrics = useMemo(() => {
    const total = filteredReports.length
    const selectedCount = filteredReports.filter(r => r.status === 'Selected').length
    const holdCount = filteredReports.filter(r => r.status === 'Hold').length
    const rejectedCount = filteredReports.filter(r => r.status === 'Rejected').length
    const avgScore = total > 0 ? (filteredReports.reduce((acc, r) => acc + r.overall_score, 0) / total).toFixed(2) : '0.00'
    const avgQuestions = total > 0 ? (filteredReports.reduce((acc, r) => acc + r.total_questions_answered, 0) / total).toFixed(1) : '0.0'

    return { total, selected: selectedCount, hold: holdCount, rejected: rejectedCount, avgScore, avgQuestions }
  }, [filteredReports])

  // Chart Data for Report Modal
  const radarData = useMemo(() => {
    if (!viewingReport) return [];
    let tech = 0, comm = 1, depthScore = 0, completenessScore = 0, practicalityScore = 0;
    let count = viewingReport.question_evaluations?.length || 1;

    viewingReport.question_evaluations?.forEach(q => {
      tech += q.evaluation?.technical_accuracy || 0;
      comm += q.evaluation?.clarity || 0;
      depthScore += q.evaluation?.depth || 0;
      completenessScore += q.evaluation?.completeness || 0;
      practicalityScore += q.evaluation?.practicality || 0;
    });

    return [
      { subject: 'Technical', A: tech / count, fullMark: 10 },
      { subject: 'Clarity', A: comm / count, fullMark: 10 },
      { subject: 'Depth', A: depthScore / count, fullMark: 10 },
      { subject: 'Completeness', A: completenessScore / count, fullMark: 10 },
      { subject: 'Practicality', A: practicalityScore / count, fullMark: 10 },
    ];
  }, [viewingReport]);

  const lineData = useMemo(() => {
    if (!viewingReport) return [];
    return viewingReport.question_evaluations?.map((q) => ({
      name: `Q${(q as any).question_number || '?'}`,
      Tech: q.evaluation?.technical_accuracy || 0,
      Comm: q.evaluation?.clarity || 0,
    })) || [];
  }, [viewingReport]);

  // Generate Text Report
  const generateTextReport = (report: Report) => {
    let text = `============================================================\n`
    text += `VIRTUAL HR INTERVIEWER - CANDIDATE REPORT\n`
    text += `============================================================\n\n`

    text += `Report Generated: ${report.display_date}\n`
    text += `Total Questions: ${report.total_questions_answered}\n`
    text += `Overall Score: ${report.overall_score.toFixed(2)}/10\n`
    text += `Status: ${report.status}\n\n`

    text += `CANDIDATE PROFILE\n`
    text += `----------------------------------------\n`
    text += `Name: ${report.candidate_profile.candidate_name || 'N/A'}\n`
    text += `Email: ${report.candidate_profile.candidate_email || 'N/A'}\n`
    text += `Role: ${report.candidate_profile.applied_role || 'N/A'}\n`
    text += `Experience: ${report.candidate_profile.experience_level || 'N/A'}\n`
    text += `Primary Skill: ${report.candidate_profile.primary_skill || 'N/A'}\n`
    text += `Communication: ${report.candidate_profile.communication || 'N/A'}\n\n`

    text += `QUESTION ANALYSIS\n`
    text += `----------------------------------------\n`
    report.question_evaluations.forEach((q, i) => {
      text += `\nQuestion ${i + 1}: ${q.question}\n`
      text += `Score: ${q.evaluation.overall}/10\n`
      if (q.evaluation.strengths) {
        text += `  Strengths:\n${q.evaluation.strengths.map(s => `    - ${s}`).join('\n')}\n`
      }
      if (q.evaluation.weaknesses) {
        text += `  Weaknesses:\n${q.evaluation.weaknesses.map(w => `    - ${w}`).join('\n')}\n`
      }
    })

    return text
  }

  const downloadCSV = () => {
    const headers = ['Candidate,Date,Primary Skill,Experience,Score,Status']
    const rows = filteredReports.map(r => [
      `"${r.filename.replace('.json', '')}"`,
      `"${r.display_date_short}"`,
      `"${r.candidate_profile.primary_skill || 'N/A'}"`,
      `"${r.candidate_profile.experience_level || 'N/A'}"`,
      `"${r.overall_score.toFixed(2)}"`,
      `"${r.status}"`
    ].join(','))

    const csvContent = [headers, ...rows].join('\n')
    downloadFile(csvContent, `interview_reports_${new Date().toISOString().split('T')[0]}.csv`, 'csv')
  }

  const downloadFile = (content: string, filename: string, type: 'json' | 'txt' | 'csv') => {
    let mimeType = 'text/plain'
    if (type === 'json') mimeType = 'application/json'
    if (type === 'csv') mimeType = 'text/csv'

    const blob = new Blob([content], { type: mimeType })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const clearAllFilters = () => {
    setStatusFilter('All')
    setSkillFilter('All')
    setExperienceFilter('All')
    setScoreRange([0, 10])
    setSearchQuery('')
    setDateFilter(undefined)
    setSelectedSkills([])
  }

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-screen bg-background">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }

  if (fetchError) {
    return (
      <div className="p-8">
        <div className="bg-red-50 text-red-600 p-4 rounded-lg border border-red-200">
          <h3 className="font-bold">Error Loading Reports</h3>
          <p>{fetchError.message || 'An error occurred while fetching reports.'}</p>
          <Button onClick={() => mutate('/api/analytics/reports')} variant="outline" className="mt-2">Retry</Button>
        </div>
      </div>
    )
  }

  return (
    /*
      Main Layout Container
      - Uses flex-col to stack Header and Grid.
      - On desktop (lg), sets explicit height [100vh - 9rem] to fill remaining space
        (allowing for 4rem header + 4rem layout padding + 1rem safety).
      - 'min-h-0' is crucial for allowing flex children to scroll.
    */
    <div className="w-full max-w-[1600px] mx-auto flex flex-col gap-4 lg:h-[calc(100vh-7.5rem)]">

      {/* Header - Fixed at the top of the component */}
      <div className="flex-none flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-black bg-clip-text text-transparent bg-gradient-to-r from-primary to-accent">
            Interview Reports
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Analytics and detailed reports for {reports.length} candidates
          </p>
        </div>
      </div>

      {/* Question Detail Modal */}
      <Dialog open={!!selectedQuestion} onOpenChange={(open) => !open && setSelectedQuestion(null)}>
        <DialogContent className="w-full md:!max-w-[35vw] md:!w-[35vw] max-h-[90vh] overflow-y-auto bg-background/95 p-6">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold">Detailed Question Analysis</DialogTitle>
            <DialogDescription>In-depth review of the candidate's response.</DialogDescription>
          </DialogHeader>

          {selectedQuestion && (
            <div className="space-y-8 mt-4">
              {/* Row 1: Question */}
              <div className="space-y-2">
                <h4 className="text-lg font-bold text-slate-900 dark:text-slate-50">Question:</h4>
                <p className="text-lg text-slate-900 dark:text-slate-50 bg-card p-6 rounded-xl border shadow-sm leading-relaxed">
                  {cleanQuestionText(selectedQuestion.question)}
                </p>
              </div>

              {/* Row 2: Answer */}
              <div className="space-y-2">
                <h4 className="text-lg font-bold text-slate-900 dark:text-slate-50">Answer:</h4>
                <p className="text-base text-slate-900 dark:text-slate-50 bg-card p-6 rounded-xl border shadow-sm leading-relaxed whitespace-pre-wrap">
                  {selectedQuestion.answer}
                </p>
              </div>

              {/* Row 3 & 4: Category Scores & Overall Score */}
              <div className="grid grid-cols-1 gap-8 items-center bg-card p-6 rounded-xl border shadow-sm">
                <div className="space-y-4">
                  <h4 className="text-sm font-bold text-muted-foreground uppercase tracking-wider mb-2">Evaluation Scores</h4>
                  {/* Evaluation Details */}
                  <div className={`grid grid-cols-2 ${selectedQuestion.question_type === 'behavioral' ? 'md:grid-cols-3' : 'md:grid-cols-5'} gap-4`}>
                    {(selectedQuestion.question_type === 'behavioral') ? (
                      <>
                        <MetricCard title="Relevance" score={selectedQuestion.evaluation.relevance ?? selectedQuestion.evaluation.communication ?? selectedQuestion.evaluation.technical_accuracy ?? 0} />
                        <MetricCard title="Action & Impact" score={selectedQuestion.evaluation.action_impact ?? selectedQuestion.evaluation.situational_handling ?? selectedQuestion.evaluation.completeness ?? 0} />
                        <MetricCard title="Clarity" score={selectedQuestion.evaluation.clarity ?? selectedQuestion.evaluation.coherence ?? 0} />
                      </>
                    ) : (
                      <>
                        <MetricCard title="Technical Accuracy" score={selectedQuestion.evaluation.technical_accuracy ?? 0} />
                        <MetricCard title="Completeness" score={selectedQuestion.evaluation.completeness ?? 0} />
                        <MetricCard title="Clarity" score={selectedQuestion.evaluation.clarity ?? 0} />
                        <MetricCard title="Depth" score={selectedQuestion.evaluation.depth ?? 0} />
                        <MetricCard title="Practicality" score={selectedQuestion.evaluation.practicality ?? 0} />
                      </>
                    )}
                  </div>
                </div>
              </div>


              {/* Row 5: Strengths | Areas for Improvement */}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Strengths */}
                <div>
                  <h4 className="text-lg font-bold text-slate-900 dark:text-slate-50 mb-3">Strengths:</h4>
                  <div className="bg-primary/10 border border-primary/20 rounded-xl p-6 h-full shadow-sm">
                    {selectedQuestion.evaluation.strengths && selectedQuestion.evaluation.strengths.length > 0 ? (
                      <ul className="space-y-3">
                        {selectedQuestion.evaluation.strengths.map((s, idx) => (
                          <li key={idx} className="flex gap-3 text-base text-primary leading-relaxed">
                            <CheckCircle2 className="h-5 w-5 shrink-0 mt-0.5 text-primary" />
                            <span>{s}</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-muted-foreground italic text-sm">No specific strengths noted.</p>
                    )}
                  </div>
                </div>

                {/* Weaknesses */}
                <div>
                  <h4 className="text-lg font-bold text-slate-900 dark:text-slate-50 mb-3">Areas for Improvement:</h4>
                  <div className="bg-destructive/10 border border-destructive/20 rounded-xl p-6 h-full shadow-sm">
                    {selectedQuestion.evaluation.weaknesses && selectedQuestion.evaluation.weaknesses.length > 0 ? (
                      <ul className="space-y-3">
                        {selectedQuestion.evaluation.weaknesses.map((w, idx) => (
                          <li key={idx} className="flex gap-3 text-base text-destructive leading-relaxed">
                            <XCircle className="h-5 w-5 shrink-0 mt-0.5 text-destructive" />
                            <span>{w}</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-muted-foreground italic text-sm">No specific improvements noted.</p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/*
              Content Grid
              - 'flex-1 min-h-0' makes it take remaining height and ALLOWS shrinkage/scrolling.
              - On desktop (lg), it's a 4-column grid.
              - On mobile, it stacks naturally.
            */}
      <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-4 gap-4 items-start">

        {/*
                  LEFT COMPONENT (Filter Panel)
                  - On desktop: 'h-full flex flex-col' ensures it fills the grid column height.
                  - Filters themselves live in a scrollable CardContent.
                  - It stays "sticky"/fixed effectively because the container doesn't scroll,
                    only the content inside this Card (if needed) and the Right Component.
                */}
        <div className="lg:col-span-1 max-h-full lg:max-h-[calc(100vh-10rem)] animate-in fade-in slide-in-from-left-8 duration-700 ease-out fill-mode-both">
          <Card className="h-full flex flex-col shadow-md border-slate-200 !py-0 !gap-0">
            <CardHeader className="p-3 !pb-0 shrink-0">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Filter className="h-4 w-4 text-primary" /> Filters
                </CardTitle>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-slate-500 dark:text-slate-400 hover:text-red-500"
                  onClick={clearAllFilters}
                  title="Clear all filters"
                >
                  <RotateCcw className="h-4 w-4" />
                </Button>
              </div>
            </CardHeader>
            <Separator />
            <CardContent className="flex-1 overflow-y-auto p-3 space-y-3 scrollbar-thin scrollbar-thumb-gray-200 scrollbar-track-transparent">
              {/* Search */}
              <div className="grid w-full items-center gap-1.5">
                <Label htmlFor="search">Search</Label>
                <div className="relative">
                  <Search className="absolute left-2 top-2.5 h-4 w-4 text-slate-500 dark:text-slate-400" />
                  <Input
                    id="search"
                    placeholder="Filename or skill..."
                    className="pl-8"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                </div>
              </div>

              {/* Status and Skill Filters Side-by-Side */}
              <div className="flex flex-col md:flex-row gap-4">
                {/* Status Filter */}
                <div className="space-y-2 flex-1">
                  <Label>Status</Label>
                  <Select value={statusFilter} onValueChange={setStatusFilter}>
                    <SelectTrigger>
                      <SelectValue placeholder="Status" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="All">All</SelectItem>
                      <SelectItem value="Selected">Selected</SelectItem>
                      <SelectItem value="Hold">On Hold</SelectItem>
                      <SelectItem value="Rejected">Rejected</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Skill Filter */}
                <div className="space-y-2 flex-1">
                  <Label>Skill</Label>
                  <Select value={skillFilter} onValueChange={setSkillFilter}>
                    <SelectTrigger>
                      <SelectValue placeholder="Skill" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="All">All</SelectItem>
                      {SKILL_CATEGORIES.map(skill => (
                        <SelectItem key={skill} value={skill}>
                          {skill.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Score Range */}
              <div className="space-y-2">
                <div className="flex justify-between">
                  <Label>Score Range</Label>
                  <span className="text-sm text-slate-500 dark:text-slate-400">{scoreRange[0]} - {scoreRange[1]}</span>
                </div>
                <Slider
                  defaultValue={[0, 10]}
                  max={10}
                  step={1}
                  value={scoreRange}
                  onValueChange={setScoreRange}
                  className="my-4"
                />
              </div>


              <Separator />

              {/* Calendar */}
              <div className="space-y-2">
                <Label>Interview Dates</Label>
                <div className="flex justify-center bg-primary/5 rounded-xl p-2 border border-primary/10">
                  <Calendar
                    mode="single"
                    selected={dateFilter}
                    onSelect={setDateFilter}
                    className="rounded-md border-none shadow-none w-full"
                    modifiers={{
                      low: (date) => {
                        const c = interviewCounts[date.toDateString()] || 0
                        return c >= 1 && c <= 5
                      },
                      medium: (date) => {
                        const c = interviewCounts[date.toDateString()] || 0
                        return c >= 6 && c <= 15
                      },
                      high: (date) => {
                        const c = interviewCounts[date.toDateString()] || 0
                        return c > 15
                      }
                    }}
                    modifiersClassNames={{
                      low: "bg-primary/10 text-primary font-semibold hover:bg-primary/20",
                      medium: "bg-secondary/10 text-secondary font-semibold hover:bg-secondary/20",
                      high: "bg-destructive/10 text-destructive font-semibold hover:bg-destructive/20"
                    }}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/*
                  RIGHT COMPONENT (Reports & Metrics)
                  - On desktop: 'h-full overflow-y-auto' enables independent scrolling.
                  - The Main Layout/Body will NOT scroll; this div scrolls instead.
                  - Added padding-right/bottom for scrollbar comfort.
                */}
        <div className="lg:col-span-3 h-full overflow-y-auto pr-2 pb-2 space-y-4">

          {/* Metrics Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 animate-in fade-in slide-in-from-top-8 duration-700 ease-out fill-mode-both delay-100">
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Total Reports</CardDescription>
                <CardTitle className="text-2xl">{metrics.total}</CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Avg Score</CardDescription>
                <CardTitle className="text-2xl">{metrics.avgScore}</CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Avg Questions</CardDescription>
                <CardTitle className="text-2xl">{metrics.avgQuestions}</CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Selection Rate</CardDescription>
                <CardTitle className="text-2xl">
                  {metrics.total > 0 ? Math.round((metrics.selected / metrics.total) * 100) : 0}%
                </CardTitle>
              </CardHeader>
            </Card>
          </div>

          {/* Status Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 animate-in fade-in slide-in-from-top-8 duration-700 ease-out fill-mode-both delay-200">
            <div className="bg-card p-4 rounded-lg border border-l-4 border-l-emerald-500 shadow-sm">
              <div className="text-emerald-500 font-bold text-2xl">{metrics.selected}</div>
              <div className="text-slate-500 dark:text-slate-400 text-sm">Selected</div>
            </div>
            <div className="bg-card p-4 rounded-lg border border-l-4 border-l-amber-500 shadow-sm">
              <div className="text-amber-500 font-bold text-2xl">{metrics.hold}</div>
              <div className="text-slate-500 dark:text-slate-400 text-sm">On Hold</div>
            </div>
            <div className="bg-card p-4 rounded-lg border border-l-4 border-l-red-500 shadow-sm">
              <div className="text-red-500 font-bold text-2xl">{metrics.rejected}</div>
              <div className="text-slate-500 dark:text-slate-400 text-sm">Rejected</div>
            </div>
          </div>

          {/* Reports List / Results */}
          <Tabs defaultValue="detailed">
            <div className="flex justify-between items-center mb-4">
              <TabsList>
                <TabsTrigger value="detailed">Detailed View</TabsTrigger>
                <TabsTrigger value="table">Table View</TabsTrigger>
                <TabsTrigger value="analytics">Summary Analytics</TabsTrigger>
              </TabsList>
              <span className="text-sm text-slate-500 dark:text-slate-400">Showing {filteredReports.length} reports</span>
            </div>

            <TabsContent value="detailed" className="space-y-4 animate-in fade-in slide-in-from-bottom-8 duration-700 ease-out fill-mode-both delay-300">
              {filteredReports.length === 0 ? (
                <div className="text-center py-12 bg-card rounded-lg border">
                  <p className="text-slate-500 dark:text-slate-400">No reports match your filters.</p>
                  <Button variant="link" onClick={clearAllFilters}>Clear Filters</Button>
                </div>
              ) : (
                <div className="space-y-4">
                  {filteredReports.map((report, idx) => (
                    <ReportCard
                      key={idx}
                      report={report}
                      onClick={() => setViewingReport(report)}
                    />
                  ))}
                </div>
              )}
            </TabsContent>

            <TabsContent value="table" className="animate-in fade-in zoom-in-95 duration-300">
              <div className="flex justify-end mb-4">
                <Button onClick={downloadCSV} variant="outline" className="gap-2 bg-background hover:bg-emerald-50 text-emerald-700 border-emerald-200 hover:border-emerald-300 shadow-sm">
                  <FileText className="h-4 w-4" /> Export to Excel
                </Button>
              </div>
              <Card>
                <CardContent className="p-0">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Candidate</TableHead>
                        <TableHead>Date</TableHead>
                        <TableHead>Applied For</TableHead>
                        <TableHead className="text-right">Aptitude</TableHead>
                        <TableHead className="text-right">Behavioral</TableHead>
                        <TableHead className="text-right">Score</TableHead>
                        <TableHead className="text-center">Suggestion</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredReports.map((report, idx) => (
                        <TableRow key={idx}>
                          <TableCell className="font-medium">{report.filename.replace('.json', '')}</TableCell>
                          <TableCell>{report.display_date_short}</TableCell>
                          <TableCell className="text-sm">{report.candidate_profile.applied_role || 'N/A'}</TableCell>
                          <TableCell className="text-right font-medium">
                            {report.aptitude_score !== undefined && report.aptitude_score !== null ? report.aptitude_score.toFixed(1) : '-'}
                          </TableCell>
                          <TableCell className="text-right font-medium">
                            {report.behavioral_score !== undefined && report.behavioral_score !== null ? report.behavioral_score.toFixed(1) : '-'}
                          </TableCell>
                          <TableCell className="text-right font-bold text-primary">{report.overall_score.toFixed(1)}</TableCell>
                          <TableCell className="text-center">
                            <Badge variant="outline" className={`
                                                            ${report.status === 'Selected' ? 'bg-primary/10 text-primary border-primary/20' : ''}
                                                            ${report.status === 'Hold' ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20' : ''}
                                                            ${report.status === 'Rejected' ? 'bg-destructive/10 text-destructive border-destructive/20' : ''}
                                                        `}>
                              {report.status === 'Selected' ? 'Select' : report.status === 'Rejected' ? 'Reject' : report.status}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      ))}
                      {filteredReports.length === 0 && (
                        <TableRow>
                          <TableCell colSpan={6} className="h-24 text-center">
                            No reports found.
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="analytics" className="animate-in fade-in zoom-in-95 duration-300">
              <Card>
                <CardHeader>
                  <CardTitle>Overview & Analysis</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-col lg:flex-row gap-8 items-start">
                    <div className="flex-1 w-full h-[250px]">
                      <StatusChart data={[
                        { name: 'Selected', value: metrics.selected, color: '#10b981' },
                        { name: 'Hold', value: metrics.hold, color: '#f59e0b' },
                        { name: 'Rejected', value: metrics.rejected, color: '#ef4444' }
                      ].filter(d => d.value > 0)} />
                    </div>

                    <div className="w-full lg:w-1/3 grid grid-cols-2 gap-4">
                      <div className="bg-muted/30 p-4 rounded-xl border text-center flex flex-col justify-center">
                        <div className="text-3xl font-bold text-slate-900 dark:text-slate-50">{metrics.avgScore}</div>
                        <div className="text-sm text-slate-500 dark:text-slate-400">Average Overall Score</div>
                      </div>
                      <div className="bg-muted/30 p-4 rounded-xl border text-center flex flex-col justify-center">
                        <div className="text-3xl font-bold text-slate-900 dark:text-slate-50">{metrics.total}</div>
                        <div className="text-sm text-slate-500 dark:text-slate-400">Total Interviews</div>
                      </div>
                      <div className="bg-muted/30 p-4 rounded-xl border text-center flex flex-col justify-center">
                        <div className="text-3xl font-bold text-slate-900 dark:text-slate-50">{metrics.avgQuestions}</div>
                        <div className="text-sm text-slate-500 dark:text-slate-400">Avg Questions Answered</div>
                      </div>
                      <div className="bg-muted/30 p-4 rounded-xl border text-center flex flex-col justify-center">
                        <div className="text-3xl font-bold text-slate-900 dark:text-slate-50">
                          {metrics.total > 0 ? Math.round((metrics.selected / metrics.total) * 100) : 0}%
                        </div>
                        <div className="text-sm text-slate-500 dark:text-slate-400">Selection Rate</div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </div>

      {/* FULL VIEW MODAL FOR REPORT */}
      <Dialog open={!!viewingReport} onOpenChange={(open) => !open && setViewingReport(null)}>
        <DialogContent className="w-[80vw] sm:max-w-[80vw] lg:w-[66vw] lg:max-w-[66vw] h-[85vh] lg:h-[80vh] flex flex-col p-6 overflow-hidden">
          {viewingReport && (
            <>
              <DialogHeader className="mb-4">
                <div className="flex justify-between items-start gap-4 pr-6">
                  <div className="flex flex-col items-start gap-1">
                    <DialogTitle className="text-2xl flex items-center gap-3">
                      {viewingReport.candidate_profile.candidate_name || viewingReport.display_date_short}
                      {viewingReport.status === 'Selected' && <Badge className="capsule-badge capsule-badge-success border-none shadow-none text-sm">Suggestion: Select</Badge>}
                      {viewingReport.status === 'Hold' && <Badge className="capsule-badge capsule-badge-warning border-none shadow-none text-sm">Suggestion: Hold</Badge>}
                      {viewingReport.status === 'Rejected' && <Badge className="capsule-badge capsule-badge-destructive border-none shadow-none text-sm">Suggestion: Reject</Badge>}
                    </DialogTitle>
                    <DialogDescription className="text-base text-muted-foreground mt-1">
                      {viewingReport.candidate_profile.applied_role || viewingReport.filename} &middot; {viewingReport.display_date}
                    </DialogDescription>
                  </div>
                  <div className="flex gap-6 items-center mr-4">
                    <div className="text-right border-l pl-6 border-border hidden sm:block">
                      <div className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Aptitude</div>
                      <div className="font-bold text-2xl text-slate-700 dark:text-slate-200">
                        {viewingReport.aptitude_score !== undefined && viewingReport.aptitude_score !== null ? (
                          <>{viewingReport.aptitude_score.toFixed(1)}<span className="text-sm text-slate-400 font-normal">/10</span></>
                        ) : (
                          <span className="text-2xl font-semibold text-muted-foreground">—</span>
                        )}
                      </div>
                    </div>
                    <div className="text-right border-l pl-6 border-border hidden sm:block">
                      <div className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Behavioral</div>
                      <div className="font-bold text-2xl text-slate-700 dark:text-slate-200">
                        {viewingReport.behavioral_score !== undefined && viewingReport.behavioral_score !== null ? (
                          <>{viewingReport.behavioral_score.toFixed(1)}<span className="text-sm text-slate-400 font-normal">/10</span></>
                        ) : (
                          <span className="text-2xl font-semibold text-muted-foreground">—</span>
                        )}
                      </div>
                    </div>
                    <div className="text-right border-l pl-6 border-border">
                      <div className="text-xs text-primary/80 uppercase tracking-wider font-semibold">Technical Score</div>
                      <div className="font-bold text-3xl text-primary">{viewingReport.overall_score.toFixed(1)}<span className="text-base text-primary/60 font-normal">/10</span></div>
                    </div>
                  </div>
                </div>
              </DialogHeader>

              <Separator className="mb-2 shrink-0" />

              <div className="flex-1 overflow-y-auto pr-2 space-y-6 pb-6">

                {/* Section Score Breakdown */}
                <div className="space-y-3">
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    <Activity className="h-5 w-5 text-primary" />
                    Section Score Breakdown
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <CategoryScoreCard title="📊 Aptitude Score" score={viewingReport.aptitude_score ?? undefined} />
                    <CategoryScoreCard title="💻 Technical Score" score={(viewingReport.technical_score ?? viewingReport.tech_score) ?? undefined} />
                    <CategoryScoreCard title="🧠 Behavioral Score" score={viewingReport.behavioral_score ?? undefined} />
                  </div>


                </div>

                <div className="space-y-4 mb-8">
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    <Activity className="h-5 w-5 text-primary" />
                    Performance Analytics
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                    {/* Chart 1: Evaluation Radar */}
                    <div className="bg-card border rounded-xl p-4 h-[250px] shadow-sm flex flex-col items-center">
                      <span className="text-sm font-semibold text-muted-foreground w-full text-left mb-2">Competency Radar</span>
                      <ResponsiveContainer width="100%" height="100%">
                        <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
                          <PolarGrid stroke="var(--border)" />
                          <PolarAngleAxis dataKey="subject" tick={{ fill: 'currentColor', fontSize: 11 }} />
                          <PolarRadiusAxis angle={30} domain={[0, 10]} tick={{ fontSize: 10 }} />
                          <Radar name="Score" dataKey="A" stroke="hsl(var(--primary))" fill="hsl(var(--primary))" fillOpacity={0.6} />
                          <Tooltip contentStyle={{ borderRadius: '8px', border: '1px solid var(--border)' }} />
                        </RadarChart>
                      </ResponsiveContainer>
                    </div>

                    {/* Chart 2: Tech vs Comm Line */}
                    <div className="bg-card border rounded-xl p-4 h-[250px] shadow-sm flex flex-col items-center">
                      <span className="text-sm font-semibold text-muted-foreground w-full text-left mb-2">Progression</span>
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={lineData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
                          <XAxis dataKey="name" tick={{ fill: 'currentColor', fontSize: 11 }} axisLine={false} tickLine={false} />
                          <YAxis domain={[0, 10]} tick={{ fill: 'currentColor', fontSize: 11 }} axisLine={false} tickLine={false} />
                          <Tooltip contentStyle={{ borderRadius: '8px', border: '1px solid var(--border)' }} />
                          <Line type="monotone" dataKey="Tech" stroke="hsl(var(--primary))" strokeWidth={3} dot={{ r: 4 }} />
                          <Line type="monotone" dataKey="Comm" stroke="#10b981" strokeWidth={3} dot={{ r: 4 }} />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>

                    {/* Chart 3: Detailed Metrics */}
                    <div className="bg-card border rounded-xl p-4 h-[250px] shadow-sm flex flex-col">
                      <span className="text-sm font-semibold text-muted-foreground w-full text-left mb-2">Detailed Metrics (Avg)</span>
                      <div className="flex-1 min-h-0">
                        <DetailedMetricsChart report={viewingReport} />
                      </div>
                    </div>

                    {/* Chart 4: Skill Proficiency Distribution */}
                    <div className="bg-card border rounded-xl p-4 h-[250px] shadow-sm flex flex-col">
                      <span className="text-sm font-semibold text-muted-foreground w-full text-left mb-2">Skill Proficiency</span>
                      <div className="flex-1 min-h-0">
                        <SkillProficiencyChart report={viewingReport} />
                      </div>
                    </div>
                  </div>

                  {/* Skill Proficiency Evaluation Justifications */}
                  <div className="flex flex-col gap-4 mb-8">
                    <h3 className="text-lg font-semibold flex items-center gap-2">
                      <Activity className="h-5 w-5 text-primary" />
                      Skill Proficiency Evaluation
                    </h3>
                    <div className="grid grid-cols-1 gap-4">
                      {(() => {
                        try {
                          if (viewingReport.evaluated_skills) {
                            const parsedSkills = JSON.parse(viewingReport.evaluated_skills);
                            if (Array.isArray(parsedSkills) && parsedSkills.length > 0) {
                              return parsedSkills.map((skill, index) => (
                                <div key={index} className="bg-card border rounded-xl p-5 shadow-sm">
                                  <div className="flex justify-between items-center mb-2">
                                    <h4 className="font-semibold text-md text-foreground">{skill.skillName || 'Unknown Skill'}</h4>
                                    <Badge variant="secondary" className="font-bold tabular-nums">
                                      {skill.score || 0}/10
                                    </Badge>
                                  </div>
                                  <p className="text-sm text-muted-foreground leading-relaxed">
                                    {skill.justification || 'No justification provided.'}
                                  </p>
                                </div>
                              ));
                            }
                          }
                        } catch (e) {
                          return <p className="text-sm text-muted-foreground">Unable to load skill proficiency details.</p>;
                        }
                        return <p className="text-sm text-muted-foreground">No specific skill evaluations recorded for this interview.</p>;
                      })()}
                    </div>
                  </div>
                </div>

                <div className="flex flex-col gap-4">
                  <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                    <h3 className="text-lg font-semibold flex items-center gap-2">
                      <FileText className="h-5 w-5 text-primary" />
                      Question Analysis
                    </h3>
                    <div className="flex gap-3 shrink-0">
                      <Button onClick={() => downloadFile(JSON.stringify(viewingReport, null, 2), viewingReport.filename, 'json')} variant="outline" className="bg-card hover:bg-muted shadow-sm">
                        <Download className="h-4 w-4 mr-2" /> Export JSON
                      </Button>
                      <Button onClick={() => downloadFile(generateTextReport(viewingReport), viewingReport.filename.replace('.json', '.txt'), 'txt')} className="shadow-sm">
                        <FileText className="h-4 w-4 mr-2" /> Download Report
                      </Button>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      variant={reportView === 'technical' ? 'default' : 'outline'}
                      onClick={() => setReportView('technical')}
                      size="sm"
                      className="rounded-full"
                    >
                      Technical Questions
                    </Button>
                    <Button
                      variant={reportView === 'behavioral' ? 'default' : 'outline'}
                      onClick={() => setReportView('behavioral')}
                      size="sm"
                      className="rounded-full"
                    >
                      Behavioral Questions
                    </Button>
                    <Button
                      variant={reportView === 'aptitude' ? 'default' : 'outline'}
                      onClick={() => setReportView('aptitude')}
                      size="sm"
                      className="rounded-full"
                    >
                      Aptitude Questions
                    </Button>
                  </div>
                  <ScrollArea className="h-[400px] w-full pr-4 border rounded-xl bg-card">
                    {reportView === 'aptitude' ? (
                      <div className="p-0">
                        <table className="w-full text-sm text-left">
                          <thead className="bg-muted/50 sticky top-0 z-10 border-b">
                            <tr>
                              <th className="px-4 py-3 font-semibold w-12 text-center">#</th>
                              <th className="px-4 py-3 font-semibold">Question</th>
                              <th className="px-4 py-3 font-semibold">Candidate's Answer</th>
                              <th className="px-4 py-3 font-semibold w-32 text-center">Result</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y">
                            {(viewingReport.aptitude_question_evaluations ?? []).map((q, i) => (
                              <tr key={i} className="hover:bg-muted/30 transition-colors">
                                <td className="px-4 py-4 text-center font-medium text-muted-foreground">{i + 1}</td>
                                <td className="px-4 py-4">{cleanQuestionText(q.question)}</td>
                                <td className="px-4 py-4 text-muted-foreground">{q.answer || <span className="italic text-muted-foreground/50">No answer provided</span>}</td>
                                <td className="px-4 py-4 text-center">
                                  {q.correct ? (
                                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400 font-medium">
                                      <CheckCircle2 className="w-4 h-4" /> Correct
                                    </span>
                                  ) : (
                                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400 font-medium">
                                      <XCircle className="w-4 h-4" /> Incorrect
                                    </span>
                                  )}
                                </td>
                              </tr>
                            ))}
                            {(viewingReport.aptitude_question_evaluations?.length === 0) && (
                              <tr>
                                <td colSpan={4} className="px-4 py-12 text-center text-muted-foreground italic">
                                  No aptitude questions found for this interview.
                                </td>
                              </tr>
                            )}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                        {viewingReport.question_evaluations
                          .filter(q => (q.question_type || 'technical') === reportView)
                          .map((q, i) => {
                            const qType = q.question_type || 'technical';
                            return (
                              <div
                                key={i}
                                className="bg-muted/30 p-4 rounded-xl border cursor-pointer hover:bg-muted/70 hover:border-primary/40 transition-colors group"
                                onClick={() => setSelectedQuestion(q)}
                              >
                                <div className="flex justify-between items-start mb-3">
                                  <div className="flex items-center gap-2">
                                    <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-primary/10 text-primary text-xs font-bold">
                                      {i + 1}
                                    </span>
                                    <span className={`text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${qType === 'behavioral'
                                      ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400'
                                      : 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                                      }`}>
                                      {qType === 'behavioral' ? 'Behavioral' : 'Technical'}
                                    </span>
                                  </div>
                                  <Badge variant="secondary" className="font-bold tabular-nums">
                                    {q.evaluation.technical_accuracy ?? q.evaluation.overall ?? 0}/10
                                  </Badge>
                                </div>
                                <p className="text-sm font-medium mb-3 line-clamp-2 leading-relaxed">{cleanQuestionText(q.question)}</p>
                                <div className="flex gap-4">
                                  <div className="flex flex-col gap-1 w-1/2">
                                    <span className="text-xs font-semibold text-green-600 dark:text-green-400">Top Strength</span>
                                    <p className="text-xs text-muted-foreground line-clamp-1">{q.evaluation.strengths?.[0] || 'N/A'}</p>
                                  </div>
                                  <div className="flex flex-col gap-1 w-1/2">
                                    <span className="text-xs font-semibold text-red-600 dark:text-red-400">Area to Improve</span>
                                    <p className="text-xs text-muted-foreground line-clamp-1">{q.evaluation.weaknesses?.[0] || 'N/A'}</p>
                                  </div>
                                </div>
                              </div>
                            )
                          }
                          )}
                        {viewingReport.question_evaluations.filter(q => (q.question_type || 'technical') === reportView).length === 0 && (
                          <div className="col-span-full py-20 text-center text-muted-foreground italic">
                            No {reportView} questions found for this interview.
                          </div>
                        )}
                      </div>
                    )}
                  </ScrollArea>
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div >
  )
}
