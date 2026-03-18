import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Loader2, BrainCircuit } from 'lucide-react';

interface QuestionPanelProps {
    question: { question: string, difficulty: string } | null;
    isLoading: boolean;
}

export default function QuestionPanel({ question, isLoading }: QuestionPanelProps) {

    const getDifficultyColor = (diff: string) => {
        switch (diff) {
            case 'easy': return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300';
            case 'medium': return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300';
            case 'hard': return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    return (
        <Card className="w-full border shadow-sm transition-all duration-300 min-h-[250px] relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 to-purple-500"></div>

            <CardHeader className="pb-3">
                <div className="flex justify-between items-center">
                    <div className="flex items-center space-x-2">
                        <BrainCircuit className="w-6 h-6 text-primary" />
                        <CardTitle className="text-xl">AI Interviewer</CardTitle>
                    </div>
                    {question && (
                        <Badge className={getDifficultyColor(question.difficulty)}>
                            {question.difficulty.toUpperCase()}
                        </Badge>
                    )}
                </div>
            </CardHeader>

            <CardContent className="pt-4 flex flex-col justify-center h-[150px]">
                {isLoading ? (
                    <div className="flex flex-col items-center justify-center space-y-3 opacity-60">
                        <Loader2 className="w-6 h-6 animate-spin" />
                        <p className="animate-pulse">Thinking of the next question...</p>
                    </div>
                ) : (
                    <p className="text-lg md:text-xl font-medium leading-relaxed">
                        {question?.question}
                    </p>
                )}
            </CardContent>
        </Card>
    );
}
