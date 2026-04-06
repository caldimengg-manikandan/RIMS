import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: "Sign In – CALRIMS",
  description: "Sign in to your CALRIMS account to manage your AI-powered recruitment pipeline, view granular analytics, and hire exceptional talent seamlessly.",
  openGraph: {
    title: "Sign In – CALRIMS",
    description: "Sign in to your CALRIMS account to manage your AI-powered recruitment pipeline, view granular analytics, and hire exceptional talent seamlessly.",
    images: ['/og-image.jpg'],
  },
  alternates: {
    canonical: "https://caldimproducts.com/cal-rims/auth/login"
  }
}

export default function LoginLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>
}
