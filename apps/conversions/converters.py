import os
import tempfile
import platform
import traceback

# Import libraries with safety
try:
    from PyPDF2 import PdfReader
    from pdf2docx import Converter
    from docx import Document
    from PIL import Image
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    import openpyxl
    from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
except ImportError as e:
    print(f"⚠️ Missing library: {e}")

class FileConverter:
    CONVERTERS = {}
    
    @classmethod
    def register_converter(cls, conversion_type):
        def decorator(func):
            cls.CONVERTERS[conversion_type] = func
            return func
        return decorator
    
    @staticmethod
    def _create_temp_output(extension=''):
        """Create temp file path without pre-creating the file to avoid 'File in use' errors"""
        suffix = extension if extension.startswith('.') else f'.{extension}'
        fd, path = tempfile.mkstemp(suffix=suffix)
        os.close(fd) # Close handle immediately so libraries can write to it
        return path

    @classmethod
    def convert_file(cls, conversion_type, input_path):
        """Main conversion engine"""
        converter = cls.CONVERTERS.get(conversion_type)
        if not converter:
            return False, None, f"Unsupported conversion: {conversion_type}"
        
        if not os.path.exists(input_path):
            return False, None, "Source file not found on server."

        # Map extensions
        ext_map = {
            'pdf_to_word': '.docx', 'word_to_pdf': '.pdf',
            'pdf_to_excel': '.xlsx', 'excel_to_pdf': '.pdf',
            'pdf_to_image': '.png', 'image_to_pdf': '.pdf',
        }
        
        output_path = cls._create_temp_output(ext_map.get(conversion_type, '.tmp'))
        
        try:
            success, message = converter(input_path, output_path)
            
            if success and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                with open(output_path, 'rb') as f:
                    content = f.read()
                
                # Cleanup temp file
                if os.path.exists(output_path):
                    os.unlink(output_path)
                return True, content, message
            else:
                return False, None, message or "Conversion produced empty output."
                
        except Exception as e:
            traceback.print_exc()
            return False, None, f"Converter Error: {str(e)}"

# ============================================================================
# INDIVIDUAL CONVERTERS (FIXED)
# ============================================================================

@FileConverter.register_converter('pdf_to_word')
def pdf_to_word(input_path, output_path):
    try:
        cv = Converter(input_path)
        cv.convert(output_path, start=0, end=None)
        cv.close()
        return True, "Success"
    except Exception as e:
        return False, str(e)

@FileConverter.register_converter('word_to_pdf')
def word_to_pdf(input_path, output_path):
    """Headless-safe Word to PDF"""
    # Try docx2pdf first as it handles the Word instance better
    try:
        from docx2pdf import convert
        convert(input_path, output_path)
        return True, "Success via docx2pdf"
    except Exception:
        # Fallback to Manual ReportLab (already in your code)
        return manual_word_to_pdf_logic(input_path, output_path)

def manual_word_to_pdf_logic(input_path, output_path):
    """Your existing ReportLab logic wrapped as a safe fallback"""
    try:
        doc = Document(input_path)
        pdf_doc = SimpleDocTemplate(output_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        for para in doc.paragraphs:
            if para.text.strip():
                clean_text = para.text.encode('ascii', 'ignore').decode('ascii')
                story.append(Paragraph(clean_text, styles['Normal']))
                story.append(Spacer(1, 0.1*inch))
        pdf_doc.build(story)
        return True, "Success (Basic Formatting)"
    except Exception as e:
        return False, f"Manual fallback failed: {str(e)}"

@FileConverter.register_converter('pdf_to_excel')
def pdf_to_excel(input_path, output_path):
    try:
        reader = PdfReader(input_path)
        wb = openpyxl.Workbook()
        ws = wb.active
        for page in reader.pages:
            text = page.extract_text()
            for line in text.split('\n'):
                if line.strip():
                    ws.append(line.split())
        wb.save(output_path)
        return True, "Success"
    except Exception as e:
        return False, str(e)

@FileConverter.register_converter('pdf_to_image')
def pdf_to_image(input_path, output_path):
    try:
        import fitz # PyMuPDF
        doc = fitz.open(input_path)
        page = doc[0] # Convert first page
        pix = page.get_pixmap()
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        img.save(output_path, "PNG")
        doc.close()
        return True, "Success"
    except Exception as e:
        return False, str(e)

@FileConverter.register_converter('image_to_pdf')
def image_to_pdf(input_path, output_path):
    try:
        img = Image.open(input_path).convert('RGB')
        img.save(output_path, "PDF", resolution=100.0)
        return True, "Success"
    except Exception as e:
        return False, str(e)

@FileConverter.register_converter('excel_to_pdf')
def excel_to_pdf(input_path, output_path):
    try:
        wb = openpyxl.load_workbook(input_path, data_only=True)
        sheet = wb.active
        pdf_doc = SimpleDocTemplate(output_path, pagesize=A4)
        data = []
        for row in sheet.iter_rows(values_only=True):
            data.append([str(c) if c is not None else "" for c in row])
        
        table = Table(data)
        table.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
        pdf_doc.build([table])
        return True, "Success"
    except Exception as e:
        return False, str(e)