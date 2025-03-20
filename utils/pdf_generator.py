from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO

def generate_invoice_pdf(Invoice):
    pdf_buffer = BytesIO()
    pdf_canvas = canvas.Canvas(pdf_buffer, pagesize=letter)
    width, height = letter

    ## Title 
    title = "MLAAS Invoice"
    ## Font and Size
    pdf_canvas.setFont("Times-Roman", 20)
    title_width = pdf_canvas.stringWidth(title, "Times-Roman", 20)
    ## Position 
    pdf_canvas.drawString((width - title_width) / 2, height - 50, title)

    ## Line 
    pdf_canvas.setLineWidth(3)
    pdf_canvas.line(50, height - 60, width - 50, height - 60)

    ## Content 
    pdf_canvas.setFont("Times-Roman", 16)
    pdf_canvas.setLineWidth(1)
    pdf_canvas.drawString(100, height - 100, f"Invoice Number : {Invoice.id}")
    pdf_canvas.drawString(100, height - 120, f"Name: {Invoice.user.name}")
    pdf_canvas.drawString(100, height - 140, f"Email: {Invoice.user.email}")
    pdf_canvas.drawString(100, height - 160, f"Date Issued: {Invoice.issued_date}")
    pdf_canvas.drawString(100, height - 180, f"Services Due Date: {Invoice.due_date}")
    pdf_canvas.drawString(100, height - 200, f"Status: {Invoice.status}")
    pdf_canvas.drawString(100, height - 220, f"Amount: £{Invoice.amount}")

    ## End the PDF
    pdf_canvas.showPage()
    pdf_canvas.save()

    pdf_buffer.seek(0)
    return pdf_buffer