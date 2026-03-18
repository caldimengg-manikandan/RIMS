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
import { Textarea } from "@/components/ui/textarea"
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import { AlertTriangle } from 'lucide-react'

interface RejectDialogProps {
    candidateName: string;
    onConfirm: (reason: string, notes: string) => Promise<void>;
    trigger: React.ReactNode;
}

const REJECTION_REASONS = [
    "Not a good fit",
    "Lacks required experience",
    "Missing required technical skills",
    "Salary expectations too high",
    "Position filled",
    "Other"
];

export function RejectDialog({ candidateName, onConfirm, trigger }: RejectDialogProps) {
    const [open, setOpen] = useState(false);
    const [reason, setReason] = useState<string>("");
    const [notes, setNotes] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleConfirm = async () => {
        if (!reason) {
            alert("Please select a reason for rejection.");
            return;
        }

        setIsSubmitting(true);
        try {
            await onConfirm(reason, notes);
            setOpen(false);
            // Reset state
            setReason("");
            setNotes("");
        } catch (error) {
            console.error("Failed to reject candidate:", error);
            alert("Failed to reject candidate. Please try again.");
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleOpenChange = (newOpen: boolean) => {
        if (!newOpen && isSubmitting) return; // Prevent closing while submitting
        setOpen(newOpen);
        if (!newOpen) {
            // Reset state on close
            setReason("");
            setNotes("");
        }
    };

    return (
        <Dialog open={open} onOpenChange={handleOpenChange}>
            <DialogTrigger asChild>
                {trigger}
            </DialogTrigger>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2 text-destructive font-bold text-xl">
                        <AlertTriangle className="h-5 w-5" />
                        Confirm Rejection
                    </DialogTitle>
                    <DialogDescription className="text-[0.95rem] pt-2 text-foreground leading-relaxed">
                        Are you sure you want to reject <strong className="font-bold text-primary">{candidateName}</strong>? This action is permanent and will notify the candidate.
                    </DialogDescription>
                </DialogHeader>

                <div className="grid gap-4 py-4">
                    <div className="grid gap-2">
                        <Label htmlFor="reason" className="font-semibold">
                            Reason for Rejection <span className="text-destructive">*</span>
                        </Label>
                        <Select value={reason} onValueChange={setReason}>
                            <SelectTrigger id="reason" className={!reason ? "text-muted-foreground" : ""}>
                                <SelectValue placeholder="Select a reason..." />
                            </SelectTrigger>
                            <SelectContent>
                                {REJECTION_REASONS.map((r) => (
                                    <SelectItem key={r} value={r}>
                                        {r}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="grid gap-2">
                        <Label htmlFor="notes" className="font-semibold">
                            Additional Notes <span className="text-muted-foreground font-normal">(optional)</span>
                        </Label>
                        <Textarea
                            id="notes"
                            placeholder="Add any additional notes or context..."
                            className="resize-none h-24"
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
                        variant="destructive"
                        onClick={handleConfirm}
                        disabled={isSubmitting || !reason}
                        className="min-w-[120px]"
                    >
                        {isSubmitting ? "Rejecting..." : "Confirm Rejection"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    )
} 
