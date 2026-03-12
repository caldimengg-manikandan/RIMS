'use client';

import React from 'react';
import { useParams, useSearchParams } from 'next/navigation';
import InterviewSession from '@/modules/interview/InterviewSession';

export default function LiveInterviewPage() {
    const params = useParams();
    const searchParams = useSearchParams();

    // In a real flow, the backend provides the interview ID and token securely
    const sessionId = params.id as string || "test-session";
    const token = searchParams.get('token') || "dummy_jwt_token";

    return (
        <div className="min-h-screen bg-[#f8fafc] flex flex-col pt-12">
            <header className="fixed top-0 w-full h-16 bg-white/80 backdrop-blur-md border-b border-slate-200 px-10 flex items-center justify-between z-20">
                <div className="flex items-center gap-6">
                    <h1 className="text-xl font-black text-slate-900 tracking-tight">Enterprise WebSockets Interview</h1>
                </div>
                <div className="text-sm font-medium text-slate-500">
                    Session: {sessionId}
                </div>
            </header>

            <main className="flex-1 w-full max-w-7xl mx-auto p-6 md:p-12 overflow-hidden">
                <InterviewSession sessionId={sessionId} token={token} />
            </main>
        </div>
    );
}
