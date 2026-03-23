'use client'

import React, { useEffect, useState, useMemo } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import Link from 'next/link'
import { APIClient } from '@/app/dashboard/lib/api-client'
import useSWR from 'swr'
import { fetcher } from '@/app/dashboard/lib/swr-fetcher'
import dynamic from 'next/dynamic'
import {
  Briefcase,
  Users,
  Calendar,
  CheckCircle,
  TrendingUp,
  Clock,
  ArrowRight,
  Search,
  Filter,
  X,
  Award,
  RotateCw,
  RotateCcw
} from 'lucide-react'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

// Lazy-load the entire chart component — defers Recharts bundle (~200KB)
const DashboardChart = dynamic(
  () => import('@/components/dashboard-chart').then(mod => ({ default: mod.DashboardChart })),
  {
    ssr: false,
    loading: () => (
      <div className="h-[300px] flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }
)
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'

interface DashboardData {
  recruitment_metrics: {
    total_candidates: number
    shortlisted_candidates: number
    interviewed_candidates: number
    offers_released: number
    hiring_success_rate: number
  }
  candidate_metrics: {
    avg_job_compatibility: number
    avg_aptitude_score: number
    avg_interview_score: number
    avg_composite_score: number
  }
  chart_data: { name: string; value: number }[]
  recent_interviews: any[]
}

export default function HRDashboard() {
  const { data: dashboardData, error: dashboardError, isLoading: dashboardLoading } = useSWR<DashboardData>('/api/analytics/dashboard', (url: string) => fetcher<DashboardData>(url))

  // Filter States
  const [filters, setFilters] = useState<any>({
    search: '',
    date: '',
    status: 'all'
  })
  
  const [debouncedSearch, setDebouncedSearch] = useState(filters.search)

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(filters.search)
    }, 500)
    return () => clearTimeout(timer)
  }, [filters.search])

  // We use SWR for the initial filtered interviews as well
  const filterQuery = useMemo(() => {
    const params = new URLSearchParams()
    if (debouncedSearch) params.append('search', debouncedSearch)
    if (filters.date) params.append('date', filters.date)
    if (filters.status && filters.status !== 'all') params.append('status', filters.status)
    return params.toString()
  }, [debouncedSearch, filters.date, filters.status])

  const { data: filteredInterviews, isValidating: isFiltering, mutate: mutateInterviews } = useSWR<any[]>(
    `/api/analytics/interviews${filterQuery ? `?${filterQuery}` : ''}`,
    (url: string) => fetcher<any[]>(url),
    { keepPreviousData: true }
  )

  // ... helper calculations ...
  const r_metrics = dashboardData?.recruitment_metrics || {
    total_candidates: 0,
    shortlisted_candidates: 0,
    interviewed_candidates: 0,
    offers_released: 0,
    hiring_success_rate: 0
  }
  
  const c_metrics = dashboardData?.candidate_metrics || {
    avg_job_compatibility: 0,
    avg_aptitude_score: 0,
    avg_interview_score: 0,
    avg_composite_score: 0
  }

  const chartData = dashboardData?.chart_data || []
  const recentInterviews = Array.isArray(filteredInterviews) ? filteredInterviews : (Array.isArray(dashboardData?.recent_interviews) ? dashboardData?.recent_interviews : [])

  const handleReset = () => {
    setFilters({
      search: '',
      date: '',
      status: 'all'
    })
  }

  const COLORS = ['#3b82f6', '#8b5cf6', '#f59e0b', '#10b981', '#ef4444'];

  if (dashboardLoading && !dashboardData) {
    return (
      <div className="p-8 flex justify-center items-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <div className="p-4 md:p-0 space-y-8">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">
            Enterprise Recruitment Dashboard
          </h1>
          <p className="text-sm text-muted-foreground mt-1">AI-Powered Hiring Intelligence</p>
        </div>
        <Link href="/dashboard/hr/jobs/create">
          <Button className="bg-primary hover:bg-primary/90 text-primary-foreground shadow-md hover:shadow-lg transition-all">
            <Briefcase className="mr-2 h-4 w-4" />
            Create Job Posting
          </Button>
        </Link>
      </div>

      {/* Stats Cards AI Enhanced */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <StatsCard
          title="Total Candidates"
          value={r_metrics.total_candidates}
          icon={Users}
          color="text-primary"
          bg="bg-primary/10"
        />
        <StatsCard
          title="Hiring Success"
          value={`${r_metrics.hiring_success_rate}%`}
          icon={TrendingUp}
          color="text-emerald-600"
          bg="bg-emerald-500/10"
        />
        <StatsCard
          title="Avg Candidate Score"
          value={c_metrics.avg_composite_score}
          icon={Award}
          color="text-amber-600"
          bg="bg-amber-500/10"
        />
        <StatsCard
          title="Offers Released"
          value={r_metrics.offers_released}
          icon={CheckCircle}
          color="text-blue-600"
          bg="bg-blue-500/10"
        />
      </div>

      {/* Charts & Tables Section */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">

        {/* Chart Section */}
        <div className="lg:col-span-3 animate-in fade-in duration-500 delay-300">
          <Card className="h-full shadow-none border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-xl">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-slate-800 dark:text-slate-200">Application Pipeline</CardTitle>
                  <CardDescription className="text-muted-foreground">Distribution of candidates by status</CardDescription>
                </div>
                <div className=" bg-blue-50 text-blue-600 rounded-lg">
                  <TrendingUp className="h-5 w-5" />
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="h-[300px] w-full">
                <DashboardChart data={chartData} />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Recent Activity / Quick Actions */}
        <div className="lg:col-span-1 space-y-6 animate-in fade-in duration-500 delay-500">
          <Card className="h-full shadow-none border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-xl">
            <CardHeader>
              <CardTitle className="text-slate-800 dark:text-slate-200">Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <ActionButton href="/dashboard/hr/applications" label="Review Applications" />
              <ActionButton href="/dashboard/hr/pipeline" label="Hiring Pipeline" />
              <ActionButton href="/dashboard/hr/reports" label="View Reports" />
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Recent Interviews Table */}
      <Card className="shadow-none border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 rounded-xl animate-in fade-in duration-500 delay-700">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-slate-800 dark:text-slate-200">Recent Interviews</CardTitle>
              <CardDescription>Upcoming and recently completed sessions</CardDescription>
            </div>
            <Clock className="h-5 w-5 text-muted-foreground" />
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Filter Bar */}
          <div className="flex flex-col md:flex-row gap-4 p-4 bg-slate-50/50 dark:bg-slate-900/50 rounded-xl border border-slate-200 dark:border-slate-800 items-center">
            <div className="flex-1 w-full relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search candidates, roles, or IDs..."
                value={filters.search}
                onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                className="bg-white dark:bg-slate-950 h-10 pl-10 pr-10 border-slate-200 focus:ring-primary shadow-sm"
              />
              {isFiltering && (
                <RotateCw className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-primary animate-spin" />
              )}
            </div>

            <div className="w-full md:w-48">
              <Select
                value={filters.status}
                onValueChange={(value) => setFilters({ ...filters, status: value })}
              >
                <SelectTrigger className="bg-white dark:bg-slate-950 h-10 border-slate-200 shadow-sm">
                  <SelectValue placeholder="All Statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Statuses</SelectItem>
                  <SelectItem value="not_started">Pending</SelectItem>
                  <SelectItem value="in_progress">In Progress</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                  <SelectItem value="cancelled">Cancelled</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Button
              variant="outline"
              size="icon"
              onClick={handleReset}
              className="h-10 w-10 shrink-0 border-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-all shadow-sm"
              title="Reset all filters"
            >
              <RotateCcw className="h-4 w-4 text-muted-foreground" />
            </Button>
          </div>

          {recentInterviews.length > 0 ? (
            <div className="relative">
              {isFiltering && (
                <div className="absolute inset-0 bg-background/20 backdrop-blur-[1px] z-10 flex items-center justify-center rounded-md">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                </div>
              )}
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Candidate ID</TableHead>
                    <TableHead>Candidate</TableHead>
                    <TableHead>Job Role</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {recentInterviews.map((interview: any) => (
                    <TableRow key={interview.id} className="group hover:bg-muted/50 transition-colors">
                      <TableCell className="font-mono text-sm text-muted-foreground">
                        {interview.test_id || 'N/A'}
                      </TableCell>
                      <TableCell className="font-medium">{interview.candidate_name}</TableCell>
                      <TableCell>{interview.job_title}</TableCell>
                      <TableCell>{new Date(interview.date).toLocaleDateString()}</TableCell>
                      <TableCell>
                        <Badge variant={
                          interview.status === 'completed' ? 'default' :
                            interview.status === 'scheduled' ? 'secondary' : 'outline'
                        } className={
                          interview.status === 'completed' ? 'bg-primary/10 text-primary hover:bg-primary/20 ' :
                            interview.status === 'scheduled' ? 'bg-secondary/10 text-secondary hover:bg-secondary/20 ' : ''
                        }>
                          {interview.status.replace('_', ' ')}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <Link 
                          href={interview.report_id ? `/dashboard/hr/reports?search=${encodeURIComponent(interview.candidate_name)}&reportId=${interview.report_id}` : `/dashboard/hr/applications`} 
                          className="text-primary hover:underline text-sm font-medium"
                        >
                          View Details
                        </Link>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <div className="text-center py-12 text-muted-foreground border-2 border-dashed border-muted rounded-lg">
              <div className="p-3 bg-muted w-fit rounded-full mx-auto mb-3">
                <Search className="h-6 w-6" />
              </div>
              <p className="font-medium">No interviews match your filters.</p>
              <Button variant="link" onClick={handleReset} className="text-primary">Clear all filters</Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

const StatsCard = React.memo(({ title, value, icon: Icon, color, bg }: any) => {
  return (
    <Card className="shadow-sm hover:shadow-lg transition-all duration-300 border-border bg-card group hover:-translate-y-1">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-base font-bold text-muted-foreground group-hover:text-foreground transition-colors">
          {title}
        </CardTitle>
        <div className={`p-2 rounded-full ${bg}`}>
          <Icon className={`h-4 w-4 ${color}`} />
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-3xl font-bold text-slate-900 dark:text-white mt-1">{value}</div>
      </CardContent>
    </Card>
  )
})

const ActionButton = React.memo(({ href, label }: { href: string, label: string }) => {
  return (
    <Link href={href} className="block group">
      <Button variant="outline" className="w-full justify-between hover:border-primary/50 hover:bg-primary/5 transition-all">
        {label}
        <ArrowRight className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
      </Button>
    </Link>
  )
})
