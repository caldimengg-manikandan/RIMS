'use client'

import React, { useRef, useState, useCallback } from 'react'
import Webcam from 'react-webcam'
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
    DialogFooter
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Camera, RefreshCw, Check, X } from 'lucide-react'
import { APIClient } from '@/app/dashboard/lib/api-client'
import { useToast } from "@/components/ui/use-toast"

interface CapturePhotoDialogProps {
    isOpen: boolean
    onOpenChange: (open: boolean) => void
    applicationId: number
    onSuccess: () => void
}

export function CapturePhotoDialog({ isOpen, onOpenChange, applicationId, onSuccess }: CapturePhotoDialogProps) {
    const webcamRef = useRef<Webcam>(null)
    const [imgSrc, setImgSrc] = useState<string | null>(null)
    const [isUploading, setIsUploading] = useState(false)
    const { toast } = useToast()

    const capture = useCallback(() => {
        const imageSrc = webcamRef.current?.getScreenshot()
        setImgSrc(imageSrc || null)
    }, [webcamRef])

    const retake = () => {
        setImgSrc(null)
    }

    const uploadPhoto = async () => {
        if (!imgSrc) return
        
        setIsUploading(true)
        try {
            // Convert base64 to blob
            const response = await fetch(imgSrc)
            const blob = await response.blob()
            
            const formData = new FormData()
            formData.append('photo', blob, 'capture.jpg')

            await APIClient.postFormData(`/api/onboarding/applications/${applicationId}/capture-photo`, formData)

            toast({ title: "Success", description: "Photo captured and uploaded" })
            onSuccess()
            onOpenChange(false)
            setImgSrc(null)
        } catch (error) {
            toast({ title: "Error", description: "Failed to upload photo", variant: "destructive" })
        } finally {
            setIsUploading(false)
        }
    }

    return (
        <Dialog open={isOpen} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-md">
                <DialogHeader>
                    <DialogTitle>Capture Candidate Photo</DialogTitle>
                    <DialogDescription>
                        Take a clear photo of the candidate for their ID card.
                    </DialogDescription>
                </DialogHeader>
                
                <div className="flex flex-col items-center justify-center bg-slate-900 rounded-xl overflow-hidden aspect-video relative">
                    {!imgSrc ? (
                        <>
                            <Webcam
                                audio={false}
                                ref={webcamRef}
                                screenshotFormat="image/jpeg"
                                className="w-full h-full object-cover"
                                videoConstraints={{ facingMode: "user" }}
                            />
                            <div className="absolute bottom-4 left-1/2 -translate-x-1/2">
                                <Button onClick={capture} variant="secondary" className="rounded-full h-12 w-12 p-0 bg-white/20 hover:bg-white/40 backdrop-blur-md border-white/50 border">
                                    <Camera className="h-6 w-6 text-white" />
                                </Button>
                            </div>
                        </>
                    ) : (
                        <>
                            <img src={imgSrc} className="w-full h-full object-cover" alt="Captured" />
                            <div className="absolute inset-0 bg-black/40 flex items-center justify-center gap-4 opacity-0 hover:opacity-100 transition-opacity">
                                <Button onClick={retake} variant="outline" className="bg-white/10 text-white border-white/20">
                                    <RefreshCw className="h-4 w-4 mr-2" />
                                    Retake
                                </Button>
                            </div>
                        </>
                    )}
                </div>

                <DialogFooter className="sm:justify-between">
                    <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
                    {imgSrc && (
                        <Button 
                            onClick={uploadPhoto} 
                            disabled={isUploading}
                            className="bg-emerald-600 hover:bg-emerald-700 font-bold"
                        >
                            {isUploading ? "Uploading..." : "Save Photo"}
                            {!isUploading && <Check className="ml-2 h-4 w-4" />}
                        </Button>
                    )}
                </DialogFooter>
            </DialogContent>
        </Dialog>
    )
}
