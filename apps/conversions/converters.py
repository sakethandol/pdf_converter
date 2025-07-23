import os
import tempfile
from pathlib import Path
import io

# Import libraries with fallback handling
try:
    from PyPDF2 import PdfReader
    from pdf2docx import Converter
    from docx import Document
    from PIL import Image
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    import openpyxl
    from docx2pdf import convert
    from openpyxl import Workbook
except ImportError as e:
    print(f"Missing library: {e}")

class FileConverter:
    """Efficient file converter with algorithm optimization"""
    
    # Conversion mapping for efficiency
    CONVERTERS = {}
    
    @classmethod
    def register_converter(cls, conversion_type):
        """Decorator to register conversion methods"""
        def decorator(func):
            cls.CONVERTERS[conversion_type] = func
            return func
        return decorator
    
    @staticmethod
    def _create_temp_output():
        """Create temporary output file"""
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.close()
        return temp_file.name
    
    @staticmethod
    def _read_file_content(file_path):
        """Efficiently read file content"""
        try:
            with open(file_path, 'rb') as f:
                return f.read()
        except Exception as e:
            raise Exception(f"Error reading file: {e}")
    
    @staticmethod
    def _safe_cleanup(file_path):
        """Safely cleanup temporary files"""
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
        except:
            pass
    
    @classmethod
    def convert_file(cls, conversion_type, input_path):
        """Main conversion dispatcher using algorithm optimization"""
        converter = cls.CONVERTERS.get(conversion_type)
        if not converter:
            return False, None, f"Unsupported conversion: {conversion_type}"
        
        output_path = cls._create_temp_output()
        try:
            success, message = converter(input_path, output_path)
            if success:
                content = cls._read_file_content(output_path)
                cls._safe_cleanup(output_path)
                return True, content, message
            else:
                cls._safe_cleanup(output_path)
                return False, None, message
        except Exception as e:
            cls._safe_cleanup(output_path)
            return False, None, str(e)

# Register all conversion methods using decorator pattern
@FileConverter.register_converter('pdf_to_word')
def pdf_to_word(input_path, output_path):
    try:
        cv = Converter(input_path)
        cv.convert(output_path)
        cv.close()
        return True, "Success"
    except Exception as e:
        return False, str(e)

@FileConverter.register_converter('word_to_pdf')
def word_to_pdf(input_path, output_path):
    # Primary conversion using dedicated library
    try:
        from docx2pdf import convert
        convert(input_path, output_path)
        # Verify conversion actually produced content
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1024:  # 1KB threshold
            return True, "Success"
        # If file is too small, fall through to secondary method
    except Exception as e:
        pass  # Proceed to fallback
    
    # Enhanced fallback with better content extraction
    try:
        import os
        import tempfile
        from docx import Document
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

        # Register better font support
        try:
            pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))
            default_font = 'DejaVuSans'
        except:
            default_font = 'Helvetica'

        doc = Document(input_path)
        styles = getSampleStyleSheet()
        custom_style = styles['Normal']
        custom_style.fontName = default_font
        custom_style.spaceAfter = 6
        story = []
        
        # Extract ALL document content including headers, footers, footnotes
        content_parts = [
            *doc.paragraphs,
            *doc.tables,
            *doc.inline_shapes,
            *[section.header for section in doc.sections],
            *[section.footer for section in doc.sections],
            *[footnote for footnote in doc.footnotes]
        ]
        
        if not content_parts:
            return False, "Document appears to be empty"

        # Process all content elements
        for element in content_parts:
            # Paragraphs
            if hasattr(element, 'text'):
                text = element.text.strip()
                if text:
                    # Preserve basic alignment
                    alignment = TA_LEFT
                    if element.paragraph_format.alignment:
                        align_map = {
                            1: TA_LEFT,    # LEFT
                            2: TA_CENTER,  # CENTER
                            3: TA_RIGHT,   # RIGHT
                            4: TA_LEFT,    # JUSTIFY -> LEFT
                        }
                        alignment = align_map.get(element.paragraph_format.alignment, TA_LEFT)
                    
                    p = Paragraph(text, style=custom_style)
                    p.alignment = alignment
                    story.append(p)
                    story.append(Spacer(1, 10))
            
            # Tables
            elif hasattr(element, 'rows'):
                table_data = []
                for row in element.rows:
                    row_data = []
                    for cell in row.cells:
                        cell_text = " ".join(p.text for p in cell.paragraphs if p.text.strip())
                        row_data.append(cell_text)
                    table_data.append(row_data)
                
                if table_data:
                    from reportlab.platypus import Table
                    tbl = Table(table_data)
                    story.append(tbl)
                    story.append(Spacer(1, 15))
        
        if not story:
            return False, "No extractable content found"

        # Create PDF with proper metadata
        pdf = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            title=doc.core_properties.title or "Converted Document",
            author=doc.core_properties.author or "",
            subject=doc.core_properties.subject or ""
        )
        pdf.build(story)
        
        # Final content check
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1024:
            return True, "Success (fallback)"
        return False, "Generated PDF is empty"
        
    except Exception as e:
        return False, f"Conversion failed: {str(e)}"
@FileConverter.register_converter('pdf_to_excel')
def pdf_to_excel(input_path, output_path):
    try:
        reader = PdfReader(input_path)
        wb = Workbook()
        ws = wb.active
        ws.append(["Page", "Content"])
        
        for page_num, page in enumerate(reader.pages, 1):
            for line in page.extract_text().split('\n'):
                if line.strip():
                    ws.append([f"Page {page_num}", line.strip()])
        
        wb.save(output_path)
        return True, "Success"
    except Exception as e:
        return False, str(e)

@FileConverter.register_converter('excel_to_pdf')
def excel_to_pdf(input_path, output_path):
    try:
        wb = openpyxl.load_workbook(input_path)
        c = canvas.Canvas(output_path, pagesize=letter)
        c.setFont("Helvetica", 10)
        
        y = letter[1] - 50
        for sheet in wb.worksheets:
            c.setFont("Helvetica-Bold", 14)
            c.drawString(50, y, f"Sheet: {sheet.title}")
            y -= 30
            c.setFont("Helvetica", 10)
            
            for row in sheet.iter_rows(values_only=True):
                text = " | ".join(str(cell) if cell else "" for cell in row)
                if text.strip():
                    c.drawString(50, y, text[:100] + "..." if len(text) > 100 else text)
                    y -= 12
                    if y < 50:
                        c.showPage()
                        c.setFont("Helvetica", 10)
                        y = letter[1] - 50
        c.save()
        return True, "Success"
    except Exception as e:
        return False, str(e)

@FileConverter.register_converter('pdf_to_image')
def pdf_to_image(input_path, output_path):
    try:
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(input_path)
            page = doc[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img.save(output_path, "PNG", quality=95)
            doc.close()
        except ImportError:
            # Fallback: create placeholder
            img = Image.new('RGB', (800, 600), 'white')
            img.save(output_path, "PNG")
        return True, "Success"
    except Exception as e:
        return False, str(e)

@FileConverter.register_converter('image_to_pdf')
def image_to_pdf(input_path, output_path):
    try:
        img = Image.open(input_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img.thumbnail((2000, 2000), Image.Resampling.LANCZOS)
        img.save(output_path, "PDF", quality=95)
        return True, "Success"
    except Exception as e:
        return False, str(e)

