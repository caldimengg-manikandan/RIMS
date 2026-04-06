import React, { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Send, Mic } from 'lucide-react';

interface AnswerInputProps {
    onSubmit: (answer: string) => void;
    disabled: boolean;
}

export default function AnswerInput({ onSubmit, disabled }: AnswerInputProps) {
    const [text, setText] = useState('');

    const handleSubmit = (e?: React.FormEvent) => {
        e?.preventDefault();
        if (text.trim() && !disabled) {
            onSubmit(text);
            setText('');
        }
    };

    return (
        <Card className="w-full shadow-sm border-t-4 border-t-primary/20">
            <CardContent className="p-4">
                <form onSubmit={handleSubmit} className="flex flex-col space-y-4">
                    <Textarea
                        placeholder={disabled ? "Waiting for the AI..." : "Type your answer here explicitly, or use the microphone to dictate..."}
                        className="min-h-[120px] resize-y text-base p-4"
                        value={text}
                        onChange={(e) => setText(e.target.value)}
                        disabled={disabled}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && e.ctrlKey) {
                                handleSubmit();
                            }
                        }}
                    />
                    <div className="flex justify-between items-center">
                        <div className="text-xs text-muted-foreground flex items-center space-x-2">
                            <span>Press <b>Ctrl + Enter</b> to submit</span>
                        </div>
                        <div className="flex space-x-2">
                            <Button type="button" variant="outline" size="icon" disabled={disabled} title="Speech to Text (Coming soon)">
                                <Mic className="w-4 h-4" />
                            </Button>
                            <Button type="submit" disabled={disabled || !text.trim()} className="px-8">
                                <Send className="w-4 h-4 mr-2" /> Submit
                            </Button>
                        </div>
                    </div>
                </form>
            </CardContent>
        </Card>
    );
}
