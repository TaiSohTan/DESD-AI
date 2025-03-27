from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle, Spacer, Image
from io import BytesIO
from datetime import datetime

def generate_invoice_pdf(invoice):
    """Generate a professional-looking PDF invoice"""
    # Create a buffer and canvas
    buffer = BytesIO()
    pagesize = A4  # (595.27, 841.89) points
    c = canvas.Canvas(buffer, pagesize=pagesize)
    width, height = pagesize
    
    # Define colors
    primary_color = colors.HexColor('#2c3e50')  # Dark blue
    secondary_color = colors.HexColor('#3498db')  # Light blue
    text_color = colors.HexColor('#333333')  # Dark gray
    light_color = colors.HexColor('#ecf0f1')  # Light gray
    
    # Set up styles
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='InvoiceTitle',
        fontName='Helvetica-Bold',
        fontSize=18,
        textColor=primary_color,
        alignment=1,  # Center
        spaceAfter=0.2*inch
    ))
    styles.add(ParagraphStyle(
        name='InvoiceInfo',
        fontName='Helvetica',
        fontSize=10,
        textColor=text_color
    ))
    styles.add(ParagraphStyle(
        name='InvoiceInfoBold',
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=text_color
    ))
    styles.add(ParagraphStyle(
        name='TableHeader',
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=colors.white,
        alignment=1  # Center
    ))
    
    # Draw the header
    # Logo could be added here if available
    # c.drawImage("path/to/logo.png", 50, height - 100, width=100, height=50)
    
    # Draw header background
    c.setFillColor(primary_color)
    c.rect(0, height - 120, width, 120, fill=1, stroke=0)
    
    # Invoice title
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 24)
    c.drawCentredString(width/2, height - 60, "INVOICE")
    
    # Invoice number
    c.setFont('Helvetica', 12)
    c.drawCentredString(width/2, height - 80, f"#{invoice.id}")
    
    # Organization info in header
    c.setFont('Helvetica', 10)
    c.drawString(50, height - 40, "MLAAS - Machine Learning as a Service")
    c.drawString(50, height - 55, "UWE Bristol")
    c.drawString(50, height - 70, "Bristol, UK")
    
    # Status badge
    if invoice.status == 'Paid':
        status_color = colors.HexColor('#27ae60')  # Green
        status_text = "PAID"
    else:
        status_color = colors.HexColor('#e74c3c')  # Red
        status_text = "PENDING"
    
    # Draw status badge
    c.setFillColor(status_color)
    badge_width = 100
    badge_height = 30
    badge_x = width - badge_width - 50
    badge_y = height - 50
    c.roundRect(badge_x, badge_y, badge_width, badge_height, 5, fill=1, stroke=0)
    
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 14)
    c.drawCentredString(badge_x + badge_width/2, badge_y + 10, status_text)
    
    # Invoice information section
    y_position = height - 150
    
    # Left column - Bill to
    c.setFillColor(text_color)
    c.setFont('Helvetica-Bold', 12)
    c.drawString(50, y_position, "BILL TO")
    
    c.setFont('Helvetica', 10)
    c.drawString(50, y_position - 20, invoice.user.name if hasattr(invoice.user, 'name') and invoice.user.name else invoice.user.email)
    c.drawString(50, y_position - 35, invoice.user.email)
    
    # Right column - Invoice details
    col_width = 175
    detail_x = width - col_width - 50
    
    c.setFont('Helvetica-Bold', 10)
    c.drawString(detail_x, y_position, "INVOICE DATE")
    c.drawString(detail_x, y_position - 30, "DUE DATE")
    c.drawString(detail_x, y_position - 60, "AMOUNT DUE")
    
    c.setFont('Helvetica', 10)
    # Format dates
    issued_date = invoice.issued_date.strftime("%d %b %Y") if hasattr(invoice, 'issued_date') else "N/A"
    due_date = invoice.due_date.strftime("%d %b %Y") if hasattr(invoice, 'due_date') else "N/A"
    
    c.drawString(detail_x + 100, y_position, issued_date)
    c.drawString(detail_x + 100, y_position - 30, due_date)
    
    # Amount with larger font and bold
    c.setFont('Helvetica-Bold', 14)
    c.drawString(detail_x + 100, y_position - 60, f"£{invoice.amount:.2f}")
    
    # Horizontal separator
    y_position -= 100
    c.setStrokeColor(light_color)
    c.setLineWidth(1)
    c.line(50, y_position, width - 50, y_position)
    
    # Invoice items table
    y_position -= 30
    c.setFont('Helvetica-Bold', 12)
    c.drawString(50, y_position, "INVOICE ITEMS")
    
    # Create table for invoice items
    y_position -= 20
    data = [
        ["DESCRIPTION", "AMOUNT"],
        [invoice.description, f"£{invoice.amount:.2f}"],
    ]
    
    # Set table style
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), secondary_color),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.white),
        ('ALIGN', (0, 0), (1, 0), 'CENTER'),
        ('ALIGN', (1, 1), (1, 1), 'RIGHT'),
        ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (1, 0), 8),
        ('TOPPADDING', (0, 0), (1, 0), 8),
        ('GRID', (0, 0), (1, 1), 0.5, light_color),
    ])
    
    # Create and draw table
    table_width = width - 100
    table = Table(data, colWidths=[table_width * 0.7, table_width * 0.3])
    table.setStyle(table_style)
    
    # Draw table
    table.wrapOn(c, width, height)
    table.drawOn(c, 50, y_position - 30)
    
    # Total
    y_position -= 60
    c.setFont('Helvetica-Bold', 12)
    c.drawString(width - 150, y_position, "TOTAL:")
    c.drawString(width - 80, y_position, f"£{invoice.amount:.2f}")
    
    # Footer
    y_position = 50
    c.setFillColor(light_color)
    c.rect(0, 0, width, y_position + 20, fill=1, stroke=0)
    
    c.setFillColor(text_color)
    c.setFont('Helvetica', 9)
    c.drawCentredString(width/2, y_position, "Thank you for using MLAAS - Machine Learning as a Service")
    c.drawCentredString(width/2, y_position - 15, "For any questions, please contact support@mlaas.com")
    
    # Payment information
    if invoice.status == 'Pending':
        y_position = 100
        c.setFillColor(colors.HexColor('#f39c12'))  # Orange
        c.roundRect(50, y_position, width - 100, 40, 5, fill=1, stroke=0)
        
        c.setFillColor(colors.white)
        c.setFont('Helvetica-Bold', 10)
        c.drawCentredString(width/2, y_position + 25, "PAYMENT INFORMATION")
        c.setFont('Helvetica', 9)
        c.drawCentredString(width/2, y_position + 10, "Please pay this invoice by the due date to continue using our services.")
    
    # Finalize the PDF
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer