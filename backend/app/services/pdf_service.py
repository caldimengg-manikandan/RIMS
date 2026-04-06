from PIL import Image, ImageDraw, ImageFont
import io
import os
import logging
from pypdf import PdfWriter, PdfReader
from datetime import datetime

logger = logging.getLogger(__name__)

def overlay_offer_letter_details(base_pdf_path: str, candidate_name: str, job_title: str, joining_date: datetime):
    """
    Overlays candidate name, job title, and joining date onto the first page of a PDF.
    """
    if not os.path.exists(base_pdf_path):
        raise FileNotFoundError(f"Base PDF not found: {base_pdf_path}")

    # 1. Create overlay image with Pillow
    # Standard Letter size (8.5 x 11 inches) at 72 DPI is 612 x 792 pixels
    # We use a transparent background
    width, height = 612, 792
    img = Image.new('RGBA', (width, height), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    
    # Try to load a font, fallback to default
    font_paths = [
        "C:\\Windows\\Fonts\\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", # Linux fallback
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

    # Format dates
    current_date_str = datetime.now().strftime("%B %d, %Y")
    joining_date_str = joining_date.strftime("%B %d, %Y") if joining_date else "TBD"

    # Draw text at specific coordinates to fill the blanks in the template
    text_color = (10, 10, 10, 255) # Deep black
    
    # 1. Date (Top Right)
    d.text((475, 122), joining_date_str, fill=text_color, font=font)
    
    # 2. To Mr [Name] (Top Left)
    d.text((100, 172), candidate_name, fill=text_color, font=font)
    
    # 3. Dear [Name] (Salutation)
    d.text((100, 272), f"{candidate_name},", fill=text_color, font=font)
    
    # 4. Post of [Job Title] (Body)
    d.text((350, 322), job_title, fill=text_color, font=font)
    
    # 2. Convert image to PDF in-memory
    pdf_buffer = io.BytesIO()
    # Pillow can save RGBA as PDF if we convert to RGB first or just save
    # To maintain transparency merge, we might need a different approach if Pillow PDF isn't transparent
    # But for an overlay, we'll just merge the pages
    img.save(pdf_buffer, format="PDF", resolution=72)
    pdf_buffer.seek(0)
    
    # 3. Merge with base PDF using pypdf
    try:
        base_pdf = PdfReader(base_pdf_path)
        overlay_pdf = PdfReader(pdf_buffer)
        
        writer = PdfWriter()
        
        # Merge overlay onto the first page
        if len(base_pdf.pages) > 0:
            first_page = base_pdf.pages[0]
            first_page.merge_page(overlay_pdf.pages[0])
            
            for page in base_pdf.pages:
                writer.add_page(page)
        
        # Save output - same directory, new filename
        dir_name = os.path.dirname(base_pdf_path)
        base_name = os.path.basename(base_pdf_path)
        name_part, ext_part = os.path.splitext(base_name)
        output_filename = f"{name_part}_formalized{ext_part}"
        output_path = os.path.join(dir_name, output_filename).replace("\\", "/")
        
        with open(output_path, "wb") as f:
            writer.write(f)
            
        return output_path
    except Exception as e:
        logger.error(f"Error in PDF overlay: {e}")
        # If overlay fails, return the original so at least something is sent
        return base_pdf_path
