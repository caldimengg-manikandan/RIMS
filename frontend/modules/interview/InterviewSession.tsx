'use client';

import React, { useState, useEffect, useRef } from 'react';
import QuestionPanel from './QuestionPanel';
import AnswerInput from './AnswerInput';
import ScoreIndicator from './ScoreIndicator';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Loader2 } from 'lucide-react';

interface InterviewSessionProps {
  sessionId: string;
  token: string;
}

export default function InterviewSession({ sessionId, token }: InterviewSessionProps) {
  const [isConnected, setIsConnected] = useState(false);
  const [isFinished, setIsFinished] = useState(false);
  const [currentQuestion, setCurrentQuestion] = useState<{question: string, difficulty: string} | null>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [latestFeedback, setLatestFeedback] = useState<{score: number, text: string} | null>(null);
  
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Determine WS protocol
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // Use localhost:8000 for local dev if window.location isn't the backend
    const host = process.env.NEXT_PUBLIC_API_URL ? new URL(process.env.NEXT_PUBLIC_API_URL).host : 'localhost:8000';
    const wsUrl = `${protocol}//${host}/ws/interview/${sessionId}?token=${token}`;
    
    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => {
      setIsConnected(true);
      console.log("WebSocket connected");
    };

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log("WS Message received:", data);
      
      switch(data.type) {
        case 'question':
          setCurrentQuestion({ question: data.question, difficulty: data.difficulty });
          setLatestFeedback(null); // Clear feedback when new question arrives
          break;
        case 'evaluation':
          setLatestFeedback({ score: data.score, text: data.feedback });
          break;
        case 'system':
          setMessages(prev => [...prev, { text: data.message, type: 'system' }]);
          break;
        case 'end':
          setIsFinished(true);
          ws.current?.close();
          break;
        case 'error':
          setMessages(prev => [...prev, { text: data.message, type: 'error' }]);
          break;
      }
    };

    ws.current.onclose = () => {
      setIsConnected(false);
      console.log("WebSocket disconnected");
    };

    return () => {
      ws.current?.close();
    };
  }, [sessionId, token]);

  const handleSubmitAnswer = (answerText: string) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({
        action: 'submit_answer',
        answer: answerText
      }));
    }
  };

  if (!isConnected && !isFinished) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
        <h2 className="text-xl font-semibold">Connecting to AI Interview Engine...</h2>
      </div>
    );
  }

  if (isFinished) {
    return (
      <Card className="max-w-3xl mx-auto mt-12 bg-card border-primary/20 shadow-lg">
        <CardHeader>
          <CardTitle className="text-center text-3xl text-primary">Interview Complete</CardTitle>
        </CardHeader>
        <CardContent className="text-center space-y-6">
          <p className="text-lg text-muted-foreground">Thank you for completing the interview. The AI is generating your comprehensive profile.</p>
          <Button onClick={() => window.location.href = '/dashboard/candidate'}>Return to Dashboard</Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-6 p-4">
      
      {/* Main Interview Area */}
      <div className="md:col-span-2 space-y-6">
        <QuestionPanel question={currentQuestion} isLoading={!currentQuestion} />
        
        <AnswerInput 
          onSubmit={handleSubmitAnswer} 
          disabled={!currentQuestion || latestFeedback !== null}
        />
      </div>

      {/* Sidebar / HUD */}
      <div className="space-y-6">
        <ScoreIndicator feedback={latestFeedback} currentDifficulty={currentQuestion?.difficulty} />
        
        <Card className="bg-muted/30">
          <CardHeader>
            <CardTitle className="text-sm">Session Log</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 h-64 overflow-y-auto text-sm">
            {messages.map((m, idx) => (
              <div key={idx} className={`p-2 rounded ${m.type === 'error' ? 'bg-destructive/10 text-destructive' : 'bg-secondary/50 text-secondary-foreground'}`}>
                {m.text}
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

    </div>
  );
}
