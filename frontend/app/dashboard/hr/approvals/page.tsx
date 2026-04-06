'use client'

import React from 'react'
import Link from 'next/link'
import useSWR from 'swr'
import { useAuth } from '@/app/dashboard/lib/auth-context'
import { APIClient } from '@/app/dashboard/lib/api-client'
import { fetcher } from '@/app/dashboard/lib/swr-fetcher'
import { performMutation } from '@/app/dashboard/lib/swr-utils'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Check, ArrowRight, Trash2 } from 'lucide-react'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'

export default function ApprovalsPage() {
  const { user, isLoading: isAuthLoading } = useAuth()
  const [processingId, setProcessingId] = React.useState<number | null>(null)
  const [status, setStatus] = React.useState<string>('pending')

  const isSuperAdmin = user?.role === 'super_admin'
  const shouldFetch = isSuperAdmin
  const fetchUrl = `/api/auth/hr-requests?status=${status}`
  const { data: hrUsers = [], error, isValidating, mutate } = useSWR<any[]>(
    shouldFetch ? fetchUrl : null,
    (url: string) => fetcher<any[]>(url)
  )

  const userCount = hrUsers.length

  const handleApprove = async (userId: number) => {
    setProcessingId(userId)
    try {
      await performMutation<any[]>(
        fetchUrl,
        mutate,
        () => APIClient.post(`/api/auth/approve/${userId}`, {}),
        {
          lockKey: `approval-${userId}`,
          successMessage: 'HR user approved successfully',
          invalidateKeys: [fetchUrl, '/api/analytics/dashboard']
        }
      )
    } catch (err) {
      console.error('Failed to approve user', err)
    } finally {
      setProcessingId(null)
    }
  }

  const handleReject = async (userId: number) => {
    if (!confirm('Are you sure you want to reject this HR registration?')) return
    setProcessingId(userId)
    try {
      await performMutation<any[]>(
        fetchUrl,
        mutate,
        () => APIClient.post(`/api/auth/reject/${userId}`, {}),
        {
          lockKey: `approval-${userId}`,
          successMessage: 'HR user rejected',
          invalidateKeys: [fetchUrl, '/api/analytics/dashboard']
        }
      )
    } catch (err) {
      console.error('Failed to reject user', err)
    } finally {
      setProcessingId(null)
    }
  }

  const handleRemove = async (userId: number) => {
    if (!confirm('Are you sure you want to deactivate this HR account? They will no longer be able to log in.')) return
    setProcessingId(userId)
    try {
      await performMutation<any[]>(
        fetchUrl,
        mutate,
        () => APIClient.delete(`/api/auth/remove/${userId}`),
        {
          lockKey: `approval-remove-${userId}`,
          successMessage: 'HR user deactivated',
          invalidateKeys: [fetchUrl, '/api/analytics/dashboard']
        }
      )
    } catch (err) {
      console.error('Failed to deactivate user', err)
    } finally {
      setProcessingId(null)
    }
  }

  if (isAuthLoading || (shouldFetch && isValidating && hrUsers.length === 0)) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary" />
      </div>
    )
  }

  if (!user || !isSuperAdmin) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background px-4">
        <Card className="max-w-xl w-full">
          <CardHeader>
            <CardTitle>Access denied</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              This page is reserved for Super Admin accounts only.
            </p>
            <div className="mt-4">
              <Link href="/dashboard/hr">
                <Button>Return to dashboard</Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  const getStatusBadge = (user: any) => {
    if (user.approval_status === 'pending') {
      return <Badge variant="outline" className="bg-yellow-100 text-yellow-700 border-yellow-200">Pending</Badge>
    }
    if (user.approval_status === 'approved' && user.is_active) {
      return <Badge variant="outline" className="bg-green-100 text-green-700 border-green-200">Approved</Badge>
    }
    if (user.approval_status === 'approved' && !user.is_active) {
      return <Badge variant="outline" className="bg-slate-100 text-slate-700 border-slate-200">Deactivated</Badge>
    }
    if (user.approval_status === 'rejected') {
      return <Badge variant="outline" className="bg-red-100 text-red-700 border-red-200">Rejected</Badge>
    }
    return <Badge variant="outline">{user.approval_status}</Badge>
  }

  return (
    <div className="p-4 md:p-8 space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.25em] text-primary">Admin management</p>
          <h1 className="text-3xl font-semibold text-slate-900">HR Account Management</h1>
          <p className="text-sm text-muted-foreground mt-2">Manage HR access, approve requests, and deactivate accounts.</p>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/dashboard/hr">
            <Button variant="outline" className="whitespace-nowrap">
              <ArrowRight className="mr-2 h-4 w-4" /> Back to dashboard
            </Button>
          </Link>
        </div>
      </div>

      <Tabs value={status} onValueChange={setStatus} className="w-full">
        <TabsList className="grid w-full grid-cols-3 max-w-md">
          <TabsTrigger value="pending">Pending</TabsTrigger>
          <TabsTrigger value="approved">Approved</TabsTrigger>
          <TabsTrigger value="rejected">Rejected</TabsTrigger>
        </TabsList>
      </Tabs>

      <Card className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>{status.charAt(0).toUpperCase() + status.slice(1)} HR Users</CardTitle>
            <CardDescription>
              {status === 'pending' && "Confirm and enable verified HR users."}
              {status === 'approved' && "Manage active HR accounts."}
              {status === 'rejected' && "View rejected registration requests."}
            </CardDescription>
          </div>
          <Badge variant="secondary" className="bg-primary/10 text-primary hover:bg-primary/20">
            {userCount} {status}
          </Badge>
        </CardHeader>
        <CardContent>
          {error ? (
            <div className="rounded-xl border border-destructive/20 bg-destructive/10 p-4 text-sm text-destructive">
              Failed to load users. Please refresh the page.
            </div>
          ) : userCount === 0 ? (
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-8 text-center text-sm text-muted-foreground">
              No {status} HR accounts found.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Full Name</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {hrUsers.map((hrUser) => (
                  <TableRow key={hrUser.id} className="hover:bg-muted/50 transition-colors">
                    <TableCell>{hrUser.id}</TableCell>
                    <TableCell>{hrUser.email}</TableCell>
                    <TableCell>{hrUser.full_name}</TableCell>
                    <TableCell>
                      {getStatusBadge(hrUser)}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        {status === 'pending' && (
                          <>
                            <Button
                              size="sm"
                              variant="destructive"
                              disabled={processingId === hrUser.id}
                              onClick={() => handleReject(hrUser.id)}
                            >
                              Reject
                            </Button>
                            <Button
                              size="sm"
                              disabled={processingId === hrUser.id}
                              onClick={() => handleApprove(hrUser.id)}
                            >
                              <Check className="mr-2 h-4 w-4" />
                              Approve
                            </Button>
                          </>
                        )}
                        {status === 'approved' && hrUser.is_active && (
                          <Button
                            size="sm"
                            variant="destructive"
                            disabled={processingId === hrUser.id}
                            onClick={() => handleRemove(hrUser.id)}
                          >
                            <Trash2 className="mr-2 h-4 w-4" />
                            Deactivate
                          </Button>
                        )}
                        {status === 'rejected' && (
                          <span className="text-xs text-muted-foreground italic">No actions available</span>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
