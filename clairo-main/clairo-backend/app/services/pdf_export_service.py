from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_LEFT, TA_CENTER
import io


def generate_appeal_pdf(appeal_letter: str, claim: dict) -> bytes:

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=inch,
        leftMargin=inch,
        topMargin=inch,
        bottomMargin=inch
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "title",
        parent=styles["Normal"],
        fontSize=13,
        fontName="Helvetica-Bold",
        alignment=TA_CENTER,
        spaceAfter=12
    )

    header_style = ParagraphStyle(
        "header",
        parent=styles["Normal"],
        fontSize=10,
        fontName="Helvetica-Bold",
        spaceAfter=4
    )

    body_style = ParagraphStyle(
        "body",
        parent=styles["Normal"],
        fontSize=10,
        fontName="Helvetica",
        leading=14,
        spaceAfter=8
    )

    story = []

    # Title
    story.append(Paragraph("INSURANCE APPEAL LETTER", title_style))
    story.append(Spacer(1, 0.1 * inch))

    # Claim header info
    story.append(Paragraph(f"Payer: {claim.get('payer', 'N/A')}", header_style))
    story.append(Paragraph(f"Patient ID: {claim.get('patient_id', 'N/A')}", header_style))
    story.append(Paragraph(f"CPT Codes: {', '.join(claim.get('cpt_codes', []))}", header_style))
    story.append(Paragraph(f"Service Date: {claim.get('service_date', 'N/A')}", header_style))
    story.append(Paragraph(f"Denied Amount: {claim.get('denied_amount', 'N/A')}", header_style))
    story.append(Spacer(1, 0.2 * inch))

    # Appeal letter body — split by newlines into paragraphs
    for line in appeal_letter.split("\n"):
        line = line.strip()
        if line:
            story.append(Paragraph(line, body_style))
        else:
            story.append(Spacer(1, 0.05 * inch))

    # Footer
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("AI-Assisted Document — Review required before submission.", ParagraphStyle(
        "footer",
        parent=styles["Normal"],
        fontSize=8,
        fontName="Helvetica-Oblique",
        alignment=TA_CENTER
    )))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()