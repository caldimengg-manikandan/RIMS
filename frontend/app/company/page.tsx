'use client'

import React from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { ArrowRight, Globe, Users, Zap, Shield, Star, Award } from 'lucide-react'
import { Badge } from '@/components/ui/badge'

export default function CompanyPage() {
    return (
        <div className="min-h-screen bg-background font-sans">

            {/* Hero Section */}
            <section className="relative overflow-hidden py-24 md:py-32 lg:py-40 flex items-center justify-center border-b border-border/50">
                <div className="absolute inset-0 z-0">
                    <div className="absolute inset-0 bg-gradient-to-b from-transparent to-background/90" />
                    <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] bg-primary/10 rounded-full blur-3xl" />
                    <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] bg-accent/10 rounded-full blur-3xl" />
                </div>

                <div className="relative z-10 max-w-5xl mx-auto px-6 text-center space-y-8 animate-in fade-in slide-in-from-bottom-8 duration-1000">
                    <Badge variant="outline" className="bg-primary/10 text-primary border-primary/20 px-4 py-1.5 text-sm font-bold rounded-full">
                        ✨ Top 100 Innovators
                    </Badge>
                    <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight text-foreground leading-[1.1]">
                        Innovate the <span className="bg-clip-text text-transparent bg-gradient-to-r from-primary to-accent">Future</span> With Us.
                    </h1>
                    <p className="text-xl md:text-2xl text-muted-foreground max-w-3xl mx-auto leading-relaxed">
                        We are building cutting-edge intelligent systems. Join a team of passionate engineers, designers, and thinkers reshaping how the world works.
                    </p>
                    <div className="flex flex-col sm:flex-row gap-4 justify-center items-center pt-8">
                        <Link href="/jobs">
                            <Button size="lg" className="h-14 px-8 text-lg font-bold bg-foreground hover:bg-foreground/90 text-background rounded-full shadow-xl hover:shadow-2xl transition-all hover:-translate-y-1">
                                View Open Positions
                                <ArrowRight className="ml-2 h-5 w-5" />
                            </Button>
                        </Link>
                    </div>
                </div>
            </section>

            {/* Values / Why Join */}
            <section className="py-24 bg-card/30">
                <div className="max-w-7xl mx-auto px-6">
                    <div className="text-center mb-16 space-y-4">
                        <h2 className="text-3xl md:text-4xl font-bold">Why Join Us?</h2>
                        <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                            We offer more than just a job. We offer an environment where your best work is celebrated.
                        </p>
                    </div>

                    <div className="grid md:grid-cols-3 gap-8">
                        <ValueCard
                            icon={Zap}
                            title="Fast-Paced Innovation"
                            description="We move quickly from idea to execution. Your code ships to millions, not to the backlog."
                            delay="0"
                        />
                        <ValueCard
                            icon={Users}
                            title="Inclusive Culture"
                            description="A diverse team is a strong team. We foster an environment of belonging and mutual respect."
                            delay="100"
                        />
                        <ValueCard
                            icon={Shield}
                            title="Radical Transparency"
                            description="No hidden agendas. We share metrics, financial health, and strategic pivots openly with everyone."
                            delay="200"
                        />
                    </div>
                </div>
            </section>

            {/* Generic Footer */}
            <footer className="border-t border-border py-12 bg-card">
                <div className="max-w-7xl mx-auto px-6 text-center text-muted-foreground text-sm">
                    <p>© {new Date().getFullYear()} Caldim Tech. All rights reserved.</p>
                </div>
            </footer>
        </div>
    )
}

function ValueCard({ icon: Icon, title, description, delay }: { icon: any, title: string, description: string, delay: string }) {
    return (
        <Card style={{ animationDelay: `${delay}ms` }} className="bg-card/50 backdrop-blur-md border-border hover:border-primary/30 transition-colors duration-300 animate-in fade-in slide-in-from-bottom-8 fill-mode-both shadow-sm hover:shadow-md">
            <CardContent className="p-8">
                <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-6">
                    <Icon className="h-6 w-6 text-primary" />
                </div>
                <h3 className="text-xl font-bold mb-3">{title}</h3>
                <p className="text-muted-foreground leading-relaxed">
                    {description}
                </p>
            </CardContent>
        </Card>
    )
}

function TestimonialCard({ name, role, text, delay }: { name: string, role: string, text: string, delay: string }) {
    return (
        <Card style={{ animationDelay: `${delay}ms` }} className="bg-background border-border shadow-md animate-in fade-in slide-in-from-bottom-8 fill-mode-both">
            <CardContent className="p-8 space-y-6">
                <div className="flex gap-1">
                    {[1, 2, 3, 4, 5].map(i => <Star key={i} className="h-5 w-5 fill-amber-400 text-amber-400" />)}
                </div>
                <p className="text-lg leading-relaxed italic text-foreground/90">
                    "{text}"
                </p>
                <div className="flex items-center gap-4 pt-4 border-t border-border">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-accent flex items-center justify-center text-primary-foreground font-bold text-sm">
                        {name.charAt(0)}
                    </div>
                    <div>
                        <div className="font-bold">{name}</div>
                        <div className="text-sm text-muted-foreground">{role}</div>
                    </div>
                </div>
            </CardContent>
        </Card>
    )
}


