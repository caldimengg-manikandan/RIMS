import React, { useState, useRef } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Mic, MicOff, Loader2, Send } from 'lucide-react';
import { toast } from 'sonner';

interface AnswerInputProps {
    onSubmit: (answer: string) => void;
    disabled: boolean;
    isEvaluating?: boolean;
    interviewId?: string;
    isListening?: boolean;
    isTranscribing?: boolean;
    onStartRecording?: (callback: (text: string) => void) => void;
    onStopRecording?: () => void;
}

export default function AnswerInput({
    onSubmit,
    disabled,
    isEvaluating = false,
    interviewId,
    isListening = false,
    isTranscribing = false,
    onStartRecording,
    onStopRecording,
}: AnswerInputProps) {
    const [text, setText] = useState('');

    const handleTranscriptionResult = (transcribedText: string) => {
        setText((prev) => {
            const trimmedPrev = prev.trim();
            return trimmedPrev ? `${trimmedPrev} ${transcribedText}` : transcribedText;
        });
    };

    const handleMicClick = () => {
        if (isListening) {
            onStopRecording?.();
        } else {
            onStartRecording?.(handleTranscriptionResult);
        }
    };

    const handleSubmit = (e?: React.FormEvent) => {
        e?.preventDefault();
        // If user submits while listening, stop it first
        if (isListening) onStopRecording?.();
        
        if (text.trim() && !disabled) {
            onSubmit(text);
            setText('');
        }
    };

    return (
        <Card className="w-full shadow-sm border-t-4 border-t-primary/20 bg-white">
            <CardContent className="p-6">
                <form onSubmit={handleSubmit} className="flex flex-col space-y-4">
                    <Textarea
                        placeholder={isEvaluating ? "AI is processing your answer..." : disabled ? "Waiting for the AI..." : "Type your answer here, or click the mic to speak..."}
                        className="min-h-[150px] resize-y text-lg p-6 bg-slate-50/50 border-slate-200 focus:bg-white transition-all rounded-2xl"
                        value={text}
                        onChange={(e) => setText(e.target.value)}
                        disabled={disabled || isEvaluating}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && e.ctrlKey) {
                                e.preventDefault();
                                handleSubmit();
                            }
                        }}
                    />
                    <div className="flex justify-between items-center">
                        <div className="flex flex-col">
                            <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">
                                {isEvaluating ? (
                                    <span className="text-primary animate-pulse flex items-center gap-1">
                                        <Loader2 className="w-3 h-3 animate-spin" /> AI is thinking...
                                    </span>
                                ) : isListening ? (
                                    <span className="text-red-500 animate-pulse flex items-center gap-1">
                                        <Mic className="w-3 h-3" /> Recording Live...
                                    </span>
                                ) : isTranscribing ? (
                                    <span className="text-blue-500 flex items-center gap-1">
                                        <Loader2 className="w-3 h-3 animate-spin" /> Processing Audio...
                                    </span>
                                ) : (
                                    "Ready to answer"
                                )}
                            </span>
                            <span className="text-[10px] text-slate-400 mt-1">Press <b>Ctrl + Enter</b> to quick-submit</span>
                        </div>
                        <div className="flex items-center gap-3">
                            <Button 
                                type="button" 
                                variant={isListening ? "destructive" : "outline"}
                                size="icon" 
                                disabled={disabled || isTranscribing} 
                                onClick={handleMicClick}
                                title={isListening ? "Stop Recording" : "Start Voice Dictation"}
                                className={`w-12 h-12 rounded-2xl transition-all ${isListening ? "animate-pulse shadow-lg shadow-red-500/20" : "hover:border-blue-500 hover:text-blue-600 shadow-sm"}`}
                            >
                                {isTranscribing ? (
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                ) : isListening ? (
                                    <MicOff className="w-5 h-5" />
                                ) : (
                                    <Mic className="w-5 h-5" />
                                )}
                            </Button>
                            <Button 
                                type="submit" 
                                disabled={disabled || (!text.trim() && !isListening)} 
                                className="h-12 px-8 rounded-2xl shadow-lg shadow-primary/20 font-black text-sm uppercase tracking-widest"
                            >
                                <Send className="w-4 h-4 mr-2" /> Submit Answer
                            </Button>
                        </div>
                    </div>
                </form>
            </CardContent>
        </Card>
    );
}
