from app.services.scoring_engine.answer_evaluator import AnswerEvaluator
from app.services.skill_graph.skill_updater import SkillUpdater
from app.services.rag_engine.context_builder import ContextBuilder

class AnswerProcessor:
    """
    Processes incoming candidate answers, queries RAG for context,
    runs the Answer Evaluator, and mutates the Skill Graph.
    """
    
    def __init__(self, db_session, session_id: str):
        self.db = db_session
        self.session_id = session_id
        self.evaluator = AnswerEvaluator(session_id)
        self.skill_updater = SkillUpdater(db_session, session_id)
        self.context_builder = ContextBuilder(session_id)

    def process_answer(self, question: dict, candidate_answer: str) -> dict:
        """
        Full orchestration of answer scoring and graph updating.
        """
        # 1. Get RAG Ground Truth Context
        context = self.context_builder.get_interview_context(question.get("domain", "General"))
        
        # 2. Evaluate the answer using the LLM
        evaluation = self.evaluator.evaluate(question.get("text", ""), candidate_answer, context)
        
        # 3. Update candidate's skill graph dynamically
        self.skill_updater.update_skill(
            skill_name=question.get("domain", "General Skill"),
            answer_score=evaluation.get("technical_score", 0.0),
            difficulty=question.get("difficulty", "medium")
        )
        
        return evaluation
