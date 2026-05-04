'use client'

import React, { useState, useMemo } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { BatchUploadModal } from '@/components/batch-upload-modal'
import { UploadCloud, Download, Loader2, SearchX, CalendarDays, Briefcase, Clock, Filter } from 'lucide-react'
import { useRouter } from 'next/navigation'
import useSWR from 'swr'
import { APIClient } from '@/app/dashboard/lib/api-client'
import { fetcher } from '@/app/dashboard/lib/swr-fetcher'
import * as XLSX from 'xlsx'

// ─── Phone normalizer (mirrored from batch-upload-modal) ────────────
function normalizePhone(rawPhone: string, countryCode?: string | null): string {
  if (!rawPhone || rawPhone.trim() === '') return 'N/A'
  const cleaned = rawPhone.replace(/[\s\-\(\)]/g, '').trim()
  if (!cleaned) return 'N/A'
  const digitsOnly = cleaned.replace(/[^\d]/g, '')
  if (!digitsOnly) return 'N/A'
  if (cleaned.startsWith('+')) return '+' + digitsOnly
  const prefix = countryCode ? countryCode.toString().replace(/\D/g, '') : '91'
  if (digitsOnly.length > 10 && digitsOnly.startsWith(prefix)) return '+' + digitsOnly
  if (digitsOnly.length === 10) return '+' + prefix + digitsOnly
  return '+' + digitsOnly
}

interface Job {
  id: number
  title: string
  status: string
}

interface BatchApplication {
  candidate_name?: string
  candidate_email?: string
  candidate_phone?: string
  country_code?: string
  job?: { title?: string }
  resume_score?: number
  resume_extraction?: { resume_score?: number }
  applied_at?: string
}

const TIME_OPTIONS = [
  { value: 'all', label: 'All Time' },
  { value: 'morning', label: 'Morning (6 AM – 12 PM)' },
  { value: 'afternoon', label: 'Afternoon (12 PM – 6 PM)' },
  { value: 'evening', label: 'Evening (6 PM – 12 AM)' },
  { value: 'night', label: 'Night (12 AM – 6 AM)' },
]

