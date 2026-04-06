import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: "Create Account – CALRIMS",
  description: "Create your CALRIMS account to start automating your recruitment natively with AI interviews, skill scoring, and intelligent candidate matching.",
  openGraph: {
    title: "Create Account – CALRIMS",
    description: "Create your CALRIMS account to start automating your recruitment natively with AI interviews, skill scoring, and intelligent candidate matching.",
    images: ['/og-image.jpg'],
  },
  alternates: {
    canonical: "https://caldimproducts.com/cal-rims/auth/register"
  }
}

export default function RegisterLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>
}
