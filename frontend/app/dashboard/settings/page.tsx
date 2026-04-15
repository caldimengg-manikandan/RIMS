'use client'

import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { APIClient } from '@/app/dashboard/lib/api-client'
import { toast } from "sonner"
import { Building2, Mail, Phone, User, Image as ImageIcon, FileText, Save, Loader2, ShieldAlert } from 'lucide-react'
import { useAuth } from '@/app/dashboard/lib/auth-context'
import { useRouter } from 'next/navigation'

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
            <div className="flex justify-between">
                <div>
                    <h1 className="text-3xl font-extrabold tracking-tight">System Settings</h1>
                    <p className="text-muted-foreground mt-1">Configure company details and automation templates</p>
                </div>
                <div className="flex justify-end pt-4">
                    <Button 
                        size="lg" 
                        className="gap-2 px-8 font-bold" 
                        onClick={handleSave}
                        disabled={saving}
                    >
                        {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                        Save Changes
                    </Button>
                </div>
            </div>

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
                            
                            <div className="space-y-2">
                                <Label htmlFor="logo_url">Company Logo URL</Label>
                                <Input 
                                    id="logo_url" 
                                    value={settings.company_logo_url} 
                                    onChange={(e) => setSettings({...settings, company_logo_url: e.target.value})}
                                    placeholder="https://example.com/logo.png"
                                />
                            </div>

                            {settings.company_logo_url && (
                                <div className="mt-4 p-4 border rounded-xl bg-muted/20 flex justify-center overflow-hidden">
                                    <img src={settings.company_logo_url} alt="Logo preview" className="max-h-24 object-contain" />
                                </div>
                            )}

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
                                    onChange={(e) => setSettings({...settings, hr_phone: e.target.value})}
                                    placeholder="+1 (555) 000-0000"
                                />
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
                                    input.accept = '.html,.txt';
                                    input.onchange = (e: any) => {
                                        const file = e.target.files[0];
                                        if (file) {
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