export default function BatchAnalysisPage() {
  const [isBatchModalOpen, setIsBatchModalOpen] = useState(false)
  const router = useRouter()

  // ─── Filter state ─────────────────────────────────────────────
  const [fromDate, setFromDate] = useState('')
  const [toDate, setToDate] = useState('')
  const [filterJobId, setFilterJobId] = useState('all')
  const [timeRange, setTimeRange] = useState('all')

  // ─── Export state ─────────────────────────────────────────────
  const [isExporting, setIsExporting] = useState(false)
  const [exportError, setExportError] = useState('')
  const [exportCount, setExportCount] = useState<number | null>(null)

  const { data: jobs, isLoading: jobsLoading } = useSWR<Job[]>(
    '/api/jobs?limit=500',
    (url: string) => fetcher<Job[]>(url),
  )

  // Validation
  const dateError = useMemo(() => {
    if (fromDate && toDate && fromDate > toDate) return 'From date cannot be after To date'
    const todayStr = new Date().toISOString().slice(0, 10)
    if (fromDate && fromDate > todayStr) return 'From date cannot be in the future'
    if (toDate && toDate > todayStr) return 'To date cannot be in the future'
    return ''
  }, [fromDate, toDate])

  // Human-readable filter summary
  const filterSummary = useMemo(() => {
    const parts: string[] = []
    if (fromDate || toDate) {
      const f = fromDate ? new Date(fromDate + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'Start'
      const t = toDate ? new Date(toDate + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'Present'
      parts.push(`📅 ${f} → ${t}`)
    }
    if (filterJobId !== 'all') {
      const job = jobs?.find(j => j.id.toString() === filterJobId)
      parts.push(`💼 ${job?.title || 'Selected Role'}`)
    }
    if (timeRange !== 'all') {
      const opt = TIME_OPTIONS.find(t => t.value === timeRange)
      parts.push(`⏱ ${opt?.label || timeRange}`)
    }
    return parts
  }, [fromDate, toDate, filterJobId, timeRange, jobs])

  const hasFilters = fromDate || toDate || filterJobId !== 'all' || timeRange !== 'all'

  const clearFilters = () => {
    setFromDate('')
    setToDate('')
    setFilterJobId('all')
    setTimeRange('all')
    setExportError('')
    setExportCount(null)
  }

  // ─── Export handler ───────────────────────────────────────────
  const handleFilteredExport = async () => {
    if (dateError) return
    setIsExporting(true)
    setExportError('')
    setExportCount(null)

    try {
      // Build query params
      const params = new URLSearchParams()
      if (filterJobId !== 'all') params.append('job_id', filterJobId)
      if (fromDate) params.append('from_date', fromDate)
      if (toDate) params.append('to_date', toDate)
      if (timeRange !== 'all') params.append('time_range', timeRange)
      params.append('limit', '1000')

      const qs = params.toString()
      const url = `/api/applications${qs ? '?' + qs : ''}`

      // BA_033: Warn if no filters are applied
      if (!hasFilters) {
        const confirmAll = window.confirm('You are about to export ALL candidates without any filters. This may take a moment. Continue?')
        if (!confirmAll) {
          setIsExporting(false)
          return
        }
      }

      const response = await APIClient.get(url) as any
      const data = Array.isArray(response) ? response : (response?.items || [])

      if (!data || data.length === 0) {
        setExportError('No candidates found for selected filters.')
        setExportCount(0)
        return
      }

      setExportCount(data.length)

      // Build Excel rows
      const rows = data.map((app: BatchApplication) => {
        const name = app.candidate_name || 'Unknown'
        const email = app.candidate_email || 'N/A'
        const phone = normalizePhone(app.candidate_phone || '', app.country_code || null)
        const role = app.job?.title || 'Unknown Role'
        const rawScore = app.resume_score ?? app.resume_extraction?.resume_score ?? 0
        const pctScore = rawScore <= 10 && rawScore > 0 ? rawScore * 10 : rawScore
        const match = pctScore >= 50 ? 'YES' : 'NO'
        const appliedAt = app.applied_at ? new Date(app.applied_at).toLocaleString() : 'N/A'

        return {
          'Name': name,
          'Email': email,
          'Phone Number': phone,
          'Job Role': role,
          'Applied At': appliedAt,
          'MATCH': match,
        }
      })

      const worksheet = XLSX.utils.json_to_sheet(rows)
      const workbook = XLSX.utils.book_new()
      XLSX.utils.book_append_sheet(workbook, worksheet, 'Candidates')

      // Generate filename with filter context
      const datePart = fromDate || toDate ? `_${fromDate || 'start'}_to_${toDate || 'present'}` : ''
      const rolePart = filterJobId !== 'all' ? `_${(jobs?.find(j => j.id.toString() === filterJobId)?.title || 'role').replace(/\s+/g, '_')}` : ''
      XLSX.writeFile(workbook, `candidates_export${datePart}${rolePart}.xlsx`)
    } catch (err) {
      console.error('Export failed:', err)
      setExportError(err instanceof Error ? err.message : 'Failed to export data.')
    } finally {
      setIsExporting(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Batch Resume Analysis</h1>
          <p className="text-muted-foreground mt-2">
            Upload and process multiple resumes, or export filtered candidate data.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* ─── Bulk Upload Card ──────────────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <UploadCloud className="h-5 w-5 text-primary" />
              Bulk Processing Engine
            </CardTitle>
            <CardDescription>
              Supported inputs: PDF/DOCX files, nested folders, or ZIP archives (max 25 per batch).
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="bg-muted/30 border border-dashed rounded-xl p-8 text-center flex flex-col items-center justify-center">
              <div className="w-14 h-14 bg-primary/10 rounded-full flex items-center justify-center mb-4">
                <UploadCloud className="h-7 w-7 text-primary" />
              </div>
              <h3 className="text-lg font-semibold mb-2">Ready to ingest resumes</h3>
              <p className="text-muted-foreground text-sm max-w-md mx-auto mb-6">
                Our AI engine maps resumes to job roles, strips duplicates, extracts identities, and prepares spreadsheets for export.
              </p>
              <Button
                onClick={() => setIsBatchModalOpen(true)}
                size="lg"
                className="gap-2"
              >
                <UploadCloud className="h-4 w-4" />
                Run Batch Analysis
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* ─── Filtered Export Card ──────────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Filter className="h-5 w-5 text-primary" />
              Export Filtered Data
            </CardTitle>
            <CardDescription>
              Download candidate data filtered by date, role, or time-of-day directly as Excel (Max 1000 per export).
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            {/* Date Range */}
            <div className="space-y-2">
              <Label className="flex items-center gap-1.5 text-sm font-medium">
                <CalendarDays className="h-3.5 w-3.5 text-muted-foreground" />
                Date Range
              </Label>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="text-xs text-muted-foreground mb-1 block">From</Label>
                  <Input
                    type="date"
                    value={fromDate}
                    onChange={(e) => setFromDate(e.target.value)}
                    className="text-sm"
                  />
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground mb-1 block">To</Label>
                  <Input
                    type="date"
                    value={toDate}
                    onChange={(e) => setToDate(e.target.value)}
                    className="text-sm"
                  />
                </div>
              </div>
              {dateError && (
                <p className="text-xs text-destructive mt-1">{dateError}</p>
              )}
            </div>
            <div className="grid grid-cols-2 gap-3">
              
                {/* Job Role */}
                <div className="space-y-2">
                  <Label className="flex items-center gap-1.5 text-sm font-medium">
                    <Briefcase className="h-3.5 w-3.5 text-muted-foreground" />
                    Job Role
                  </Label>
                  <Select value={filterJobId} onValueChange={setFilterJobId} disabled={jobsLoading}>
                    <SelectTrigger className="text-sm">
                      <SelectValue placeholder={jobsLoading ? 'Loading...' : 'All Roles'} />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Roles</SelectItem>
                      {jobs?.filter(j => j.status === 'open').map(job => (
                        <SelectItem key={job.id} value={job.id.toString()}>
                          {job.title}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Time Window */}
                <div className="space-y-2">
                  <Label className="flex items-center gap-1.5 text-sm font-medium">
                    <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                    Applied Time
                  </Label>
                  <Select value={timeRange} onValueChange={setTimeRange}>
                    <SelectTrigger className="text-sm">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {TIME_OPTIONS.map(opt => (
                        <SelectItem key={opt.value} value={opt.value}>
                          {opt.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
            
            </div>
            {/* Filter Summary */}
            {filterSummary.length > 0 && (
              <div className="bg-primary/5 border border-primary/10 rounded-lg p-3 space-y-1">
                <p className="text-xs font-bold text-primary uppercase tracking-wider">Exporting with filters:</p>
                {filterSummary.map((line, i) => (
                  <p key={i} className="text-sm text-foreground">{line}</p>
                ))}
              </div>
            )}

            {/* Export Error / Empty */}
            {exportError && (
              <div className="flex items-center gap-2 bg-destructive/10 text-destructive border border-destructive/20 rounded-lg p-3">
                <SearchX className="h-4 w-4 shrink-0" />
                <p className="text-sm font-medium">{exportError}</p>
              </div>
            )}

            {/* Export Success Count */}
            {exportCount !== null && exportCount > 0 && !exportError && (
              <p className="text-sm text-emerald-600 font-medium">
                ✅ Successfully exported {exportCount} candidates.
              </p>
            )}

            {/* Action Buttons */}
            <div className="flex gap-3 pt-2">
              <Button
                onClick={handleFilteredExport}
                disabled={isExporting || !!dateError}
                className="flex-1 gap-2"
              >
                {isExporting ? (
                  <><Loader2 className="h-4 w-4 animate-spin" /> Exporting...</>
                ) : (
                  <><Download className="h-4 w-4" /> Download Excel</>
                )}
              </Button>
              {hasFilters && (
                <Button variant="outline" onClick={clearFilters} className="shrink-0">
                  Clear Filters
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <BatchUploadModal
        isOpen={isBatchModalOpen}
        onClose={() => setIsBatchModalOpen(false)}
        onSuccess={() => {
          setIsBatchModalOpen(false)
          router.push('/dashboard/hr/applications')
        }}
      />
    </div>
  )
}
