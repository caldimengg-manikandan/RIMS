"use client";

import React, { useEffect, useState, useCallback, useMemo } from "react";
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
import { HireDialog } from "@/components/hire-dialog";
import useSWR from "swr";
import { fetcher } from "@/app/dashboard/lib/swr-fetcher";
import { performMutation } from "@/app/dashboard/lib/swr-utils";
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
  candidate_photo_path: string | null;
  composite_score: number | null;
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

// Backend caps `limit` to <50 for performance.
const APPLICATIONS_PAGE_SIZE = 49;

export default function HRApplicationsPage() {
  const router = useRouter();
  const [applicationsPage, setApplicationsPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState("");
  /** Server-side search; debounced to avoid refetching on every keystroke. */
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [isMagicSearch, setIsMagicSearch] = useState(false);
  const [magicSearchResults, setMagicSearchResults] = useState<Application[] | null>(null);
  const [isMagicLoading, setIsMagicLoading] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(searchTerm.trim()), 400);
    return () => clearTimeout(t);
  }, [searchTerm]);

  const handleMagicSearch = useCallback(async () => {
    if (!searchTerm.trim()) return;
    setIsMagicLoading(true);
    try {
      const resp = await APIClient.post<{candidates: any[]}>(
        "/api/search/candidates", 
        { query: searchTerm }
      );
      // Map basic candidate results to Application interface for table compatibility
      const mappedResults = resp.candidates.map(c => ({
        id: c.id,
        candidate_name: c.candidate_name,
        status: c.current_status,
        applied_at: new Date().toISOString(), // Mock if missing, usually search returns list
        job: { title: c.job_title, id: 0, job_id: "" },
        resume_extraction: { 
            resume_score: c.resume_score, 
            summary: c.match_insight,
            extracted_skills: c.skills
        }
      })) as Application[];
      setMagicSearchResults(mappedResults);
      setIsMagicSearch(true);
    } catch (err) {
      console.error("Magic Search Error:", err);
      alert("Magic Search failed. Falling back to keyword search.");
    } finally {
      setIsMagicLoading(false);
    }
  }, [searchTerm]);

  const applicationsListUrl = useMemo(() => {
    if (isMagicSearch) return null; // Don't fetch via SWR if magic search is active
    const q = new URLSearchParams();
    q.set("limit", String(APPLICATIONS_PAGE_SIZE));
    q.set("skip", String((applicationsPage - 1) * APPLICATIONS_PAGE_SIZE));
    if (statusFilter !== "all") q.set("status", statusFilter);
    if (dateFrom) q.set("from_date", dateFrom);
    if (dateTo) q.set("to_date", dateTo);
    if (debouncedSearch) q.set("search", debouncedSearch);
    return `/api/applications?${q.toString()}`;
  }, [applicationsPage, statusFilter, dateFrom, dateTo, debouncedSearch, isMagicSearch]);

  useEffect(() => {
    setApplicationsPage(1);
    // Auto-disable magic search if the user clears the search term or changes filters
    if (!searchTerm && isMagicSearch) {
        setIsMagicSearch(false);
        setMagicSearchResults(null);
    }
  }, [statusFilter, dateFrom, dateTo, debouncedSearch, searchTerm]);

  const {
    data: paginatedData,
    error,
    isLoading: isSwrLoading,
    mutate,
  } = useSWR<{ items: Application[]; total: number; pages: number }>(
    applicationsListUrl,
    (url: string) => fetcher<{ items: Application[]; total: number; pages: number }>(url),
    { keepPreviousData: true },
  );

  const swrApplications = paginatedData?.items || [];
  const applications = isMagicSearch && magicSearchResults ? magicSearchResults : swrApplications;
  const isLoading = isSwrLoading || isMagicLoading;

  const handleDecision = useCallback(async (
    applicationId: number,
    decision: "hired" | "rejected",
    reason?: string,
    notes?: string,
  ) => {
    const actionFn = () => {
      let userComments = `Candidate ${decision} via quick action in applications list.`;
      if (decision === "rejected") {
        userComments = `Reason: ${reason}${notes ? `\nNotes: ${notes}` : ""}`;
      }
      return APIClient.put(
        `/api/decisions/applications/${applicationId}/decide`,
        {
          decision,
          decision_comments: userComments,
        },
      );
    };

    await performMutation<Application[]>(
      applicationsListUrl,
      mutate,
      actionFn,
      {
        lockKey: `application-${applicationId}`,
        optimisticData: (current: any) => {
          if (!current) return current;
          const items = current.items || (Array.isArray(current) ? current : []);
          const mapped = items.map((app: any) =>
            app.id === applicationId ? { ...app, status: decision } : app
          );
          return Array.isArray(current) ? mapped : { ...current, items: mapped };
        },
        successMessage: `Candidate ${decision} successfully`,
        invalidateKeys: ["/api/analytics/dashboard"]
      }
    );
  }, [mutate, applicationsListUrl]);

  const handleTransition = useCallback(async (
    applicationId: number,
    action: string,
    notes?: string,
  ) => {
    let nextStatus = "applied";
    if (action === "approve_for_interview") nextStatus = "ai_interview";
    else if (action === "reject") nextStatus = "rejected";
    else if (action === "call_for_interview") nextStatus = "physical_interview";
    else if (action === "review_later") nextStatus = "review_later";
    else if (action === "hire") nextStatus = "hired";

    const actionFn = () => APIClient.put(`/api/applications/${applicationId}/status`, {
      action,
      hr_notes: notes || `Action: ${action}`,
    });

    await performMutation<Application[]>(
      applicationsListUrl,
      mutate,
      actionFn,
      {
        lockKey: `application-${applicationId}`,
        optimisticData: (current: any) => {
          if (!current) return current;
          const items = current.items || (Array.isArray(current) ? current : []);
          const mapped = items.map((app: any) =>
            app.id === applicationId ? { ...app, status: nextStatus } : app
          );
          return Array.isArray(current) ? mapped : { ...current, items: mapped };
        },
        invalidateKeys: ["/api/analytics/dashboard"]
      }
    );
  }, [mutate, applicationsListUrl]);

  const handleHire = useCallback(async (
    applicationId: number,
    joiningDate: string,
    offerLetter: File,
    notes: string,
  ) => {
    const actionFn = () => {
      const formData = new FormData();
      formData.append("joining_date", joiningDate);
      formData.append("notes", notes || `Action: hire`);
      formData.append("offer_letter", offerLetter);
      return APIClient.postFormData(`/api/decisions/applications/${applicationId}/hire`, formData);
    };

    await performMutation<Application[]>(
      applicationsListUrl,
      mutate,
      actionFn,
      {
        lockKey: `application-${applicationId}`,
        optimisticData: (current: any) => {
          if (!current) return current;
          const items = current.items || (Array.isArray(current) ? current : []);
          const mapped = items.map((app: any) =>
            app.id === applicationId ? { ...app, status: "hired" } : app
          );
          return Array.isArray(current) ? mapped : { ...current, items: mapped };
        },
        successMessage: "Candidate hired successfully",
        invalidateKeys: ["/api/analytics/dashboard"]
      }
    );
  }, [mutate, applicationsListUrl]);

  // Get unique job titles for the filter dropdown
  const jobTitles = useMemo(() => Array.from(
    new Set(applications.map((app) => app.job.title)),
  ).sort(), [applications]);

  const hasMoreApplications = paginatedData ? applicationsPage < paginatedData.pages : false;

  const getStatusColor = (status: string) => {
    switch (status) {
      case "applied":
        return "capsule-badge-primary";
      case "screened":
        return "bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border-indigo-500/20";
      case "interview_scheduled":
        return "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20";
      case "interview_completed":
        return "capsule-badge-info";
      case "review_later":
        return "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20";
      case "physical_interview":
        return "bg-teal-500/10 text-teal-600 dark:text-teal-400 border-teal-500/20";
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
          <div className="flex-1 min-w-0">
            <div className="relative group flex gap-2">
              <div className="relative flex-1">
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
                    placeholder="Search name, email, ID, or job details..."
                    className="w-full pl-12 pr-4 h-11 bg-background border-2 border-input rounded-xl focus:outline-none focus:ring-4 focus:ring-primary/5 focus:border-primary transition-all text-base placeholder:text-muted-foreground text-foreground"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleMagicSearch()}
                />
              </div>
              <Button 
                onClick={handleMagicSearch}
                disabled={!searchTerm.trim() || isMagicLoading}
                className={`h-11 px-6 rounded-xl font-bold transition-all shadow-sm ${isMagicSearch ? 'bg-primary text-primary-foreground scale-105' : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'}`}
              >
                {isMagicLoading ? (
                    <div className="animate-spin h-4 w-4 border-2 border-current border-t-transparent rounded-full" />
                ) : (
                    <>
                        <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M12 2L14.5 9H22L16 13.5L18.5 20.5L12 16L5.5 20.5L8 13.5L2 9H9.5L12 2Z" />
                        </svg>
                        Magic Search
                    </>
                )}
              </Button>
            </div>
          </div>

          {/* Date From Filter */}
          <div className="w-full sm:w-[170px]">
            <label className="block text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-1 shadow-sm px-1">From Date</label>
            <input
              type="date"
              min="2020-01-01"
              max={dateTo || new Date().toLocaleDateString('en-CA')}
              className="w-full px-3 h-11 bg-background border-2 border-input rounded-xl text-sm font-medium focus:outline-none focus:ring-4 focus:ring-primary/5 focus:border-primary transition-all text-foreground cursor-pointer"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
            />
          </div>

          {/* Date To Filter */}
          <div className="w-full sm:w-[170px]">
            <label className="block text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-1 shadow-sm px-1">To Date</label>
            <input
              type="date"
              min={dateFrom || "2020-01-01"}
              max={new Date().toLocaleDateString('en-CA')}
              className="w-full px-3 h-11 bg-background border-2 border-input rounded-xl text-sm font-medium focus:outline-none focus:ring-4 focus:ring-primary/5 focus:border-primary transition-all text-foreground cursor-pointer"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
            />
          </div>

          {/* Status Filter */}
          <div className="w-[200px]">
            <label className="block text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-1 shadow-sm px-1">Current Status</label>
            <select
              className="w-full px-4 h-11 bg-background border-2 border-input rounded-xl text-base font-medium focus:outline-none focus:ring-4 focus:ring-primary/5 focus:border-primary transition-all text-foreground cursor-pointer"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="all">All Statuses</option>
              <option value="applied">Applied</option>
              <option value="screened">Screened</option>
              <option value="interview_scheduled">Interview Scheduled</option>
              <option value="interview_completed">Interview Completed</option>
              <option value="review_later">Review Later</option>
              <option value="physical_interview">Physical Interview</option>
              <option value="hired">Hired</option>
              <option value="rejected">Rejected</option>
            </select>
          </div>

          {/* Clear Filters */}
          {(searchTerm || dateFrom || dateTo || statusFilter !== "all" || isMagicSearch) && (
            <Button 
                variant="ghost" 
                size="sm"
                onClick={() => {
                    setSearchTerm("");
                    setDateFrom("");
                    setDateTo("");
                    setStatusFilter("all");
                    setIsMagicSearch(false);
                    setMagicSearchResults(null);
                    setApplicationsPage(1);
                }}
                className="h-11 px-4 text-muted-foreground hover:text-foreground transition-colors"
            >
                Clear All
            </Button>
          )}
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
        </div>
      ) : applications.length === 0 ? (
        <div className="text-center py-16 bg-card rounded-xl border border-border">
          <p className="text-muted-foreground">
            No applications match your filtering criteria.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {applications.map((app, index) => (
            <Card
              key={app.id}
              onClick={() =>
                router.push(`/dashboard/hr/applications/${app.id}`)
              }
              style={{ animationDelay: `${index * 50}ms` }}
              className="hover:shadow-md transition-all duration-300 bg-card border border-border hover:border-border/80 cursor-pointer group animate-in fade-in slide-in-from-bottom-4 duration-500 ease-out fill-mode-both"
            >
              <CardContent className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="flex items-center gap-4 flex-1">
                  <div className="relative shrink-0">
                    <div className="h-14 w-14 rounded-full overflow-hidden border-2 border-border/50 bg-muted flex items-center justify-center shadow-sm">
                      {app.candidate_photo_path ? (
                        <img
                          src={`${API_BASE_URL}/${app.candidate_photo_path.replace(/\\/g, "/")}`}
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
                      {(app.composite_score! > 0 || app.resume_extraction) && (
                        <span className="text-primary font-medium bg-primary/10 px-2 py-0.5 rounded-sm border border-primary/20 whitespace-nowrap">
                          Score:{" "}
                          {(app.composite_score! > 0 
                            ? Number(app.composite_score) 
                            : Number(app.resume_extraction?.resume_score || 0)
                          ).toFixed(1)}
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
                        <HireDialog 
                          candidateName={app.candidate_name}
                          onConfirm={(date, file, notes) => handleHire(app.id, date, file, notes)}
                          trigger={
                            <Button
                              size="sm"
                              variant="outline"
                              className="border-emerald-500 text-emerald-600 hover:bg-slate-600 hover:text-white hover:scale-105 text-[10px] font-black px-4 py-1 h-8 rounded uppercase tracking-wider transition-all duration-300"
                            >
                              HIRE
                            </Button>
                          }
                        />
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
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-border">
            <p className="text-sm text-muted-foreground">
              Page {applicationsPage}
              {hasMoreApplications ? " · Up to " + APPLICATIONS_PAGE_SIZE + " per page" : ""}
            </p>
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={applicationsPage <= 1 || isLoading}
                onClick={() => setApplicationsPage((p) => Math.max(1, p - 1))}
              >
                Previous
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={!hasMoreApplications || isLoading}
                onClick={() => setApplicationsPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
