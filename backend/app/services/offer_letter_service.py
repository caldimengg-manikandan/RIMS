import os
import io
from jinja2 import Template
from xhtml2pdf import pisa
from datetime import datetime
from app.core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

def generate_offer_letter_pdf(template_html: str, data: dict, output_path: str):
    """
    Generates a PDF from an HTML template string and data dictionary.
    Writes result to output_path on disk.
    """
    try:
        template = Template(template_html)
        rendered_html = template.render(**data)
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, "wb") as result_file:
            pisa_status = pisa.CreatePDF(rendered_html, dest=result_file)
            
        if pisa_status.err:
            logger.error(f"Error generating PDF: {pisa_status.err}")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Failed to generate offer letter PDF: {e}")
        return False


def generate_offer_letter_pdf_bytes(template_html: str, data: dict) -> bytes:
    """
    Renders the Jinja2 HTML template with the given data and converts it to a
    PDF entirely in-memory using xhtml2pdf/pisa.

    Returns the raw PDF bytes on success.
    Raises RuntimeError if the PDF engine reports errors.
    """
    template = Template(template_html)
    rendered_html = template.render(**data)

    buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(rendered_html, dest=buffer)

    if pisa_status.err:
        raise RuntimeError(f"xhtml2pdf reported errors while generating offer letter PDF: {pisa_status.err}")

    return buffer.getvalue()

def get_offer_letter_data(candidate_name, job_role, department, joining_date, company_name, logo_url, hr_email, hr_name="", hr_phone="", company_address=""):
    """ Helper to structure offer letter data """
    return {
        "candidate_name": candidate_name,
        "job_role": job_role,
        "department": department,
        "joining_date": joining_date.strftime("%B %d, %Y") if joining_date else "TBD",
        "company_name": company_name,
        "logo": logo_url,       # legacy compat
        "logo_url": logo_url,   # new template variable
        "hr_email": hr_email,
        "hr_name": hr_name,
        "hr_phone": hr_phone,
        "company_address": company_address,
        "offer_date": datetime.now().strftime("%B %d, %Y")
    }
