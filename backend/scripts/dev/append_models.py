import os

models_path = os.path.join('d:', '\\Caldim', 'RIMS-main', 'RIMS-main', 'backend', 'app', 'domain', 'models.py')

new_models = """

class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey('jobs.id', ondelete='CASCADE'), nullable=False, index=True)
    application_id = Column(Integer, ForeignKey('applications.id', ondelete='CASCADE'), nullable=True, index=True)
    start_time = Column(DateTime(timezone=True), default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), default='pending', index=True)  # 'pending', 'active', 'completed', 'aborted'
    final_score = Column(Float, nullable=True)
    difficulty_level = Column(String(50), default='medium')

    # Relationships
    events = relationship("InterviewEvent", back_populates="session", cascade="all, delete-orphan")


class InterviewEvent(Base):
    __tablename__ = "interview_events"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey('interview_sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)  # 'question_asked', 'answer_received', 'ai_evaluated', 'status_changed'
    payload = Column(Text, nullable=True)  # JSON serialized data
    created_at = Column(DateTime(timezone=True), default=func.now(), index=True)

    # Relationships
    session = relationship("InterviewSession", back_populates="events")


class QuestionBank(Base):
    __tablename__ = "question_bank"

    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String(100), index=True)  # e.g. 'Engineering', 'Sales'
    role = Column(String(100), index=True)    # e.g. 'Frontend', 'Backend'
    difficulty = Column(String(50), index=True) # 'easy', 'medium', 'hard'
    question_text = Column(Text, nullable=False)
    expected_key_points = Column(Text) # JSON array of points
    created_at = Column(DateTime(timezone=True), default=func.now())


class CandidateSkill(Base):
    __tablename__ = "candidate_skills"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey('applications.id', ondelete='CASCADE'), nullable=False, index=True)
    skill_name = Column(String(100), nullable=False, index=True)
    proficiency_score = Column(Float, nullable=True) # 0-10 based on AI analysis
    years_experience = Column(Float, nullable=True)


class AIEvaluation(Base):
    __tablename__ = "ai_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    answer_id = Column(Integer, ForeignKey('interview_answers.id', ondelete='CASCADE'), nullable=False, index=True)
    technical_score = Column(Float)
    communication_score = Column(Float)
    reasoning_score = Column(Float)
    feedback_text = Column(Text)
    created_at = Column(DateTime(timezone=True), default=func.now())
"""

with open(models_path, 'a', encoding='utf-8') as f:
    f.write(new_models)

print("Successfully appended new models to models.py")
