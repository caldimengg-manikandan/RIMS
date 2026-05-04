'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
    DialogDescription,
} from '@/components/ui/dialog'
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { APIClient } from '@/app/dashboard/lib/api-client'
import { toast } from 'sonner'
import {
    Database,
    Plus,
    Pencil,
    Trash2,
    Loader2,
    X,
    BookOpen,
    Tag,
    Users,
    HelpCircle,
    FileSpreadsheet,
} from 'lucide-react'
import * as XLSX from 'xlsx'
import { useAuth } from '@/app/dashboard/lib/auth-context'
import { useRouter } from 'next/navigation'

// ── Types ─────────────────────────────────────────────────────────────────────

interface QuestionRow {
    question: string
    answer_key: string
}

interface QuestionSet {
    id: number
    title: string
    round_type: 'aptitude' | 'technical' | 'behavioural'
    job_roles: string[]
    question_count: number
    topic_tags: string[]
}

interface QuestionSetDetail extends QuestionSet {
    questions: QuestionRow[]
}

const ROUND_TYPE_OPTIONS = [
    { value: 'aptitude', label: 'Aptitude' },
    { value: 'technical', label: 'Technical' },
    { value: 'behavioural', label: 'Behavioural' },
] as const

const ROUND_TYPE_COLORS: Record<string, string> = {
    aptitude: 'bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30',
    technical: 'bg-blue-500/15 text-blue-600 dark:text-blue-400 border-blue-500/30',
    behavioural: 'bg-purple-500/15 text-purple-600 dark:text-purple-400 border-purple-500/30',
}

// ── Tag input helper ──────────────────────────────────────────────────────────

function TagInput({
    value,
    onChange,
    placeholder,
}: {
    value: string[]
    onChange: (tags: string[]) => void
    placeholder?: string
}) {
    const [input, setInput] = useState('')

    const addTag = (raw: string) => {
        const parts = raw.split(',').map(t => t.trim()).filter(Boolean)
        const next = Array.from(new Set([...value, ...parts]))
        onChange(next)
        setInput('')
    }

    const removeTag = (idx: number) => {
        onChange(value.filter((_, i) => i !== idx))
    }

    return (
        <div className="space-y-2">
            <div className="flex flex-wrap gap-1.5 min-h-[32px]">
                {value.map((tag, i) => (
                    <span
                        key={i}
                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-primary/10 text-primary border border-primary/20"
                    >
                        {tag}
                        <button
                            type="button"
                            onClick={() => removeTag(i)}
                            className="hover:text-destructive transition-colors"
                        >
                            <X className="h-3 w-3" />
                        </button>
                    </span>
                ))}
            </div>
            <Input
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => {
                    if (e.key === 'Enter' || e.key === ',') {
                        e.preventDefault()
                        if (input.trim()) addTag(input)
                    }
                }}
                onBlur={() => { if (input.trim()) addTag(input) }}
                placeholder={placeholder ?? 'Type and press Enter or comma to add'}
                className="h-9 text-sm"
            />
        </div>
    )
}

// ── Empty state ───────────────────────────────────────────────────────────────

function EmptyState({ onAdd }: { onAdd: () => void }) {
    return (
        <div className="flex flex-col items-center justify-center py-24 gap-5 text-center">
            <div className="w-20 h-20 rounded-full bg-muted/50 flex items-center justify-center border border-border">
                <Database className="h-9 w-9 text-muted-foreground/50" />
            </div>
            <div className="space-y-1">
                <h3 className="text-lg font-semibold text-foreground">No question sets yet</h3>
                <p className="text-sm text-muted-foreground max-w-xs">
                    Create reusable question sets for aptitude, technical, and behavioural rounds.
                    They'll be available to pick when creating a job.
                </p>
            </div>
            <Button onClick={onAdd} className="gap-2">
                <Plus className="h-4 w-4" /> Create First Set
            </Button>
        </div>
    )
}

// ── Set card ──────────────────────────────────────────────────────────────────

