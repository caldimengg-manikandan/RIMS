import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-background text-foreground py-20 px-6">
      <div className="max-w-3xl mx-auto space-y-8">
        <Link href="/">
          <Button variant="ghost" className="mb-4 pl-0 hover:bg-transparent hover:underline">
            <ArrowLeft className="mr-2 h-4 w-4" /> Back to Home
          </Button>
        </Link>
        <h1 className="text-4xl font-extrabold tracking-tight">Privacy Policy</h1>
        <div className="prose prose-slate dark:prose-invert max-w-none">
          <p>Last updated: {new Date().toLocaleDateString()}</p>
          <p>
            At CALRIMS, we are committed to protecting your privacy and ensuring the security of your personal data.
          </p>
          <h2>1. Information We Collect</h2>
          <p>
            We collect information you provide directly to us, such as when you create an account, update your profile, or use our services. This includes names, emails, and professional experience data.
          </p>
          <h2>2. How We Use Your Information</h2>
          <p>
            Your information is used to provide, maintain, and improve our services, including processing applications and communicating with you about your account.
          </p>
          <h2>3. Data Security</h2>
          <p>
            We implement industry-standard security measures to protect your data. However, no communication over the internet is completely secure.
          </p>
        </div>
      </div>
    </div>
  );
}
