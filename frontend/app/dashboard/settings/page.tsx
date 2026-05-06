'use client'

import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { APIClient } from '@/app/dashboard/lib/api-client'
import { toast } from "sonner"
import { Loader2, Save, Building2, User, Mail, Phone, FileText, ShieldAlert, Settings, Image as ImageIcon } from 'lucide-react'
import { PageHeader } from '@/components/page-header'
import { useAuth } from '@/app/dashboard/lib/auth-context'
import { useRouter } from 'next/navigation'
import { ModeToggle } from '@/components/mode-toggle'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'

export default function SettingsPage() {
    const { user } = useAuth()
    const router = useRouter()
    const [loading, setLoading] = useState(false)
    const [saving, setSaving] = useState(false)
    const [settings, setSettings] = useState({
        company_logo_url: '',
        company_name: '',
        company_address: '',
        hr_email: '',
        hr_name: '',
        hr_phone: '',
        offer_letter_template: ''
    })

    if (user && user.role !== 'hr' && user.role !== 'super_admin') {
        return (
            <div className="flex flex-col items-center justify-center p-20 gap-4 text-center">
                <ShieldAlert className="h-16 w-16 text-destructive opacity-20" />
                <h2 className="text-2xl font-black">Access Denied</h2>
                <p className="text-muted-foreground">This page is restricted to HR and Administrators only.</p>
                <Button onClick={() => router.push('/dashboard/hr')}>Return to Dashboard</Button>
            </div>
        )
    }

    useEffect(() => {
        fetchSettings()
    }, [])

    const fetchSettings = async () => {
        setLoading(true)
        try {
            const data = await APIClient.get('/api/settings') as any
            setSettings(data)
        } catch (error) {
            toast.error("Failed to load settings")
        } finally {
            setLoading(false)
        }
    }
    const handleSave = async () => {
        if (!settings.company_name.trim() || !settings.hr_name.trim() || !settings.hr_email.trim() || !settings.hr_phone.trim() || !settings.company_address.trim()) {
            toast.error("Please fill in all required fields (Company Name, Address, HR Name, Email, Phone)");
            return;
        }

    const isEmailValid = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(settings.hr_email);
    if (!isEmailValid) {
        toast.error("Please enter a valid email address");
        return;
    }

    const isPhoneValid = /^\+?[0-9\s]{7,15}$/.test(settings.hr_phone);
    if (!isPhoneValid) {
        toast.error("Please enter a valid phone number (7-15 digits)");
        return;
    }

    const isCompanyNameValid = /^[A-Za-z\s&.,'-]{2,100}$/.test(settings.company_name);
    if (!isCompanyNameValid) {
        toast.error("Please enter a valid company name");
        return;
    }

    const isNameValid = /^[A-Za-z\s'-]{2,50}$/.test(settings.hr_name);
    if (!isNameValid) {
        toast.error("Please enter a valid name");
        return;
    }

        setSaving(true)
        try {
            await APIClient.post('/api/settings', settings)
            toast.success("Saved successfully")
        } catch (error) {
            toast.error("Failed to update settings")
        } finally {
            setSaving(false)
        }
    }

    if (loading) {
        return (
            <div className="flex items-center justify-center p-20">
                <Loader2 className="h-10 w-10 animate-spin text-primary" />
            </div>
        )
    }

    return (
        <div className="p-6 max-w-5xl mx-auto space-y-8 animate-in fade-in duration-500">
            <PageHeader
                title="System Settings"
                description="Configure company details and automation templates"
                icon={Settings}
            >
                <Button 
                    size="lg" 
                    className="font-bold gap-2 px-8 shadow-md rounded-xl h-12"
                    onClick={handleSave}
                    disabled={saving}
                >
                    {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                    Save Changes
                </Button>
            </PageHeader>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Card className="border-border/50 shadow-sm overflow-hidden">
                    <CardHeader className="bg-muted/30">
                        <CardTitle className="flex items-center gap-2 text-lg">
                            <Building2 className="h-5 w-5 text-primary" />
                            Company Profile
                        </CardTitle>
                        <CardDescription>Basic information used in communications</CardDescription>
                    </CardHeader>
                    <CardContent className="p-6 space-y-6">
                        <div className="space-y-4">
                            <div className="space-y-2">
                                <Label htmlFor="company_name">Company Name</Label>
                                <Input 
                                    id="company_name" 
                                    value={settings.company_name} 
                                    onChange={(e) => setSettings({...settings, company_name: e.target.value})}
                                    placeholder="e.g. Acme Corp"
                                />
                            </div>
                            
                            <div className="space-y-4">
                                <Label htmlFor="logo_url">Company Logo</Label>
                                <div className="flex items-center gap-4">
                                    <div className="h-20 w-20 rounded-2xl bg-muted/30 border-2 border-dashed border-border/50 flex items-center justify-center overflow-hidden group relative">
                                        {settings.company_logo_url ? (
                                            <img 
                                                src={settings.company_logo_url} 
                                                alt="Logo" 
                                                className="h-full w-full object-contain p-2"
                                                onError={(e) => {
                                                    (e.target as HTMLImageElement).src = 'https://api.dicebear.com/7.x/bottts/svg?seed=' + encodeURIComponent(settings.company_name || 'C')
                                                }}
                                            />
                                        ) : (
                                            <ImageIcon className="h-8 w-8 text-muted-foreground/40" />
                                        )}
                                    </div>
                                    <div className="flex-1 space-y-2">
                                        <div className="flex gap-2 w-full">
                                            <Input 
                                                id="logo_url" 
                                                value={settings.company_logo_url} 
                                                onChange={(e) => setSettings({...settings, company_logo_url: e.target.value})}
                                                placeholder="https://example.com/logo.png"
                                                className="flex-1 h-12"
                                            />
                                        </div>
                                        <p className="text-[10px] text-muted-foreground italic">Paste a transparent PNG/SVG link for best results in PDFs.</p>
                                    </div>
                                </div>
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="company_address">Office Address</Label>
                                <Textarea 
                                    id="company_address" 
                                    value={settings.company_address} 
                                    onChange={(e) => setSettings({...settings, company_address: e.target.value})}
                                    placeholder="123 Silicon Valley, CA"
                                    rows={3}
                                />
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <Card className="border-border/50 shadow-sm overflow-hidden flex flex-col">
                    <CardHeader className="bg-muted/30">
                        <CardTitle className="flex items-center gap-2 text-lg">
                            <ImageIcon className="h-5 w-5 text-primary" />
                            HR Details
                        </CardTitle>
                        <CardDescription>HR Contact Information</CardDescription>
                    </CardHeader>
                    
                    <CardContent className="p-6 space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="hr_name">HR Contact Name</Label>
                            <div className="relative">
                                <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                <Input 
                                    id="hr_name" 
                                    className="pl-10"
                                    value={settings.hr_name} 
                                    onChange={(e) => setSettings({...settings, hr_name: e.target.value})}
                                    placeholder="e.g. Jane Smith"
                                />
                            </div>
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="hr_email">HR Contact Email</Label>
                            <div className="relative">
                                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                <Input 
                                    id="hr_email" 
                                    type="email"
                                    required
                                    className="pl-10"
                                    value={settings.hr_email} 
                                    onChange={(e) => setSettings({...settings, hr_email: e.target.value})}
                                    placeholder="hr@company.com"
                                />
                            </div>
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="hr_phone">HR Contact Phone</Label>
                            <div className="relative">
                                <Phone className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                <Input 
                                    id="hr_phone" 
                                    className="pl-10"
                                    value={settings.hr_phone} 
                                    maxLength={15}
                                    onChange={(e) => {
                                        const val = e.target.value;
                                        if (val === '' || /^[0-9+]+$/.test(val)) {
                                            setSettings({...settings, hr_phone: val});
                                        }
                                    }}
                                    placeholder="+91 9876543210"
                                />
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* New Theme Preference Card */}
                <Card className="border-border/50 shadow-sm overflow-hidden md:col-span-2">
                    <CardHeader className="bg-muted/30">
                        <div className="flex items-center justify-between">
                            <div>
                                <CardTitle className="flex items-center gap-2 text-lg">
                                    <Settings className="h-5 w-5 text-primary" />
                                    Theme Preferences
                                </CardTitle>
                                <CardDescription>Choose how CAL-RIMS looks to you</CardDescription>
                            </div>
                            <ModeToggle />
                        </div>
                    </CardHeader>
                    <CardContent className="p-6">
                        <div className="flex items-center justify-between gap-6">
                            <div className="space-y-1">
                                <p className="text-sm font-medium">Appearance Mode</p>
                                <p className="text-xs text-muted-foreground">Select between Light, Dark, or System default theme.</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>

            <Card className="border-border/50 shadow-sm overflow-hidden">
                <CardHeader className="bg-muted/30">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                        <div>
                            <CardTitle className="flex items-center gap-2 text-lg">
                                <FileText className="h-5 w-5 text-primary" />
                                Offer Letter Template
                            </CardTitle>
                            <CardDescription>Paste the edited HTML code (with internal css) of the offer letter. Use the placeholders specified below</CardDescription>
                        </div>
                        <div className="flex items-center gap-2">
                            <Button 
                                variant="outline" 
                                size="sm" 
                                className="gap-2"
                                onClick={() => {
                                    const input = document.createElement('input');
                                    input.type = 'file';
                                    input.accept = '.html';
                                    input.onchange = (e: any) => {
                                        const file = e.target.files[0];
                                        if (file) {
                                            // Validate file type
                                            const fileName = file.name.toLowerCase();
                                            if (!fileName.endsWith('.html') && !fileName.endsWith('.htm')) {
                                                toast.error("Invalid file type. Only HTML files are supported.");
                                                return;
                                            }

                                            const reader = new FileReader();
                                            reader.onload = (re) => {
                                                setSettings({...settings, offer_letter_template: re.target?.result as string});
                                                toast.success("Template uploaded successfully");
                                            };
                                            reader.readAsText(file);
                                        }
                                    };
                                    input.click();
                                }}
                            >
                                <Building2 className="h-4 w-4" />
                                Upload HTML
                            </Button>
                            <Button 
                                variant="secondary" 
                                size="sm" 
                                className="gap-2"
                                onClick={() => {
                                    if (!settings.offer_letter_template) {
                                        toast.error("Template is empty");
                                        return;
                                    }
                                    const win = window.open('', '_blank');
                                    if (win) {
                                        // Simple preview replacement for demonstration
                                        let html = settings.offer_letter_template;
                                        const mocks: Record<string, string> = {
                                            candidate_name: 'John Doe',
                                            job_role: 'Software Engineer',
                                            company_name: settings.company_name || 'Acme Corp',
                                            offer_date: new Date().toLocaleDateString()
                                        };
                                        Object.keys(mocks).forEach(key => {
                                            html = html.replace(new RegExp(`{{${key}}}`, 'g'), mocks[key]);
                                        });
                                        win.document.write(html);
                                        win.document.close();
                                    }
                                }}
                            >
                                <ImageIcon className="h-4 w-4" />
                                Preview
                            </Button>
                        </div>
                    </div>
                </CardHeader>
                <CardContent className="p-6 space-y-4">
                    <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-xl border border-blue-100 dark:border-blue-800">
                        <div className="flex items-center justify-between mb-2">
                            <h4 className="font-bold text-blue-800 dark:text-blue-300 text-sm">Available Placeholders</h4>
                            <span className="text-[10px] uppercase font-bold text-blue-600/50">Usage: {'{{placeholder}}'}</span>
                        </div>
                        <div className="flex flex-wrap gap-2">
                            {['candidate_name', 'job_role', 'department', 'joining_date', 'company_name', 'hr_name', 'offer_date', 'hr_email', 'hr_phone'].map(p => (
                                <code key={p} className="bg-white dark:bg-slate-800 px-1.5 py-0.5 rounded border text-[10px] font-mono shadow-sm">{p}</code>
                            ))}
                        </div>
                    </div>
                    <div className="relative group">
                        <div className="absolute top-3 left-3 text-[10px] font-bold text-muted-foreground/30 uppercase pointer-events-none group-focus-within:opacity-50 transition-opacity">
                            HTML Source Code
                        </div>
                        <Textarea 
                            id="offer_letter_template" 
                            className="min-h-[250px] max-h-[500px] font-mono text-[11px] pt-8 leading-relaxed resize-y scrollbar-thin"
                            value={settings.offer_letter_template} 
                            onChange={(e) => setSettings({...settings, offer_letter_template: e.target.value})}
                            placeholder="<html>\n  <head>\n    <style>...</style>\n  </head>\n  <body>\n    <h1>Welcome {{candidate_name}}!</h1>\n  </body>\n</html>"
                        />
                    </div>
                </CardContent>
            </Card>


        </div>
    )
}
