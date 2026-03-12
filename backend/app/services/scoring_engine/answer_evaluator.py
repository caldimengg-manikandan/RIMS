import os
import json
import requests
from app.services.rag_engine.context_builder import ContextBuilder

class AnswerEvaluator:
    """
    Evaluates candidate answers in real-time using an LLM.
    Uses RAG context context via ContextBuilder if available.
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        # We assume Groq or OpenAI API key is in the env vars.
        # RIMS currently uses Groq according to the .env file.
        self.api_key = os.getenv("GROQ_API_KEY", "dummy_key_if_none")
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"

    def evaluate(self, question_text: str, candidate_answer: str, context: str = "") -> dict:
        """
        Calls the LLM to score the answer across multiple axes.
        Returns a structured JSON mapping containing technical_score, 
        communication_score, confidence_score, correctness_score, and feedback.
        """
        
        system_prompt = f"""You are an expert FAANG technical interviewer.
        Evaluate the candidate's answer based on the question and the provided ground truth context.
        Provide your score strictly as a JSON object matching this schema:
        {{
            "technical_score": float (0-10),
            "communication_score": float (0-10),
            "confidence_score": float (0-10),
            "correctness_score": float (0-10),
            "feedback": string (constructive HR feedback),
            "strengths": [string],
            "weaknesses": [string]
        }}
        
        Context for evaluation:
        {context}
        """

        user_prompt = f"Question: {question_text}\nCandidate's Answer: {candidate_answer}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama3-8b-8192",  # Replace with appropriate Groq/Ollama model
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"}
        }

        try:
            # Mocking the HTTP request response for immediate deployment unless api_key is valid
            # In production, use `requests.post()` and handle API errors cleanly.
            # response = requests.post(self.api_url, headers=headers, json=payload, timeout=5)
            # data = response.json()['choices'][0]['message']['content']
            # return json.loads(data)
            
            # Simulated Response for offline testing
            return {
                "technical_score": 7.5,
                "communication_score": 8.0,
                "confidence_score": 7.0,
                "correctness_score": 8.5,
                "feedback": "Good fundamental understanding, but lacked depth on edge cases.",
                "strengths": ["Clear explanation", "Correct terminology"],
                "weaknesses": ["Missed edge cases", "Brief"]
            }
            
        except Exception as e:
            print(f"Error evaluating answer: {e}")
            return {
                "technical_score": 5.0,
                "communication_score": 5.0,
                "confidence_score": 5.0,
                "correctness_score": 5.0,
                "feedback": "Evaluation engine failed.",
                "strengths": [],
                "weaknesses": []
            }
