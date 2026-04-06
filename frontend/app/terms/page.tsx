import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-background text-foreground py-20 px-6">
      <div className="max-w-3xl mx-auto space-y-8">
        <Link href="/">
          <Button variant="ghost" className="mb-4 pl-0 hover:bg-transparent hover:underline">
            <ArrowLeft className="mr-2 h-4 w-4" /> Back to Home
          </Button>
        </Link>
        <h1 className="text-4xl font-extrabold tracking-tight">Terms of Service</h1>
        <div className="prose prose-slate dark:prose-invert max-w-none">
          <p>Last updated: {new Date().toLocaleDateString()}</p>
          <p>
            Welcome to CALRIMS. By accessing or using our platform, you agree to be bound by these Terms of Service.
          </p>
          <h2>1. Acceptance of Terms</h2>
          <p>
            By creating an account and using the service, you accept and agree to comply with these terms. If you do not agree, you may not use our services.
          </p>
          <h2>2. Use of Service</h2>
          <p>
            You agree to use the service only for lawful purposes. You represent and warrant that you have full right and authority to enter into these Terms of Service.
          </p>
          <h2>3. Modifications</h2>
          <p>
            We reserve the right to modify these terms at any time. We will notify users of any significant changes.
          </p>
        </div>
      </div>
    </div>
  );
}
