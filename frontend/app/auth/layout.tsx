import React from 'react'
import { ParticlesBackground } from '@/components/particles-background'

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="min-h-screen relative overflow-hidden bg-transparent">
      {children}
    </div>
  )
}
