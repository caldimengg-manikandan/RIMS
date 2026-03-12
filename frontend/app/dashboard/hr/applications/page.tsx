"use client";

import React, { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { APIClient } from "@/app/dashboard/lib/api-client";
import { RejectDialog } from "@/components/reject-dialog";
import useSWR, { useSWRConfig } from "swr";
import { fetcher } from "@/app/dashboard/lib/swr-fetcher";
import { useRouter } from "next/navigation";
import { API_BASE_URL } from "@/lib/config";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

interface Application {
  id: number;
  status: string;
  applied_at: string;
  candidate_name: string;
  candidate_email: string;
  job: {
    id: number;
    job_id: string | null;
    title: string;
  };
  interview: {
    id: number;
    test_id: string | null;
    report: {
      aptitude_score: number | null;
      technical_skills_score: number | null;
      behavioral_score: number | null;
    } | null;
  } | null;
  resume_extraction: {
    resume_score: number;
    skill_match_percentage: number;
    summary: string | null;
    extracted_skills: string | null;
  } | null;
}

export default function HRApplicationsPage() {
  const router = useRouter();
  const {
    data: applications = [],
    error,
    isLoading,
    mutate,
  } = useSWR<Application[]>(
    "/api/applications",
    (url: string) => fetcher<Application[]>(url),
    { keepPreviousData: true },
  );
  const { mutate: globalMutate } = useSWRConfig();

  const handleDecision = async (
    applicationId: number,
    decision: "hired" | "rejected",
    reason?: string,
    notes?: string,
  ) => {
    // Optimistic update
    const updatedApps = applications.map((app) =>
      app.id === applicationId
        ? {
            ...app,
            status: decision === "hired" ? "hired" : "rejected",
          }
        : app,
    );

    try {
      // Update local cache immediately
      mutate(updatedApps, false);

      let userComments = `Candidate ${decision} via quick action in applications list.`;
      if (decision === "rejected") {
        userComments = `Reason: ${reason}${notes ? `\nNotes: ${notes}` : ""}`;
      }

      await APIClient.put(
        `/api/decisions/applications/${applicationId}/decide`,
        {
          decision,
          decision_comments: userComments,
        },
      );

      // Revalidate
      mutate();
      // Also update dashboard stats if they are cached
      globalMutate("/api/analytics/dashboard");
    } catch (err) {
      // Rollback on error
      mutate();
      console.error("Failed to make decision:", err);
      const errorMsg =
        (err as any)?.response?.data?.detail ||
        "Failed to make decision. Ensure the candidate has completed the interview Round.";
      alert(errorMsg);
      throw err;
    }
  };

  const handleTransition = async (
    applicationId: number,
    action: string,
    notes?: string,
  ) => {
    try {
      mutate(
        applications.map((app) =>
          app.id === applicationId ? { ...app } : app,
        ),
        false,
      );

      await APIClient.put(`/api/applications/${applicationId}/status`, {
        action,
        hr_notes: notes || `Action: ${action}`,
      });

      mutate();
      globalMutate("/api/analytics/dashboard");
    } catch (err) {
      mutate();
      console.error("Failed to execute transition:", err);
      const errorMsg =
        (err as any)?.message || "Failed to execute action.";
      alert(errorMsg);
    }
  };

  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [dateFilter, setDateFilter] = useState("");

  // Get unique job titles for the filter dropdown
  const jobTitles = Array.from(
    new Set(applications.map((app) => app.job.title)),
  ).sort();

  const filteredApplications = applications
    .filter((app) => {
      // Global search (candidate name, candidate email, job title, job ID, candidate ID)
      const search = searchTerm.toLowerCase();
      const matchesSearch =
        (app.candidate_name || "").toLowerCase().includes(search) ||
        (app.candidate_email || "").toLowerCase().includes(search) ||
        (app.job.title || "").toLowerCase().includes(search) ||
        (app.job.job_id || "").toLowerCase().includes(search) ||
        (app.id || "").toString().includes(search);

      // Status filter
      let matchesStatus = statusFilter === "all" || app.status === statusFilter;
      if (statusFilter === "applied") {
        matchesStatus = app.status === "applied" || app.status === "submitted";
      }
      if (statusFilter === "rejected") {
        matchesStatus =
          app.status === "rejected";
      }

      // Date filter (matching YYYY-MM-DD)
      const appDate = new Date(app.applied_at).toISOString().split("T")[0];
      const matchesDate = !dateFilter || appDate === dateFilter;

      return matchesSearch && matchesStatus && matchesDate;
    })
    .sort((a, b) => {
      // Default sort: Newest First
      return (
        new Date(b.applied_at).getTime() - new Date(a.applied_at).getTime()
      );
    });

  const getStatusColor = (status: string) => {
    switch (status) {
      case "applied":
      case "submitted":
        return "capsule-badge-primary";
      case "review_later":
        return "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20";
      case "aptitude_round":
      case "ai_interview":
      case "ai_interview_completed":
        return "capsule-badge-info";
      case "physical_interview":
        return "capsule-badge-primary";
      case "hired":
        return "capsule-badge-success";
      case "rejected":
        return "capsule-badge-destructive";
      default:
        return "capsule-badge-neutral";
    }
  };

  return (
    <div className="space-y-8">
      <h1 className="text-4xl font-black text-foreground mb-2 tracking-tight">
        Applications
      </h1>
      <p className="text-muted-foreground mb-8">
        Review and manage candidate applications.
      </p>

      {/* Filters Toolbar */}
      <div className="bg-card p-6 rounded-2xl border border-border/50 shadow-sm mb-8 animate-in fade-in slide-in-from-top-4 duration-700 ease-out">
        <div className="flex flex-wrap gap-4 items-end">
          {/* Combined Search Bar */}
          <div className="flex-1 min-w-[300px]">
            <div className="relative group">
              <svg
                className="absolute left-4 top-1/2 transform -translate-y-1/2 text-muted-foreground group-focus-within:text-primary h-5 w-5 transition-colors"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
              <input
                type="text"
                placeholder="Search candidate name, ID, or job details..."
                className="w-full pl-12 pr-4 h-11 bg-background border-2 border-input rounded-xl focus:outline-none focus:ring-4 focus:ring-primary/5 focus:border-primary transition-all text-base placeholder:text-muted-foreground text-foreground"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>

          {/* Date Filter */}
          <div className="w-[200px]">
            <input
              type="date"
              className="w-full px-4 h-11 bg-background border-2 border-input rounded-xl text-sm font-medium focus:outline-none focus:ring-4 focus:ring-primary/5 focus:border-primary transition-all text-foreground cursor-pointer"
              value={dateFilter}
              onChange={(e) => setDateFilter(e.target.value)}
            />
          </div>

          {/* Status Filter */}
          <div className="w-[200px]">
            <select
              className="w-full px-4 h-11 bg-background border-2 border-input rounded-xl text-base font-medium focus:outline-none focus:ring-4 focus:ring-primary/5 focus:border-primary transition-all text-foreground cursor-pointer"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="all">All Statuses</option>
              <option value="applied">Applied</option>
              <option value="aptitude_round">Aptitude Round</option>
              <option value="ai_interview">AI Interview</option>
              <option value="ai_interview_completed">AI Completed</option>
              <option value="review_later">Review Later</option>
              <option value="physical_interview">Physical Interview</option>
              <option value="hired">Hired</option>
              <option value="rejected">Rejected</option>
            </select>
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
        </div>
      ) : filteredApplications.length === 0 ? (
        <div className="text-center py-16 bg-card rounded-xl border border-border">
          <p className="text-muted-foreground">
            No applications match your filtering criteria.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {filteredApplications.map((app, index) => (
            <Card
              key={app.id}
              onClick={() =>
                router.push(`/dashboard/hr/applications/${app.id}`)
              }
              style={{ animationDelay: `${index * 50}ms` }}
              className="hover:shadow-md transition-all duration-300 bg-card border border-border hover:border-border/80 cursor-pointer group animate-in fade-in slide-in-from-bottom-4 duration-500 ease-out fill-mode-both"
            >
              <CardContent className="p-3 flex items-center justify-between">
                <div className="flex items-center gap-4 flex-1">
                  <div className="relative shrink-0">
                    <div className="h-14 w-14 rounded-full overflow-hidden border-2 border-border/50 bg-muted flex items-center justify-center shadow-sm">
                      {(app as any).candidate_photo_path ? (
                        <img
                          src={`${API_BASE_URL}/${(app as any).candidate_photo_path.replace(/\\/g, "/")}`}
                          alt={app.candidate_name}
                          className="h-full w-full object-cover"
                        />
                      ) : (
                        <span className="text-lg font-bold text-muted-foreground">
                          {app.candidate_name.charAt(0).toUpperCase()}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="text-base font-bold text-foreground group-hover:text-primary transition-colors">
                        {app.candidate_name}
                      </h3>
                      {app.job.job_id && (
                        <span className="text-[10px] bg-muted px-1.5 py-0.5 rounded text-muted-foreground border border-border">
                          {app.job.job_id}
                        </span>
                      )}
                      {app.interview?.test_id && (
                        <span className="text-[10px] bg-muted px-1.5 py-0.5 rounded text-muted-foreground border border-border">
                          {app.interview.test_id}
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground">
                      Applied for{" "}
                      <span className="font-medium text-foreground">
                        {app.job.title}
                      </span>
                    </p>
                    <div className="flex flex-wrap gap-1 mt-0.5 mb-1">
                      {(() => {
                        try {
                          const skills = JSON.parse(app.resume_extraction?.extracted_skills || '[]');
                          if (Array.isArray(skills) && skills.length > 0) {
                            return skills.slice(0, 6).map((skill: string, idx: number) => (
                              <Badge key={idx} variant="secondary" className="bg-primary/5 text-primary border-primary/10 text-[8px] py-0 px-1 h-4">
                                {skill}
                              </Badge>
                            ));
                          }
                        } catch (e) {}
                        return null;
                      })()}
                    </div>
                    <div className="flex items-center gap-2 text-[11px] font-medium text-muted-foreground line-clamp-1 leading-normal">
                      {app.resume_extraction?.summary || "No summary available."}
                    </div>
                    <div className="flex flex-wrap gap-2 mt-1.5 text-xs text-muted-foreground items-center">
                      <span className="flex items-center gap-1 whitespace-nowrap">
                        <svg
                          className="w-3.5 h-3.5"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
                          />
                        </svg>
                        {new Date(app.applied_at).toLocaleDateString()}
                      </span>
                      {app.resume_extraction && (
                        <span className="text-primary font-medium bg-primary/10 px-2 py-0.5 rounded-sm border border-primary/20 whitespace-nowrap">
                          Job Compatibility:{" "}
                          {Number(app.resume_extraction.resume_score).toFixed(
                            2,
                          )}
                          /10
                        </span>
                      )}
                      {app.interview?.report && (
                        <div className="flex flex-wrap gap-1.5">
                          {app.interview.report.aptitude_score !== null && (
                            <span className="text-purple-600 font-medium bg-purple-100 px-2 py-0.5 rounded-sm border border-purple-200 whitespace-nowrap">
                              Aptitude:{" "}
                              {Number(
                                app.interview.report.aptitude_score,
                              ).toFixed(2)}
                              /10
                            </span>
                          )}
                          {app.interview.report.technical_skills_score !==
                            null && (
                            <span className="text-blue-600 font-medium bg-blue-100 px-2 py-0.5 rounded-sm border border-blue-200 whitespace-nowrap">
                              Tech:{" "}
                              {Number(
                                app.interview.report.technical_skills_score,
                              ).toFixed(2)}
                              /10
                            </span>
                          )}
                          {app.interview.report.behavioral_score !== null && (
                            <span className="text-green-600 font-medium bg-green-100 px-2 py-0.5 rounded-sm border border-green-200 whitespace-nowrap">
                              Behav:{" "}
                              {Number(
                                app.interview.report.behavioral_score,
                              ).toFixed(2)}
                              /10
                            </span>
                          )}
                        </div>
                      )}
                    </div>

                    <div
                      className="flex flex-wrap gap-2 mt-3"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {/* APPROVE: only from applied */}
                      {app.status === "applied" && (
                        <Button
                          size="sm"
                          variant="outline"
                          className="border-primary text-primary hover:bg-slate-600 hover:text-white hover:scale-105 text-[10px] font-black px-4 py-1 h-8 rounded uppercase tracking-wider transition-all duration-300"
                          onClick={(e) => {
                            e.preventDefault();
                            handleTransition(app.id, "approve_for_interview");
                          }}
                        >
                          APPROVE FOR INTERVIEW
                        </Button>
                      )}

                      {/* CALL FOR INTERVIEW: from ai_interview_completed or review_later */}
                      {['ai_interview_completed', 'review_later'].includes(app.status) && (
                        <Button
                          size="sm"
                          variant="outline"
                          className="border-teal-500 text-teal-600 hover:bg-slate-600 hover:text-white hover:scale-105 text-[10px] font-black px-4 py-1 h-8 rounded uppercase tracking-wider transition-all duration-300"
                          onClick={(e) => {
                            e.preventDefault();
                            handleTransition(app.id, "call_for_interview");
                          }}
                        >
                          CALL FOR INTERVIEW
                        </Button>
                      )}

                      {/* REVIEW LATER: from ai_interview_completed */}
                      {app.status === 'ai_interview_completed' && (
                        <Button
                          size="sm"
                          variant="outline"
                          className="border-amber-500 text-amber-600 hover:bg-slate-600 hover:text-white hover:scale-105 text-[10px] font-black px-4 py-1 h-8 rounded uppercase tracking-wider transition-all duration-300"
                          onClick={(e) => {
                            e.preventDefault();
                            handleTransition(app.id, "review_later");
                          }}
                        >
                          REVIEW LATER
                        </Button>
                      )}

                      {/* HIRE: from physical_interview */}
                      {app.status === 'physical_interview' && (
                        <Button
                          size="sm"
                          variant="outline"
                          className="border-emerald-500 text-emerald-600 hover:bg-slate-600 hover:text-white hover:scale-105 text-[10px] font-black px-4 py-1 h-8 rounded uppercase tracking-wider transition-all duration-300"
                          onClick={(e) => {
                            e.preventDefault();
                            handleTransition(app.id, "hire");
                          }}
                        >
                          HIRE
                        </Button>
                      )}

                      {/* REJECT: from any non-terminal state */}
                      {!['hired', 'rejected'].includes(app.status) && (
                        <RejectDialog
                          candidateName={app.candidate_name}
                          onConfirm={(reason, notes) =>
                            handleTransition(app.id, "reject", `Reason: ${reason}${notes ? `\nNotes: ${notes}` : ''}`)
                          }
                          trigger={
                            <Button
                              variant="outline"
                              size="sm"
                              className="border-red-500 text-red-600 hover:bg-slate-600 hover:text-white hover:scale-105 text-[10px] font-black px-4 py-1 h-8 rounded uppercase tracking-wider transition-all duration-300"
                            >
                              REJECT
                            </Button>
                          }
                        />
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex flex-col items-end gap-1.5 shrink-0">
                  <span
                    className={`capsule-badge text-[10px] px-2 py-0.5 ${getStatusColor(app.status)}`}
                  >
                    {app.status.replace(/_/g, " ").toUpperCase()}
                  </span>
                  <span className="text-primary text-xs font-medium group-hover:underline flex items-center gap-1">
                    View Details
                    <svg
                      className="w-3.5 h-3.5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 5l7 7-7 7"
                      />
                    </svg>
                  </span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