function SetCard({
    set,
    onEdit,
    onDelete,
}: {
    set: QuestionSet
    onEdit: (s: QuestionSet) => void
    onDelete: (s: QuestionSet) => void
}) {
    return (
        <Card className="border border-border bg-card hover:border-primary/30 transition-all duration-200 group">
            <CardContent className="p-5 space-y-3">
                {/* Header row */}
                <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                        <h3 className="font-semibold text-foreground text-sm leading-snug truncate">
                            {set.title}
                        </h3>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 text-muted-foreground hover:text-primary hover:bg-primary/10 opacity-0 group-hover:opacity-100 transition-all"
                            onClick={() => onEdit(set)}
                        >
                            <Pencil className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 text-muted-foreground hover:text-destructive hover:bg-destructive/10 opacity-0 group-hover:opacity-100 transition-all"
                            onClick={() => onDelete(set)}
                        >
                            <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                    </div>
                </div>

                {/* Round type badge + question count */}
                <div className="flex items-center gap-2 flex-wrap">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold border ${ROUND_TYPE_COLORS[set.round_type] ?? 'bg-muted text-muted-foreground border-border'}`}>
                        {set.round_type.charAt(0).toUpperCase() + set.round_type.slice(1)}
                    </span>
                    <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                        <HelpCircle className="h-3 w-3" />
                        {set.question_count} question{set.question_count !== 1 ? 's' : ''}
                    </span>
                </div>

                {/* Job roles */}
                {set.job_roles.length > 0 && (
                    <div className="flex items-start gap-1.5 flex-wrap">
                        <Users className="h-3.5 w-3.5 text-muted-foreground mt-0.5 shrink-0" />
                        {set.job_roles.map((r, i) => (
                            <span key={i} className="text-[11px] text-muted-foreground bg-muted/60 px-1.5 py-0.5 rounded">
                                {r}
                            </span>
                        ))}
                    </div>
                )}

                {/* Topic tags */}
                {set.topic_tags.length > 0 && (
                    <div className="flex items-start gap-1.5 flex-wrap">
                        <Tag className="h-3.5 w-3.5 text-muted-foreground mt-0.5 shrink-0" />
                        {set.topic_tags.map((t, i) => (
                            <span key={i} className="text-[11px] px-1.5 py-0.5 rounded-full bg-primary/8 text-primary border border-primary/15">
                                {t}
                            </span>
                        ))}
                    </div>
                )}
            </CardContent>
        </Card>
    )
}

// ── Set form modal ────────────────────────────────────────────────────────────

interface SetFormProps {
    open: boolean
    onClose: () => void
    onSaved: () => void
    initial?: QuestionSetDetail | null
    sets: QuestionSet[]
}

function SetFormModal({ open, onClose, onSaved, initial, sets }: SetFormProps) {
    const isEdit = Boolean(initial)

    const [title, setTitle] = useState('')
    const [roundType, setRoundType] = useState<'aptitude' | 'technical' | 'behavioural'>('technical')
    const [jobRoles, setJobRoles] = useState<string[]>([])
    const [topicTags, setTopicTags] = useState<string[]>([])
    const [questions, setQuestions] = useState<QuestionRow[]>([])
    const [saving, setSaving] = useState(false)
    const [error, setError] = useState('')

    // Reset form when modal opens
    useEffect(() => {
        if (!open) return
        if (initial) {
            setTitle(initial.title)
            setRoundType(initial.round_type)
            setJobRoles(initial.job_roles)
            setTopicTags(initial.topic_tags)
            setQuestions(
                initial.questions.length > 0
                    ? initial.questions.map(q => ({
                        question: typeof q === 'string' ? q : (q.question ?? ''),
                        answer_key: typeof q === 'string' ? '' : (q.answer_key ?? ''),
                    }))
                    : []
            )
        } else {
            setTitle('')
            setRoundType('technical')
            setJobRoles([])
            setTopicTags([])
            setQuestions([])
        }
        setError('')
    }, [open, initial])

    const excelImportRef = React.useRef<HTMLInputElement>(null)

    const handleExcelImport = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (!file) return
        const reader = new FileReader()
        reader.onload = (evt) => {
            try {
                const data = new Uint8Array(evt.target?.result as ArrayBuffer)
                const wb = XLSX.read(data, { type: 'array' })
                const ws = wb.Sheets[wb.SheetNames[0]]
                const rows: any[][] = XLSX.utils.sheet_to_json(ws, { header: 1, defval: '' })

                if (rows.length === 0) {
                    toast.error('The file appears to be empty.')
                    return
                }

                // Detect header row — skip if any cell in row 0 is a non-numeric string
                // that looks like a label (ID, Question, Answer, etc.)
                const firstRow = rows[0].map((c: any) => String(c ?? '').trim().toLowerCase())
                const looksLikeHeader = firstRow.some(
                    (c: string) => c !== '' && isNaN(Number(c)) && c.length > 0
                )
                const startRow = looksLikeHeader ? 1 : 0

                // Detect which column holds the question text:
                // If header row has a cell containing "question", use that column index.
                // Otherwise default to column 0.
                let questionCol = 0
                let answerCol = 1
                if (looksLikeHeader) {
                    const qIdx = firstRow.findIndex((c: string) => c.includes('question'))
                    const aIdx = firstRow.findIndex((c: string) => c.includes('answer') || c.includes('key'))
                    if (qIdx !== -1) questionCol = qIdx
                    if (aIdx !== -1) answerCol = aIdx
                }

                const imported: QuestionRow[] = rows
                    .slice(startRow)
                    .filter(r => String(r[questionCol] ?? '').trim())
                    .map(r => ({
                        question: String(r[questionCol] ?? '').trim(),
                        answer_key: String(r[answerCol] ?? '').trim(),
                    }))

                if (imported.length === 0) {
                    toast.error('No questions found in the file. Check the format.')
                    return
                }

                setQuestions(prev => {
                    const existing = prev.filter(q => q.question.trim())
                    return [...existing, ...imported]
                })
                setError('') // Clear error when questions are added
                toast.success(`Imported ${imported.length} question${imported.length !== 1 ? 's' : ''} from Excel`)
            } catch {
                toast.error('Could not parse the Excel file. Use the template format.')
            } finally {
                if (excelImportRef.current) excelImportRef.current.value = ''
            }
        }
        reader.readAsArrayBuffer(file)
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')

        if (!title.trim()) { setError('Title is required.'); return }
        const validQs = questions.filter(q => q.question.trim())
        if (validQs.length === 0) { setError('Add at least one question.'); return }

        setSaving(true)
        try {
            const payload = {
                title: title.trim(),
                round_type: roundType,
                job_roles: jobRoles,
                topic_tags: topicTags,
                questions: validQs,
            }
            
            // Duplicate name check (R017)
            const isDuplicate = sets.some((s: QuestionSet) => 
                s.title.toLowerCase() === payload.title.toLowerCase() && 
                (!isEdit || s.id !== initial?.id)
            )
            if (isDuplicate) {
                setError('A question set with this name already exists. Please use a unique title.')
                setSaving(false)
                return
            }

            if (isEdit && initial) {
                await APIClient.put(`/api/repository/sets/${initial.id}`, payload)
                toast.success('Question set updated')
            } else {
                await APIClient.post('/api/repository/sets', payload)
                toast.success('Question set created')
            }
            onSaved()
            onClose()
        } catch (err: any) {
            setError(err.message || 'Failed to save question set.')
        } finally {
            setSaving(false)
        }
    }

    return (
        <Dialog open={open} onOpenChange={v => { if (!v) onClose() }}>
            <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle className="text-lg font-bold">
                        {isEdit ? 'Edit Question Set' : 'Create New Question Set'}
                    </DialogTitle>
                    <DialogDescription className="text-sm text-muted-foreground">
                        Question sets are reusable collections you can pick when creating a job instead of uploading a file.
                    </DialogDescription>
                </DialogHeader>

                <form onSubmit={handleSubmit} className="space-y-5 pt-2">
                    {error && (
                        <div className="p-3 bg-destructive/10 border border-destructive/20 text-destructive rounded-lg text-sm">
                            {error}
                        </div>
                    )}

                    {/* Title */}
                    <div className="space-y-1.5">
                        <Label htmlFor="qs-title" className="text-sm font-semibold">Title *</Label>
                        <Input
                            id="qs-title"
                            value={title}
                            onChange={e => setTitle(e.target.value)}
                            placeholder="e.g. Steel Detailer — Technical Set v3"
                            className="h-10"
                            required
                        />
                    </div>

                    {/* Round Type */}
                    <div className="space-y-1.5">
                        <Label htmlFor="qs-round" className="text-sm font-semibold">Round Type *</Label>
                        <select
                            id="qs-round"
                            value={roundType}
                            onChange={e => setRoundType(e.target.value as typeof roundType)}
                            className="w-full h-10 px-3 border border-input rounded-lg bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
                        >
                            {ROUND_TYPE_OPTIONS.map(o => (
                                <option key={o.value} value={o.value}>{o.label}</option>
                            ))}
                        </select>
                    </div>

                    {/* Job Roles */}
                    <div className="space-y-1.5">
                        <Label className="text-sm font-semibold">Job Roles</Label>
                        <p className="text-xs text-muted-foreground">
                            Used to auto-match this set when creating a job with a matching role name.
                        </p>
                        <TagInput
                            value={jobRoles}
                            onChange={setJobRoles}
                            placeholder="e.g. Steel Detailer, CAD Engineer — press Enter or comma"
                        />
                    </div>

                    {/* Topic Tags */}
                    <div className="space-y-1.5">
                        <Label className="text-sm font-semibold">Topic Tags</Label>
                        <p className="text-xs text-muted-foreground">
                            Shown as pills on the set card and in the job form picker.
                        </p>
                        <TagInput
                            value={topicTags}
                            onChange={setTopicTags}
                            placeholder="e.g. Tekla, AISC, Connections — press Enter or comma"
                        />
                    </div>

                    {/* Questions */}
                    <div className="space-y-3">
                        <div className="flex items-center justify-between">
                            <Label className="text-sm font-semibold">Questions *</Label>
                            <div className="flex items-center gap-2">
                                {/* Hidden file input for Excel */}
                                <input
                                    ref={excelImportRef}
                                    type="file"
                                    accept=".xlsx,.xls"
                                    className="hidden"
                                    onChange={handleExcelImport}
                                />
                                <Button
                                    type="button"
                                    variant="outline"
                                    size="sm"
                                    onClick={() => excelImportRef.current?.click()}
                                    className="gap-1.5 h-7 text-xs text-green-700 dark:text-green-400 border-green-600/30 hover:bg-green-500/10"
                                >
                                    <FileSpreadsheet className="h-3.5 w-3.5" />
                                    Import Excel
                                </Button>
                                {questions.length > 0 && (
                                    <Button
                                        type="button"
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => {
                                            if (window.confirm("Are you sure you want to clear all questions? This cannot be undone.")) {
                                                setQuestions([]);
                                                setError('Add at least one question.');
                                                toast.error('All questions cleared');
                                            }
                                        }}
                                        className="gap-1.5 h-7 text-xs text-destructive hover:bg-destructive/10"
                                    >
                                        <Trash2 className="h-3.5 w-3.5" />
                                        Clear All
                                    </Button>
                                )}
                            </div>
                        </div>

                        {/* Format hint */}
                        <p className="text-xs text-muted-foreground">
                            Upload an <code className="font-mono bg-muted px-1 rounded">.xlsx</code> file — Column A: Question, Column B: Answer Key (optional)
                        </p>

                        {/* Preview of imported questions */}
                        {questions.filter(q => q.question.trim()).length > 0 ? (
                            <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
                                {questions.filter(q => q.question.trim()).map((q, i) => (
                                    <div
                                        key={i}
                                        className="flex gap-2 items-start p-3 rounded-lg border border-border bg-muted/20"
                                    >
                                        <span className="text-xs text-muted-foreground font-mono mt-0.5 w-5 shrink-0 text-right">
                                            {i + 1}.
                                        </span>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm text-foreground leading-snug">{q.question}</p>
                                            {q.answer_key && (
                                                <p className="text-xs text-muted-foreground mt-0.5 truncate">
                                                    Key: {q.answer_key}
                                                </p>
                                            )}
                                        </div>
                                        <button
                                            type="button"
                                            onClick={() => {
                                                if (window.confirm("Are you sure you want to delete this question?")) {
                                                    const next = questions.filter((_, idx) => idx !== i);
                                                    setQuestions(next);
                                                    if (next.filter(q => q.question.trim()).length === 0) {
                                                        setError('Add at least one question.');
                                                    }
                                                    toast.info('Question removed');
                                                }
                                            }}
                                            className="mt-0.5 p-1 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors shrink-0"
                                        >
                                            <X className="h-3.5 w-3.5" />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="flex flex-col items-center justify-center py-8 rounded-lg border border-dashed border-border bg-muted/10 gap-2 text-center">
                                {error && error.includes('at least one question') && (
                                    <div className="text-destructive text-xs mb-2 font-semibold">Validation: Add at least one question to proceed.</div>
                                )}
                                <FileSpreadsheet className="h-8 w-8 text-muted-foreground/30" />
                                <p className="text-sm text-muted-foreground">No questions imported yet</p>
                                <Button
                                    type="button"
                                    variant="outline"
                                    size="sm"
                                    onClick={() => excelImportRef.current?.click()}
                                    className="gap-1.5 text-xs mt-1"
                                >
                                    <FileSpreadsheet className="h-3.5 w-3.5" />
                                    Import Excel
                                </Button>
                            </div>
                        )}

                        {questions.filter(q => q.question.trim()).length > 0 && (
                            <p className="text-xs text-muted-foreground">
                                {questions.filter(q => q.question.trim()).length} question{questions.filter(q => q.question.trim()).length !== 1 ? 's' : ''} imported
                                <button
                                    type="button"
                                    onClick={() => {
                                        if (window.confirm('Are you sure you want to clear all questions? This action cannot be undone.')) {
                                            setQuestions([]);
                                            const msg = 'All questions have been cleared. Please add at least one question to save.';
                                            setError(msg);
                                            toast.error(msg, { duration: 5000 });
                                        }
                                    }}
                                    className="ml-2 text-destructive/70 hover:text-destructive underline underline-offset-2"
                                >
                                    Clear all
                                </button>
                            </p>
                        )}
                    </div>

                    <DialogFooter className="pt-2 gap-2">
                        <Button type="button" variant="outline" onClick={onClose} disabled={saving}>
                            Cancel
                        </Button>
                        <Button type="submit" disabled={saving} className="min-w-[120px]">
                            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : isEdit ? 'Save Changes' : 'Create Set'}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function RepositoryPage() {
    const { user } = useAuth()
    const router = useRouter()

    const [sets, setSets] = useState<QuestionSet[]>([])
    const [loading, setLoading] = useState(true)
    const [filterRound, setFilterRound] = useState<string>('all')
    const [search, setSearch] = useState('')

    const [formOpen, setFormOpen] = useState(false)
    const [editTarget, setEditTarget] = useState<QuestionSetDetail | null>(null)
    const [loadingDetail, setLoadingDetail] = useState(false)

    const [deleteTarget, setDeleteTarget] = useState<QuestionSet | null>(null)
    const [deleting, setDeleting] = useState(false)

    // Access guard
    if (user && user.role !== 'hr' && user.role !== 'super_admin') {
        return (
            <div className="flex flex-col items-center justify-center p-20 gap-4 text-center">
                <Database className="h-16 w-16 text-muted-foreground/20" />
                <h2 className="text-2xl font-black">Access Denied</h2>
                <p className="text-muted-foreground">This page is restricted to HR and Administrators.</p>
                <Button onClick={() => router.push('/dashboard/hr')}>Return to Dashboard</Button>
            </div>
        )
    }

    const fetchSets = useCallback(async () => {
        setLoading(true)
        try {
            const data = await APIClient.get<QuestionSet[]>('/api/repository/sets')
            setSets(Array.isArray(data) ? data : [])
        } catch (err: any) {
            console.error('Failed to load question sets:', err)
            toast.error('Failed to load question sets')
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => { fetchSets() }, [fetchSets])

    const openCreate = () => {
        setEditTarget(null)
        setFormOpen(true)
    }

    const openEdit = async (set: QuestionSet) => {
        setLoadingDetail(true)
        try {
            const detail = await APIClient.get<QuestionSetDetail>(`/api/repository/sets/${set.id}`)
            setEditTarget(detail)
            setFormOpen(true)
        } catch {
            toast.error('Failed to load set details')
        } finally {
            setLoadingDetail(false)
        }
    }

    const handleDelete = async () => {
        if (!deleteTarget) return
        setDeleting(true)
        try {
            await APIClient.delete(`/api/repository/sets/${deleteTarget.id}`)
            toast.success('Question set deleted')
            setSets(prev => prev.filter(s => s.id !== deleteTarget.id))
            setDeleteTarget(null)
        } catch {
            toast.error('Failed to delete question set')
        } finally {
            setDeleting(false)
        }
    }

    // Filtered view
    const filtered = sets.filter(s => {
        const matchRound = filterRound === 'all' || s.round_type === filterRound
        const q = search.toLowerCase()
        const matchSearch = !q ||
            s.title.toLowerCase().includes(q) ||
            s.job_roles.some(r => r.toLowerCase().includes(q)) ||
            s.topic_tags.some(t => t.toLowerCase().includes(q))
        return matchRound && matchSearch
    })

    const counts = {
        all: sets.length,
        aptitude: sets.filter(s => s.round_type === 'aptitude').length,
        technical: sets.filter(s => s.round_type === 'technical').length,
        behavioural: sets.filter(s => s.round_type === 'behavioural').length,
    }

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {/* Page header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="space-y-1">
                    <h1 className="text-2xl font-bold text-foreground flex items-center gap-2.5">
                        <Database className="h-6 w-6 text-primary" />
                        Question Repository
                    </h1>
                    <p className="text-sm text-muted-foreground">
                        Manage reusable question sets for aptitude, technical, and behavioural rounds.
                    </p>
                </div>
                <Button onClick={openCreate} className="gap-2 shrink-0" disabled={loadingDetail}>
                    {loadingDetail ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                    Create New Set
                </Button>
            </div>

            {/* Filter bar */}
            <div className="flex flex-col sm:flex-row gap-3">
                <Input
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                    placeholder="Search by title, role, or tag…"
                    className="h-9 max-w-xs text-sm"
                />
                <div className="flex gap-2 flex-wrap">
                    {(['all', 'aptitude', 'technical', 'behavioural'] as const).map(rt => (
                        <button
                            key={rt}
                            onClick={() => setFilterRound(rt)}
                            className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                                filterRound === rt
                                    ? 'bg-primary text-primary-foreground border-primary'
                                    : 'bg-background text-muted-foreground border-border hover:border-primary/40 hover:text-foreground'
                            }`}
                        >
                            {rt === 'all' ? 'All' : rt.charAt(0).toUpperCase() + rt.slice(1)}
                            <span className="ml-1.5 opacity-70">
                                {counts[rt]}
                            </span>
                        </button>
                    ))}
                </div>
            </div>

            {/* Content */}
            {loading ? (
                <div className="flex items-center justify-center py-24">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
            ) : sets.length === 0 ? (
                <EmptyState onAdd={openCreate} />
            ) : filtered.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-20 gap-3 text-center">
                    <BookOpen className="h-10 w-10 text-muted-foreground/30" />
                    <p className="text-sm text-muted-foreground">No sets match your filter.</p>
                    <Button variant="ghost" size="sm" onClick={() => { setSearch(''); setFilterRound('all') }}>
                        Clear filters
                    </Button>
                </div>
            ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                    {filtered.map(set => (
                        <SetCard
                            key={set.id}
                            set={set}
                            onEdit={openEdit}
                            onDelete={setDeleteTarget}
                        />
                    ))}
                </div>
            )}

            {/* Create / Edit modal */}
            <SetFormModal
                open={formOpen}
                onClose={() => { setFormOpen(false); setEditTarget(null) }}
                onSaved={fetchSets}
                initial={editTarget}
                sets={sets}
            />

            {/* Delete confirm */}
            <AlertDialog open={Boolean(deleteTarget)} onOpenChange={v => { if (!v) setDeleteTarget(null) }}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Delete question set?</AlertDialogTitle>
                        <AlertDialogDescription>
                            <strong>{deleteTarget?.title}</strong> will be permanently deleted.
                            Any jobs referencing this set will fall back to AI-generated questions.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel disabled={deleting}>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={handleDelete}
                            disabled={deleting}
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                            {deleting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Delete'}
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    )
}
