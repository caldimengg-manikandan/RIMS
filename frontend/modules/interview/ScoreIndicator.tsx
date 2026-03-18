import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Brain, Sparkles, TrendingUp, AlertTriangle } from 'lucide-react';

interface ScoreIndicatorProps {
    feedback: { score: number, text: string } | null;
    currentDifficulty?: string;
}

export default function ScoreIndicator({ feedback, currentDifficulty }: ScoreIndicatorProps) {

    if (!feedback) {
        return (
            <Card className="bg-primary/5 border-primary/20 text-center py-8">
                <CardContent className="flex flex-col items-center justify-center space-y-4">
                    <Brain className="w-12 h-12 text-primary opacity-50" />
                    <div className="space-y-1">
                        <p className="font-semibold">AI is Listening</p>
                        <p className="text-sm text-muted-foreground">Answer the question to receive real-time evaluation.</p>
                    </div>
                </CardContent>
            </Card>
        );
    }

    const scorePercentage = (feedback.score / 10) * 100;

    const getScoreColor = (score: number) => {
        if (score >= 8) return 'text-green-500';
        if (score >= 5) return 'text-yellow-500';
        return 'text-red-500';
    };

    const getScoreIcon = (score: number) => {
        if (score >= 8) return <Sparkles className="w-8 h-8 text-green-500" />;
        if (score >= 5) return <TrendingUp className="w-8 h-8 text-yellow-500" />;
        return <AlertTriangle className="w-8 h-8 text-red-500" />;
    };

    return (
        <Card className="overflow-hidden border-border bg-card shadow-md animate-in fade-in slide-in-from-bottom-4 duration-500">
            <CardHeader className="bg-muted/50 pb-4">
                <CardTitle className="flex justify-between items-center text-lg">
                    <span>Real-time Evaluation</span>
                    {getScoreIcon(feedback.score)}
                </CardTitle>
            </CardHeader>

            <CardContent className="pt-6 space-y-6">
                <div className="space-y-2">
                    <div className="flex justify-between text-sm font-medium">
                        <span>Technical Score</span>
                        <span className={getScoreColor(feedback.score)}>{feedback.score}/10</span>
                    </div>
                    <Progress value={scorePercentage} className="h-2" />
                </div>

                <div className="bg-secondary/40 p-4 rounded-lg text-sm border border-secondary">
                    <strong className="block mb-2 text-foreground/80">AI Feedback:</strong>
                    <p className="text-muted-foreground leading-relaxed">{feedback.text}</p>
                </div>
            </CardContent>
        </Card>
    );
}
