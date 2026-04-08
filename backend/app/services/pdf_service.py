import io
import logging
from pypdf import PdfWriter, PdfReader
from datetime import datetime

logger = logging.getLogger(__name__)

def overlay_offer_letter_details(base_pdf_content: bytes, candidate_name: str, job_title: str, joining_date: datetime) -> bytes:
    """
    Overlays candidate name, job title, and joining date onto the first page of a PDF.
    Returns the final PDF content as bytes.
    """
    from PIL import Image, ImageDraw, ImageFont
    import os
    
    # 1. Create overlay image with Pillow (transparent background)
    width, height = 612, 792
    img = Image.new('RGBA', (width, height), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    
    # Try to load a font, fallback to default
    font_paths = [
        "C:\\Windows\\Fonts\\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "arial.ttf"
    ]
    
    font = None
    for path in font_paths:
        try:
            if os.path.exists(path) or path == "arial.ttf":
                font = ImageFont.truetype(path, 14)
                break
        except:
            continue
            
    if font is None:
        font = ImageFont.load_default()

    joining_date_str = joining_date.strftime("%B %d, %Y") if joining_date else "TBD"
    text_color = (10, 10, 10, 255) # Deep black
    
    # Coordinates matched to the corporate offer template
    d.text((475, 122), joining_date_str, fill=text_color, font=font)
    d.text((100, 172), candidate_name, fill=text_color, font=font)
    d.text((100, 272), f"{candidate_name},", fill=text_color, font=font)
    d.text((350, 322), job_title, fill=text_color, font=font)
    
    # 2. Convert image to PDF in-memory
    pdf_buffer = io.BytesIO()
    img.save(pdf_buffer, format="PDF", resolution=72)
    pdf_buffer.seek(0)
    
    # 3. Merge with base PDF using pypdf (In-memory)
    try:
        base_pdf = PdfReader(io.BytesIO(base_pdf_content))
        overlay_pdf = PdfReader(pdf_buffer)
        
        writer = PdfWriter()
        
        # Merge overlay onto the first page
        if len(base_pdf.pages) > 0:
            first_page = base_pdf.pages[0]
            first_page.merge_page(overlay_pdf.pages[0])
            
            for page in base_pdf.pages:
                writer.add_page(page)
        
        output_buffer = io.BytesIO()
        writer.write(output_buffer)
        return output_buffer.getvalue()
    except Exception as e:
        logger.error(f"Error in PDF overlay: {e}")
        # If overlay fails, return the original content so process continues
        return base_pdf_content
