import React, { useState } from 'react'
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { CheckCircle, Calendar, FileText } from 'lucide-react'

interface HireDialogProps {
    candidateName: string;
    onConfirm: (joiningDate: string, offerLetter: File, notes: string) => Promise<void>;
    trigger: React.ReactNode;
}

export function HireDialog({ candidateName, onConfirm, trigger }: HireDialogProps) {
    const [open, setOpen] = useState(false);
    const [joiningDate, setJoiningDate] = useState("");
    const [offerLetter, setOfferLetter] = useState<File | null>(null);
    const [notes, setNotes] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setOfferLetter(e.target.files[0]);
        }
    };

    const handleConfirm = async () => {
        if (!joiningDate) {
            alert("Please select a joining date.");
            return;
        }
        if (!offerLetter) {
            alert("Please upload an offer letter (PDF).");
            return;
        }

        setIsSubmitting(true);
        try {
            await onConfirm(joiningDate, offerLetter, notes);
            setOpen(false);
            // Reset state
            setJoiningDate("");
            setOfferLetter(null);
            setNotes("");
        } catch (error) {
            console.error("Failed to hire candidate:", error);
            alert("Failed to hire candidate. Please try again.");
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleOpenChange = (newOpen: boolean) => {
        if (!newOpen && isSubmitting) return; 
        setOpen(newOpen);
        if (!newOpen) {
            setJoiningDate("");
            setOfferLetter(null);
            setNotes("");
        }
    };

    return (
        <Dialog open={open} onOpenChange={handleOpenChange}>
            <DialogTrigger asChild>
                {trigger}
            </DialogTrigger>
            <DialogContent className="sm:max-w-[450px]">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2 text-emerald-600 font-bold text-xl">
                        <CheckCircle className="h-5 w-5" />
                        Hire Candidate
                    </DialogTitle>
                    <DialogDescription className="text-[0.95rem] pt-2 text-foreground leading-relaxed">
                        Complete the formal hiring process for <strong className="font-bold text-primary">{candidateName}</strong>. 
                        The details will be overlaid onto the offer letter and emailed to the candidate.
                    </DialogDescription>
                </DialogHeader>

                <div className="grid gap-5 py-4">
                    <div className="grid gap-2">
                        <Label htmlFor="joiningDate" className="font-semibold flex items-center gap-2">
                            <Calendar className="h-4 w-4 text-emerald-600" />
                            Expected Joining Date <span className="text-destructive">*</span>
                        </Label>
                        <Input 
                            id="joiningDate" 
                            type="date" 
                            className="w-full"
                            value={joiningDate}
                            onChange={(e) => setJoiningDate(e.target.value)}
                        />
                    </div>

                    <div className="grid gap-2">
                        <Label htmlFor="offerLetter" className="font-semibold flex items-center gap-2">
                            <FileText className="h-4 w-4 text-emerald-600" />
                            Offer Letter Template (PDF) <span className="text-destructive">*</span>
                        </Label>
                        <Input 
                            id="offerLetter" 
                            type="file" 
                            accept=".pdf"
                            className="w-full cursor-pointer"
                            onChange={handleFileChange}
                        />
                        <p className="text-xs text-muted-foreground italic">
                            System will overlay Candidate Name, Role, and Date on the first page.
                        </p>
                    </div>

                    <div className="grid gap-2">
                        <Label htmlFor="notes" className="font-semibold">
                            Onboarding Notes <span className="text-muted-foreground font-normal">(optional)</span>
                        </Label>
                        <Textarea
                            id="notes"
                            placeholder="Add any specific onboarding instructions..."
                            className="resize-none h-20"
                            value={notes}
                            onChange={(e) => setNotes(e.target.value)}
                        />
                    </div>
                </div>

                <DialogFooter className="gap-2 sm:gap-0 mt-2">
                    <Button
                        type="button"
                        variant="outline"
                        onClick={() => handleOpenChange(false)}
                        disabled={isSubmitting}
                    >
                        Cancel
                    </Button>
                    <Button
                        type="button"
                        onClick={handleConfirm}
                        disabled={isSubmitting || !joiningDate || !offerLetter}
                        className="bg-emerald-600 hover:bg-emerald-700 text-white min-w-[140px]"
                    >
                        {isSubmitting ? "Processing..." : "Confirm & Send"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    )
} 
