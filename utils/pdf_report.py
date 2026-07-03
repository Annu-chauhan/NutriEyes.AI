from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.barcode.qr import QrCodeWidget

def generate_pdf_report(
    patient_name,
    prediction,
    confidence,
    recommendation,
    hash_value,
    pdf_path,
    verify_url=None,
    severity_stage="Healthy"
):

    # =========================
    # PDF DOCUMENT
    # =========================

    doc = SimpleDocTemplate(

        pdf_path,

        pagesize=letter
    )

    styles = getSampleStyleSheet()

    elements = []

    # =========================
    # TITLE
    # =========================

    elements.append(

        Paragraph(

            "NutriEye AI Medical Report",

            styles['Title']
        )
    )

    elements.append(
        Spacer(1, 20)
    )

    # =========================
    # PATIENT DETAILS
    # =========================

    elements.append(

        Paragraph(

            f"<b>Patient Name:</b> {patient_name}",

            styles['BodyText']
        )
    )

    elements.append(
        Spacer(1, 10)
    )

    elements.append(

        Paragraph(

            f"<b>Predicted Disease:</b> {prediction}",

            styles['BodyText']
        )
    )

    elements.append(
        Spacer(1, 10)
    )

    elements.append(

        Paragraph(

            f"<b>Confidence Score:</b> {confidence}%",

            styles['BodyText']
        )
    )

    elements.append(
        Spacer(1, 10)
    )

    elements.append(

        Paragraph(

            f"<b>Estimated Severity:</b> {severity_stage}",

            styles['BodyText']
        )
    )

    elements.append(
        Spacer(1, 15)
    )

    # =========================
    # DISEASE DESCRIPTION
    # =========================

    elements.append(

        Paragraph(

            "<b>Disease Explanation:</b>",

            styles['Heading2']
        )
    )

    elements.append(

        Paragraph(

            recommendation["description"],

            styles['BodyText']
        )
    )

    elements.append(
        Spacer(1, 15)
    )

    # =========================
    # DIET
    # =========================

    diet_text = "<br/>".join(

        [
            f"• {item}"
            for item in recommendation["diet"]
        ]
    )

    elements.append(

        Paragraph(

            "<b>Recommended Diet:</b>",

            styles['Heading2']
        )
    )

    elements.append(

        Paragraph(

            diet_text,

            styles['BodyText']
        )
    )

    elements.append(
        Spacer(1, 15)
    )

    # =========================
    # EXERCISE
    # =========================

    exercise_text = "<br/>".join(

        [
            f"• {item}"
            for item in recommendation["exercise"]
        ]
    )

    elements.append(

        Paragraph(

            "<b>Recommended Exercise:</b>",

            styles['Heading2']
        )
    )

    elements.append(

        Paragraph(

            exercise_text,

            styles['BodyText']
        )
    )

    elements.append(
        Spacer(1, 15)
    )

    # =========================
    # YOGA
    # =========================

    yoga_text = "<br/>".join(

        [
            f"• {item}"
            for item in recommendation["yoga"]
        ]
    )

    elements.append(

        Paragraph(

            "<b>Recommended Yoga:</b>",

            styles['Heading2']
        )
    )

    elements.append(

        Paragraph(

            yoga_text,

            styles['BodyText']
        )
    )

    elements.append(
        Spacer(1, 15)
    )

    # =========================
    # PRECAUTIONS
    # =========================

    precautions_text = "<br/>".join(

        [
            f"• {item}"
            for item in recommendation["precautions"]
        ]
    )

    elements.append(

        Paragraph(

            "<b>Precautions:</b>",

            styles['Heading2']
        )
    )

    elements.append(

        Paragraph(

            precautions_text,

            styles['BodyText']
        )
    )

    elements.append(
        Spacer(1, 15)
    )

    # =========================
    # DOCTOR RECOMMENDATION
    # =========================

    elements.append(

        Paragraph(

            "<b>Doctor Recommendation:</b>",

            styles['Heading2']
        )
    )

    elements.append(

        Paragraph(

            recommendation["doctor"],

            styles['BodyText']
        )
    )

    elements.append(
        Spacer(1, 20)
    )

    # =========================
    # BLOCKCHAIN SECURITY
    # =========================

    elements.append(

        Paragraph(

            "Blockchain Security Verification",

            styles['Heading2']
        )
    )

    elements.append(

        Paragraph(

            (
                "This AI medical report is protected "
                "using SHA-256 blockchain-style hashing "
                "for integrity verification and tamper detection."
            ),

            styles['BodyText']
        )
    )

    elements.append(
        Spacer(1, 10)
    )

    elements.append(

        Paragraph(
            f"<b>Security Hash:</b> {hash_value}",
            styles['BodyText']
        )
    )

    elements.append(
        Spacer(1, 15)
    )

    if verify_url:
        elements.append(
            Paragraph(
                "<b>Report Verification QR Code:</b>",
                styles['Heading3']
            )
        )
        elements.append(Spacer(1, 5))
        
        # Instantiate reportlab native vector QR Code barcode
        qr = QrCodeWidget(verify_url)
        qr.barWidth = 80
        qr.barHeight = 80
        qr.qrVersion = 4
        
        # Wrap widget in drawing bounds
        d = Drawing(80, 80)
        d.add(qr)
        
        elements.append(d)
        elements.append(Spacer(1, 15))

    # =========================
    # DISCLAIMER
    # =========================

    elements.append(

        Paragraph(

            "Medical Disclaimer",

            styles['Heading2']
        )
    )

    elements.append(

        Paragraph(

            (
                "NutriEye is an AI-powered educational "
                "clinical support system and does not "
                "replace professional ophthalmologist diagnosis."
            ),

            styles['BodyText']
        )
    )

    # =========================
    # BUILD PDF
    # =========================

    doc.build(elements)