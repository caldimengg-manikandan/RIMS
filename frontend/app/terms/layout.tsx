import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Terms of Service – CALRIMS',
  description: 'Read the Terms of Service for CALRIMS, an AI-powered recruitment intelligence platform. Learn about our service agreements, rules, and guidelines.',
  openGraph: {
  title: 'Terms of Service – CALRIMS',
    description: 'Read the Terms of Service for CALRIMS, an AI-powered recruitment intelligence platform. Learn about our service agreements, rules, and guidelines.',
    images: ['/og-image.jpg'],
  },
  alternates: {
    canonical: 'https://caldimproducts.com/cal-rims/terms'
  }
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
