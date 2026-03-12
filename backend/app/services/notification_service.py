from app.services.email_service import (
    send_application_received_email, send_rejected_email, 
    send_approved_for_interview_email
)
# Note: Existing email_service.py already has basic functions. I will add more here as needed.

class NotificationService:
    def __init__(self, background_tasks):
        self.background_tasks = background_tasks

    async def notify_interview_scheduled(self, to_email: str, job_title: str, access_key: str):
        """Notify candidate that an interview is scheduled (approved)"""
        self.background_tasks.add_task(send_approved_for_interview_email, to_email, job_title, access_key)

    async def notify_rejection(self, to_email: str, job_title: str):
        """Notify candidate of rejection (Point 9)"""
        self.background_tasks.add_task(send_rejected_email, to_email, job_title, False)

    # Note: Added more specialized enterprise notification logic below
    # These functions will need corresponding email templates in email_service.py
    
    async def notify_offer_released(self, to_email: str, job_title: str):
        """Notify candidate of offer (Point 9)"""
        # Template should be added to email_service.py
        pass

    async def notify_stage_passed(self, to_email: str, stage_name: str, job_title: str):
        """Notify candidate that they moved to the next stage"""
        pass
