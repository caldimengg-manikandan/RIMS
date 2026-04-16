'use client'

import React, { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useSWRConfig } from 'swr'
import { performMutation } from '@/app/dashboard/lib/swr-utils'
import { APIClient } from '@/app/dashboard/lib/api-client'
import { JobForm } from '@/components/job-form'

export default function HRCreateJobPage() {
    const router = useRouter()
    const { mutate: globalMutate } = useSWRConfig()
    const [isSubmitting, setIsSubmitting] = useState(false)

    const handleSubmit = async (formData: any) => {
        if (isSubmitting) return
        setIsSubmitting(true)
        try {
            const actionFn = () => APIClient.post('/api/jobs', formData)

            await performMutation(
                '/api/jobs',
                (data, options) => globalMutate('/api/jobs', data as any, options as any),
                actionFn,
                {
                    lockKey: 'job-create',
                    successMessage: 'Job posted successfully',
                    invalidateKeys: ['/api/analytics/dashboard']
                }
            )

            router.push('/dashboard/hr/jobs')
        } catch (err) {
            console.error(err)
            setIsSubmitting(false)
        }
    }

    return (
        <JobForm 
            mode="create"
            onSubmit={handleSubmit}
            isSubmitting={isSubmitting}
        />
    )
}
