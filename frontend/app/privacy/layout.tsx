import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Privacy Policy – CALRIMS',
  description: 'Read the Privacy Policy for CALRIMS. Understand how we collect, use, and protect your data while complying with global privacy standards.',
  openGraph: {
  title: 'Privacy Policy – CALRIMS',
    description: 'Read the Privacy Policy for CALRIMS. Understand how we collect, use, and protect your data while complying with global privacy standards.',
    images: ['/og-image.jpg'],
  },
  alternates: {
    canonical: 'https://caldimproducts.com/cal-rims/privacy'
  }
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
