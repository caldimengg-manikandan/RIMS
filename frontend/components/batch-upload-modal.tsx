'use client'

import React, { useState, useRef, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { UploadCloud, CheckCircle2, XCircle, Loader2, AlertCircle, FileText, FolderUp, Trash2 } from 'lucide-react'
import useSWR, { mutate as globalMutate } from 'swr'
import { APIClient } from '@/app/dashboard/lib/api-client'
import { fetcher } from '@/app/dashboard/lib/swr-fetcher'
import * as XLSX from 'xlsx'
import JSZip from 'jszip'

interface Job {
  id: number
  title: string
  status: string
}

interface ProcessedFile {
  id: string
  file: File
  status: 'pending' | 'processing' | 'success' | 'failed' | 'skipped'
  errorMessage?: string
  skippedReason?: string
}

interface BatchUploadModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

const MAX_FILE_SIZE = 5 * 1024 * 1024 // 5MB
const MAX_FILES = 50

const normalizePhone = (rawPhone: string, countryCode?: string | null): string => {
  if (!rawPhone || typeof rawPhone !== 'string') return 'N/A'

  const cleaned = rawPhone.replace(/[\s\-\(\)]/g, '')
  const digitsOnly = cleaned.replace(/\D/g, '')

  // Invalid length
  if (digitsOnly.length < 10) return 'N/A'

  // Already explicitly has country code prefixed
  if (cleaned.startsWith('+')) {
    return '+' + digitsOnly
  }

  const prefix = countryCode ? countryCode.toString().replace(/\D/g, '') : '91'

  // If number already includes the prefix (e.g., 12 digits starting with 91)
  if (digitsOnly.length > 10 && digitsOnly.startsWith(prefix)) {
    return '+' + digitsOnly
  }

  // Exact 10 digits -> append prefix
  if (digitsOnly.length === 10) {
    return '+' + prefix + digitsOnly
  }

  // Any other standalone length without a '+'
  return '+' + digitsOnly
}

export function BatchUploadModal({ isOpen, onClose, onSuccess }: BatchUploadModalProps) {
  const [selectedJobId, setSelectedJobId] = useState<string>('')
  const [files, setFiles] = useState<ProcessedFile[]>([])
  const [isProcessing, setIsProcessing] = useState(false)
  
  // Stats
  const [stats, setStats] = useState({ success: 0, failed: 0, skipped: 0, total: 0, applicationIds: [] as number[], jobRole: '' })
  const [showSummary, setShowSummary] = useState(false)
  
  const [isExportReady, setIsExportReady] = useState(false)
  const [finalBatchData, setFinalBatchData] = useState<any[]>([])
  const [pollingStatus, setPollingStatus] = useState<string>('')
  
  const fileInputRef = useRef<HTMLInputElement>(null)
  const folderInputRef = useRef<HTMLInputElement>(null)
  const isCancelling = useRef(false)

  const { data: jobs, isLoading: jobsLoading } = useSWR<Job[]>('/api/jobs', (url: string) => fetcher<Job[]>(url))

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setSelectedJobId('')
      setFiles([])
      setIsProcessing(false)
      setStats({ success: 0, failed: 0, skipped: 0, total: 0, applicationIds: [], jobRole: '' })
      setShowSummary(false)
      setIsExportReady(false)
      setFinalBatchData([])
      setPollingStatus('')
      isCancelling.current = false
    }
  }, [isOpen])

  // Polling logic for background processing completion
  useEffect(() => {
    let interval: NodeJS.Timeout
    const checkCompletion = async () => {
      // We only poll if there are successfully submitted applications and we're showing the summary
      if (!showSummary || stats.applicationIds.length === 0 || isExportReady) return
      
      try {
        const resp = await APIClient.get<any>(`/api/applications?job_id=${selectedJobId}&limit=100&t=${Date.now()}`)
        // Handle both direct array and normalized { items, total } responses
        const apps = Array.isArray(resp) ? resp : (resp?.items || [])
        
        // Filter out applications for this batch
        const batchApps = apps.filter((a: any) => stats.applicationIds.includes(a.id))
        
        // Processing is complete if we have extraction OR it explicitly failed
        const completedCount = batchApps.filter((a: any) => 
          a.resume_extraction !== null || 
          (a.hr_notes && a.hr_notes.includes('AI analysis failed'))
        ).length

        setPollingStatus(`Finalizing data: ${completedCount}/${stats.applicationIds.length} candidates ready...`)

        // Only complete when ALL submitted applications are present and finished
        if (batchApps.length === stats.applicationIds.length && completedCount === stats.applicationIds.length) {
          setIsExportReady(true)
          setFinalBatchData(batchApps)
        }
      } catch (err) {
        console.error("Error polling applications state:", err)
      }
    }

    if (showSummary && !isExportReady && stats.applicationIds.length > 0) {
      // Check immediately
      checkCompletion()
      // Then poll every 3 seconds
      interval = setInterval(checkCompletion, 3000)
    }
    
    return () => clearInterval(interval)
  }, [showSummary, isExportReady, selectedJobId, stats.applicationIds])

  const processIncomingFiles = async (selectedFiles: File[]) => {
    const newProcessedFiles: ProcessedFile[] = []
    
    // We need to compare against both existing files and files added in this batch
    const allFilesSoFar = [...files]

    const addFileWithValidation = (f: File) => {
      // Rule 1: Allow only pdf/doc/docx
      const lowerName = f.name.toLowerCase()
      if (!lowerName.endsWith('.pdf') && !lowerName.endsWith('.doc') && !lowerName.endsWith('.docx')) {
        return // Ignore silently as per requirements
      }

      const id = `${f.name}-${f.size}-${Math.random()}`
      let status: ProcessedFile['status'] = 'pending'
      let skippedReason = ''

      // Rule 2: Max File Size
      if (f.size > MAX_FILE_SIZE) {
        status = 'skipped'
        skippedReason = 'Over 5MB limit'
      }

      // Rule 3: Duplicate detection (name + size)
      const isDuplicate = allFilesSoFar.some(
        existing => existing.file.name === f.name && existing.file.size === f.size
      )
      
      if (isDuplicate) {
        status = 'skipped'
        skippedReason = 'Duplicate attached'
      }

      const pFile = { id, file: f, status, skippedReason }
      newProcessedFiles.push(pFile)
      allFilesSoFar.push(pFile)
    }

    for (const file of selectedFiles) {
      if (file.name.toLowerCase().endsWith('.zip')) {
        try {
          const zip = await JSZip.loadAsync(file)
          for (const [relativePath, zipEntry] of Object.entries(zip.files)) {
            if (!zipEntry.dir) {
              const lowerName = zipEntry.name.toLowerCase()
              if (lowerName.endsWith('.pdf') || lowerName.endsWith('.doc') || lowerName.endsWith('.docx')) {
                const blob = await zipEntry.async('blob')
                const extractedFile = new File([blob], zipEntry.name.split('/').pop() || 'resume', {
                  type: lowerName.endsWith('.pdf') ? 'application/pdf' : 'application/docx'
                })
                addFileWithValidation(extractedFile)
              }
            }
          }
        } catch (err) {
          console.error('Failed to extract ZIP:', err)
        }
      } else {
        addFileWithValidation(file)
      }
    }

    // Rule 4: Total files cap (max 50)
    // We apply this by checking total active files vs the limit
    setFiles((prev) => {
      const combined = [...prev, ...newProcessedFiles]
      // Enforce max 50: Mark anything beyond 50 as skipped
      return combined.map((f, idx) => {
        if (idx >= MAX_FILES && f.status === 'pending') {
          return { ...f, status: 'skipped', skippedReason: '50 files limit exceeded' }
        }
        return f
      })
    })

    if (fileInputRef.current) fileInputRef.current.value = ''
    if (folderInputRef.current) folderInputRef.current.value = ''
  }

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return
    const selectedFiles = Array.from(e.target.files)
    await processIncomingFiles(selectedFiles)
  }

  const removeFile = (id: string) => {
    setFiles(prev => prev.filter((f) => f.id !== id))
  }

  const handleProcess = async () => {
    if (!selectedJobId || files.length === 0) return

    setIsProcessing(true)
    setShowSummary(false)
    isCancelling.current = false
    
    // Reset statuses of previously failed/skipped-by-network files (if any)
    setFiles(prev => prev.map(f => f.status === 'failed' ? {...f, status: 'pending', errorMessage: ''} : f))

    let successCount = 0
    let failedCount = 0
    const successfulAppIds: number[] = []
    
    const selectedJob = jobs?.find(j => j.id.toString() === selectedJobId)
    const jobRole = selectedJob?.title || 'Unknown Role'

    // The working queue is only pending files
    const queue = files.filter(f => f.status === 'pending')
    const initialSkippedCount = files.filter(f => f.status === 'skipped').length

    setStats({ 
        success: 0, 
        failed: 0, 
        skipped: initialSkippedCount, 
        total: queue.length + initialSkippedCount,
        applicationIds: [],
        jobRole
    })

    const worker = async () => {
      while (queue.length > 0) {
        if (isCancelling.current) break

        const currentItem = queue.shift()
        if (!currentItem) continue

        // Mark as processing
        setFiles(prev => prev.map(f => f.id === currentItem.id ? { ...f, status: 'processing' } : f))

        try {
          const formData = new FormData()
          formData.append('job_id', selectedJobId)
          
          const baseName = currentItem.file.name.split('.')[0]
          const cleanName = baseName.replace(/[-_]/g, ' ') || 'Unknown Candidate'
          const timestamp = Date.now()
          const randomStr = Math.random().toString(36).substring(7)
          const uniqueEmail = `batch.${cleanName.replace(/[^a-zA-Z0-9]/g, '')}_${timestamp}_${randomStr}@batch.example.com`.toLowerCase()

          formData.append('candidate_name', cleanName)
          formData.append('candidate_email', uniqueEmail)
          formData.append('resume_file', currentItem.file)

          const responseData = await APIClient.postFormData('/api/applications/apply', formData)
          
          const appId = responseData.id || responseData.application?.id
          if (appId) {
            successfulAppIds.push(appId)
          }
          successCount++
          
          setFiles(prev => prev.map(f => f.id === currentItem.id ? { ...f, status: 'success' } : f))
        } catch (error: any) {
          console.error(`Failed to process ${currentItem.file.name}:`, error)
          failedCount++
          setFiles(prev => prev.map(f => f.id === currentItem.id ? { ...f, status: 'failed', errorMessage: error.message || 'API Error' } : f))
        }

        // Live stats update
        setStats(prev => ({ ...prev, success: successCount, failed: failedCount, applicationIds: successfulAppIds }))
      }
    }

    // Launch Concurrency Pool (max 3 workers)
    const CONCURRENCY = 3
    const workers = Array(Math.min(CONCURRENCY, queue.length)).fill(null).map(() => worker())
    await Promise.all(workers)

    setIsProcessing(false)
    setShowSummary(true)
  }

  const handleCancel = () => {
    isCancelling.current = true
  }

  const handleExport = async () => {
    if (!showSummary || finalBatchData.length === 0) return

    const uniqueAppsMap = new Map()
    
    finalBatchData.forEach(app => {
      // EXACT 1:1 match with Applications state
      const name = app.candidate_name || 'Unknown'
      const email = app.candidate_email || 'N/A'
      
      const rawPhone = app.candidate_phone || ''
      const extCountryCode = app.country_code || null
      const phone = normalizePhone(rawPhone, extCountryCode)
      
      const role = app.job?.title || stats.jobRole || 'Unknown Role'
      
      const rawScore = app.job_compatibility_score ?? app.resume_score ?? app.resume_extraction?.match_percentage ?? app.resume_extraction?.skill_match_percentage ?? 0
      const pctScore = rawScore <= 10 && rawScore > 0 ? rawScore * 10 : rawScore
      const matchStatus = pctScore >= 50 ? "YES" : "NO"
      
      const key = email !== 'N/A' ? email : `${name}-${Math.random()}`
      if (!uniqueAppsMap.has(key)) {
          uniqueAppsMap.set(key, { 
            Name: name, 
            Email: email, 
            'Phone Number': phone, 
            'Job Role': role,
            'MATCH': matchStatus
          })
      }
    })
    
    const uniqueApps = Array.from(uniqueAppsMap.values())
    
    const worksheet = XLSX.utils.json_to_sheet(uniqueApps)
    const workbook = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(workbook, worksheet, "Candidates")
    
    XLSX.writeFile(workbook, "candidates_export.xlsx")
  }

  const handleClose = () => {
    if (isProcessing) return // Prevent closing while processing (they must hit cancel first)
    if (showSummary) {
      // Invalidate applications and dashboard analytics
      globalMutate('/api/applications')
      globalMutate('/api/analytics/dashboard')
      onSuccess()
    }
    onClose()
  }

  const progressCount = stats.success + stats.failed + files.filter(f => f.status === 'processing').length
  const processingQueueTotal = files.filter(f => ['pending', 'processing', 'success', 'failed'].includes(f.status)).length

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] flex flex-col overflow-hidden">
        <DialogHeader>
          <DialogTitle>Batch Resume Analysis</DialogTitle>
          <DialogDescription>
            Upload multiple resumes or a folder. They will be actively filtered and processed securely.
          </DialogDescription>
        </DialogHeader>

        {isProcessing ? (
          <div className="py-8 flex flex-col items-center justify-center space-y-6 flex-1">
            <Loader2 className="h-12 w-12 text-primary animate-spin" />
            <div className="text-center space-y-2 w-full max-w-sm">
              <h3 className="text-lg font-semibold">Processing resumes... ⏳</h3>
              <p className="text-muted-foreground">
                Processing {Math.min(progressCount + 1, processingQueueTotal)} of {processingQueueTotal} resumes
              </p>
              <div className="w-full bg-secondary rounded-full h-2 mt-4 mx-auto overflow-hidden">
                <div 
                  className="bg-primary h-full transition-all duration-300"
                  style={{ width: `${(progressCount / processingQueueTotal) * 100}%` }}
                />
              </div>
              <div className="flex justify-between text-xs text-muted-foreground mt-2">
                <span className="text-emerald-500">{stats.success} Success</span>
                <span className="text-destructive">{stats.failed} Failed</span>
              </div>
            </div>
            <Button variant="destructive" onClick={handleCancel} className="mt-4">
               Cancel Remaining
            </Button>
          </div>
        ) : showSummary ? (
          <div className="py-6 flex flex-col items-center justify-center space-y-4 flex-1">
            <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center">
              <CheckCircle2 className="h-8 w-8 text-primary" />
            </div>
            <div className="text-center space-y-2">
              <h3 className="text-xl font-bold">Processing Finalized</h3>
              <div className="flex items-center justify-center gap-4 text-sm mt-2 flex-wrap">
                <span className="flex items-center gap-1 text-emerald-600 font-medium">
                  <CheckCircle2 className="w-4 h-4" /> {stats.success} Successful
                </span>
                {stats.failed > 0 && (
                  <span className="flex items-center gap-1 text-destructive font-medium">
                    <XCircle className="w-4 h-4" /> {stats.failed} Failed
                  </span>
                )}
                {stats.skipped > 0 && (
                  <span className="flex items-center gap-1 text-muted-foreground font-medium">
                    <AlertCircle className="w-4 h-4" /> {stats.skipped} Skipped
                  </span>
                )}
              </div>
              
              {!isExportReady && stats.success > 0 && (
                <p className="text-xs text-muted-foreground flex items-center justify-center gap-2 mt-4">
                  <Loader2 className="h-3 w-3 animate-spin"/>
                  {pollingStatus || 'Preparing final export data...'}
                </p>
              )}
            </div>
            
            <div className="w-full max-w-lg mt-6 bg-muted/30 p-4 rounded-xl max-h-48 overflow-y-auto">
                <h4 className="text-sm font-semibold mb-2">Detailed Results</h4>
                {files.filter(f => f.status !== 'pending').map(file => (
                    <div key={file.id} className="flex justify-between items-center py-1.5 text-xs border-b last:border-0 border-border/50 gap-4">
                        <span className="truncate max-w-[200px] sm:max-w-xs">{file.file.name}</span>
                        {file.status === 'success' && <span className="text-emerald-500 whitespace-nowrap shrink-0">Success</span>}
                        {file.status === 'failed' && <span className="text-destructive whitespace-nowrap shrink-0">Failed ({file.errorMessage})</span>}
                        {file.status === 'skipped' && <span className="text-muted-foreground whitespace-nowrap shrink-0">Skipped ({file.skippedReason})</span>}
                    </div>
                ))}
            </div>

            <div className="flex flex-col w-full sm:flex-row gap-3 mt-4 pt-4">
              <Button onClick={handleClose} className="flex-1">
                View Applications
              </Button>
              {stats.success > 0 && (
                <Button 
                  variant="outline" 
                  onClick={handleExport} 
                  disabled={!isExportReady}
                  className="flex-1 border-primary text-primary hover:bg-primary/5"
                >
                  {isExportReady ? 'Download Candidate Data (Excel)' : 'Preparing Data...'}
                </Button>
              )}
            </div>
          </div>
        ) : (
          <div className="space-y-6 py-4 flex-1 overflow-y-auto pr-2">
            <div className="space-y-2">
              <Label htmlFor="job-select">Target Job Role</Label>
              <Select value={selectedJobId} onValueChange={setSelectedJobId} disabled={jobsLoading}>
                <SelectTrigger id="job-select">
                  <SelectValue placeholder={jobsLoading ? "Loading jobs..." : "Select a job for these resumes"} />
                </SelectTrigger>
                <SelectContent>
                  {jobs?.filter(j => j.status === 'open').map((job) => (
                    <SelectItem key={job.id} value={job.id.toString()}>
                      {job.title}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Upload Resumes</Label>
              <div className="grid grid-cols-2 gap-4">
                  <div 
                    className="border-2 border-dashed border-border rounded-xl p-6 hover:bg-muted/50 transition-colors cursor-pointer text-center flex flex-col items-center justify-center"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <input
                      type="file"
                      multiple
                      accept=".pdf,.doc,.docx,.zip"
                      className="hidden"
                      ref={fileInputRef}
                      onChange={handleFileChange}
                    />
                    <div className="w-10 h-10 bg-primary/10 text-primary rounded-full flex items-center justify-center mb-2 mx-auto">
                      <UploadCloud className="h-5 w-5" />
                    </div>
                    <h4 className="font-medium text-sm text-foreground">Select Files / ZIP</h4>
                  </div>

                  <div 
                    className="border-2 border-dashed border-border rounded-xl p-6 hover:bg-muted/50 transition-colors cursor-pointer text-center flex flex-col items-center justify-center"
                    onClick={() => folderInputRef.current?.click()}
                  >
                    <input
                      type="file"
                      multiple
                      // @ts-ignore
                      webkitdirectory=""
                      directory=""
                      className="hidden"
                      ref={folderInputRef}
                      onChange={handleFileChange}
                    />
                    <div className="w-10 h-10 bg-primary/10 text-primary rounded-full flex items-center justify-center mb-2 mx-auto">
                      <FolderUp className="h-5 w-5" />
                    </div>
                    <h4 className="font-medium text-sm text-foreground">Select Folder</h4>
                  </div>
              </div>
            </div>

            {files.length > 0 && (
              <div className="space-y-2 border-t pt-4">
                <div className="flex items-center justify-between">
                  <Label>
                    Selected Files ({files.filter(f => f.status === 'pending').length} ready, {files.filter(f => f.status === 'skipped').length} skipped)
                  </Label>
                  <Button variant="ghost" size="sm" onClick={() => setFiles([])} className="h-auto p-0 text-muted-foreground hover:text-destructive text-xs">
                    Clear all
                  </Button>
                </div>
                
                {files.filter(f => f.status === 'pending').length === 0 && (
                   <div className="p-3 bg-destructive/10 text-destructive text-sm rounded-lg flex items-center gap-2">
                       <AlertCircle className="h-4 w-4 shrink-0" />
                       No valid resumes ready. Try clearing and selecting valid files.
                   </div>
                )}
                
                <div className="max-h-48 overflow-y-auto space-y-2 pr-2">
                  {files.map((fileObj) => (
                    <div key={fileObj.id} className={`flex items-center justify-between p-2 rounded-lg text-sm border ${fileObj.status === 'skipped' ? 'bg-muted/30 opacity-60' : 'bg-background'}`}>
                      <div className="flex items-center gap-2 overflow-hidden flex-1">
                        <FileText className={`h-4 w-4 shrink-0 ${fileObj.status === 'skipped' ? 'text-muted-foreground' : 'text-primary'}`} />
                        <div className="flex flex-col truncate flex-1">
                             <span className="truncate">{fileObj.file.name}</span>
                             {fileObj.status === 'skipped' && (
                                 <span className="text-[10px] text-destructive">Skipped: {fileObj.skippedReason}</span>
                             )}
                        </div>
                      </div>
                      <Button variant="ghost" size="icon" onClick={() => removeFile(fileObj.id)} className="h-6 w-6 text-muted-foreground hover:text-destructive shrink-0">
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {!isProcessing && !showSummary && (
          <DialogFooter className="mt-2 pt-4 border-t">
            <Button variant="outline" onClick={handleClose}>Cancel</Button>
            <Button 
              onClick={handleProcess} 
              disabled={!selectedJobId || files.filter(f => f.status === 'pending').length === 0}
              className="gap-2"
            >
              Start Analysis ({files.filter(f => f.status === 'pending').length})
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  )
}
