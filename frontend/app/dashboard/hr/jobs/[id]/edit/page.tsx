'use client'

import React, { useState } from 'react'
import { useRouter } from 'next/navigation'
import useSWR, { useSWRConfig } from 'swr'
import { fetcher } from '@/app/dashboard/lib/swr-fetcher'
import { performMutation } from '@/app/dashboard/lib/swr-utils'
import { APIClient } from '@/app/dashboard/lib/api-client'
import { JobForm } from '@/components/job-form'
import { Loader2 } from 'lucide-react'

interface PageProps {
    params: Promise<{ id: string }>
}

export default function HREditJobPage({ params }: PageProps) {
    const router = useRouter()
    const { mutate: globalMutate } = useSWRConfig()
    const unwrappedParams = React.use(params)
    const jobId = unwrappedParams.id
    const [isSubmitting, setIsSubmitting] = useState(false)

    const { data: job, isLoading } = useSWR<any>(
        jobId ? `/api/jobs/${jobId}` : null,
        fetcher
    )

    const handleSubmit = async (formData: any) => {
        if (!jobId) return
        setIsSubmitting(true)

        try {
            const actionFn = () => APIClient.put(`/api/jobs/${jobId}`, formData)
            
            await performMutation(
                '/api/jobs',
                (data, options) => globalMutate('/api/jobs', data as any, options as any),
                actionFn,
                {
                    lockKey: `job-${jobId}`,
                    successMessage: 'Job updated successfully',
                    invalidateKeys: [`/api/jobs/${jobId}`, '/api/analytics/dashboard']
                }
            )

            router.push('/dashboard/hr/jobs')
        } catch (err) {
            console.error(err)
            setIsSubmitting(false)
        }
    }

    if (isLoading) {
        return (
            <div className="flex justify-center items-center min-h-[60vh]">
                <Loader2 className="animate-spin h-10 w-10 text-primary" />
            </div>
        )
    }

    return (
        <JobForm 
            mode="edit"
            initialData={job}
            onSubmit={handleSubmit}
            isSubmitting={isSubmitting}
        />
    )
}
