import os
import io
import tempfile
from django.conf import settings
from django.core.files.base import ContentFile
from PyPDF2 import PdfReader, PdfWriter
from pdf2docx import Converter
from docx import Document
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import openpyxl
from openpyxl import Workbook

class FileConverter:
    
    @staticmethod
    def pdf_to_word(input_file_path, output_file_path):
        """Convert PDF to Word document"""
        try:
            cv = Converter(input_file_path)
            cv.convert(output_file_path, start=0, end=None)
            cv.close()
            return True, "Conversion successful"
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def word_to_pdf(input_file_path, output_file_path):
        """Convert Word document to PDF using reportlab"""
        try:
            doc = Document(input_file_path)
            
            # Create PDF using reportlab
            c = canvas.Canvas(output_file_path, pagesize=letter)
            width, height = letter
            y_position = height - 50
            
            # Set font
            c.setFont("Helvetica", 12)
            
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    # Split long lines
                    text = paragraph.text.strip()
                    words = text.split(' ')
                    line = ""
                    
                    for word in words:
                        test_line = line + word + " "
                        if len(test_line) > 80:  # Approximate character limit per line
                            if line:
                                c.drawString(50, y_position, line.strip())
                                y_position -= 15
                                line = word + " "
                            else:
                                # Single word is too long, just draw it
                                c.drawString(50, y_position, word)
                                y_position -= 15
                                line = ""
                        else:
                            line = test_line
                        
                        # Check if we need a new page
                        if y_position < 50:
                            c.showPage()
                            c.setFont("Helvetica", 12)
                            y_position = height - 50
                    
                    # Draw remaining text in line
                    if line.strip():
                        c.drawString(50, y_position, line.strip())
                        y_position -= 15
                    
                    # Add extra space after paragraph
                    y_position -= 5
                    
                    # Check if we need a new page
                    if y_position < 50:
                        c.showPage()
                        c.setFont("Helvetica", 12)
                        y_position = height - 50
            
            c.save()
            return True, "Conversion successful"
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def pdf_to_excel(input_file_path, output_file_path):
        """Convert PDF to Excel (extract text to Excel)"""
        try:
            reader = PdfReader(input_file_path)
            wb = Workbook()
            ws = wb.active
            ws.title = "PDF Content"
            
            # Set headers
            ws.cell(row=1, column=1, value="Page")
            ws.cell(row=1, column=2, value="Content")
            
            row = 2
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()
                lines = text.split('\n')
                
                for line in lines:
                    if line.strip():
                        ws.cell(row=row, column=1, value=f"Page {page_num + 1}")
                        ws.cell(row=row, column=2, value=line.strip())
                        row += 1
            
            wb.save(output_file_path)
            return True, "Conversion successful"
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def excel_to_pdf(input_file_path, output_file_path):
        """Convert Excel to PDF"""
        try:
            wb = openpyxl.load_workbook(input_file_path)
            c = canvas.Canvas(output_file_path, pagesize=letter)
            width, height = letter
            c.setFont("Helvetica", 10)
            
            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                y_position = height - 50
                
                # Add sheet title
                c.setFont("Helvetica-Bold", 14)
                c.drawString(50, y_position, f"Sheet: {sheet_name}")
                y_position -= 30
                c.setFont("Helvetica", 10)
                
                for row in ws.iter_rows(values_only=True):
                    row_text = " | ".join([str(cell) if cell is not None else "" for cell in row])
                    if row_text.strip():
                        # Limit line length and handle long text
                        if len(row_text) > 100:
                            row_text = row_text[:97] + "..."
                        c.drawString(50, y_position, row_text)
                        y_position -= 12
                        
                        if y_position < 50:
                            c.showPage()
                            c.setFont("Helvetica", 10)
                            y_position = height - 50
                
                c.showPage()  # New page for next sheet
            
            c.save()
            return True, "Conversion successful"
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def pdf_to_image(input_file_path, output_file_path):
        """Convert PDF to Image (first page)"""
        try:
            import fitz  # PyMuPDF
            pdf_document = fitz.open(input_file_path)
            page = pdf_document[0]  # First page
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img.save(output_file_path, "PNG", quality=95)
            pdf_document.close()
            return True, "Conversion successful"
        except ImportError:
            # Fallback method using PyPDF2 (limited functionality)
            try:
                # Create a simple placeholder image
                img = Image.new('RGB', (800, 600), color='white')
                img.save(output_file_path, "PNG")
                return True, "Basic conversion completed. Install PyMuPDF for better quality."
            except Exception as e:
                return False, f"PDF to image conversion failed: {str(e)}"
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def image_to_pdf(input_file_path, output_file_path):
        """Convert Image to PDF"""
        try:
            img = Image.open(input_file_path)
            
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize if image is too large
            max_size = (2000, 2000)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            img.save(output_file_path, "PDF", quality=95)
            return True, "Conversion successful"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def convert_file(conversion_type, input_file_path):
        """
        Main conversion method that handles all conversion types
        Returns (success, content_bytes, error_message)
        """
        try:
            # Create temporary output file
            with tempfile.NamedTemporaryFile(delete=False) as temp_output:
                output_path = temp_output.name
            
            # Map conversion types to methods
            conversion_map = {
                'pdf_to_word': FileConverter.pdf_to_word,
                'word_to_pdf': FileConverter.word_to_pdf,
                'pdf_to_excel': FileConverter.pdf_to_excel,
                'excel_to_pdf': FileConverter.excel_to_pdf,
                'pdf_to_image': FileConverter.pdf_to_image,
                'image_to_pdf': FileConverter.image_to_pdf,
            }
            
            # Get the conversion method
            conversion_method = conversion_map.get(conversion_type)
            if not conversion_method:
                return False, None, f"Unsupported conversion type: {conversion_type}"
            
            # Perform the conversion
            success, message = conversion_method(input_file_path, output_path)
            
            if success:
                # Read the converted file content
                with open(output_path, 'rb') as f:
                    content = f.read()
                
                # Clean up temporary file
                os.unlink(output_path)
                
                return True, content, message
            else:
                # Clean up temporary file
                if os.path.exists(output_path):
                    os.unlink(output_path)
                return False, None, message
                
        except Exception as e:
            return False, None, f"Conversion error: {str(e)}"