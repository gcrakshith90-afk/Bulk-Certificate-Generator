import os
import uuid
from pathlib import Path
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape

# ReportLab imports for fallback
from reportlab.lib.pagesizes import letter, landscape, A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = BASE_DIR / "certificate_templates"
OUTPUT_DIR = BASE_DIR / "generated_certificates"

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Jinja2 environment setup
jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def render_certificate_html(
    organization_name: str,
    certificate_title: str,
    recipient_name: str,
    recipient_email: str,
    course_name: str,
    issue_date: datetime,
    certificate_code: str,
    completion_date: datetime = None,
    signatory_name: str = None,
    signatory_designation: str = None,
) -> str:
    """Render the Jinja2 certificate HTML template with recipient data."""
    template = jinja_env.get_template("certificate.html")
    return template.render(
        organization_name=organization_name,
        certificate_title=certificate_title,
        recipient_name=recipient_name,
        recipient_email=recipient_email,
        course_name=course_name,
        issue_date=issue_date,
        completion_date=completion_date,
        signatory_name=signatory_name,
        signatory_designation=signatory_designation,
        certificate_code=certificate_code,
    )


def generate_pdf_with_reportlab(
    output_path: str,
    organization_name: str,
    certificate_title: str,
    recipient_name: str,
    recipient_email: str,
    course_name: str,
    issue_date: datetime,
    certificate_code: str,
    completion_date: datetime = None,
    signatory_name: str = None,
    signatory_designation: str = None,
):
    """Fallback generator using ReportLab in A4 landscape orientation."""
    # A4 Landscape: width ~841.89 pt, height ~595.27 pt
    width, height = landscape(A4)
    c = canvas.Canvas(output_path, pagesize=landscape(A4))

    # Outer decorative frame
    c.setStrokeColor(colors.HexColor("#1e3a8a"))
    c.setLineWidth(4)
    c.rect(20, 20, width - 40, height - 40)

    # Inner decorative frame
    c.setStrokeColor(colors.HexColor("#d97706"))
    c.setLineWidth(1.5)
    c.rect(30, 30, width - 60, height - 60)

    # Corner decorations
    c.setStrokeColor(colors.HexColor("#d97706"))
    c.setLineWidth(2)
    # top-left
    c.line(35, height - 35, 55, height - 35)
    c.line(35, height - 35, 35, height - 55)
    # top-right
    c.line(width - 35, height - 35, width - 55, height - 35)
    c.line(width - 35, height - 35, width - 35, height - 55)
    # bottom-left
    c.line(35, 35, 55, 35)
    c.line(35, 35, 35, 55)
    # bottom-right
    c.line(width - 35, 35, width - 55, 35)
    c.line(width - 35, 35, width - 35, 55)

    # Organization Header
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(colors.HexColor("#1e3a8a"))
    c.drawCentredString(width / 2.0, height - 80, organization_name.upper())

    # Certificate Title
    c.setFont("Helvetica-Bold", 26)
    c.setFillColor(colors.HexColor("#0f172a"))
    c.drawCentredString(width / 2.0, height - 125, certificate_title.upper())

    # Subtitle
    c.setFont("Helvetica-Oblique", 13)
    c.setFillColor(colors.HexColor("#64748b"))
    c.drawCentredString(width / 2.0, height - 155, "This certificate is proudly presented to")

    # Recipient Name
    c.setFont("Times-Bold", 32)
    c.setFillColor(colors.HexColor("#1e3a8a"))
    c.drawCentredString(width / 2.0, height - 205, recipient_name)
    c.setStrokeColor(colors.HexColor("#d97706"))
    c.setLineWidth(2)
    c.line((width / 2.0) - 180, height - 215, (width / 2.0) + 180, height - 215)

    # Description Paragraph
    c.setFont("Helvetica", 13)
    c.setFillColor(colors.HexColor("#334155"))
    c.drawCentredString(width / 2.0, height - 250, "For successfully participating in and completing the program")

    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.HexColor("#0f172a"))
    c.drawCentredString(width / 2.0, height - 275, course_name)

    detail_str = ""
    if completion_date:
        detail_str += f"Completed on {completion_date.strftime('%B %d, %Y')}. "
    detail_str += "Demonstrating dedication, academic excellence, and commendable performance."

    c.setFont("Helvetica", 11)
    c.setFillColor(colors.HexColor("#475569"))
    c.drawCentredString(width / 2.0, height - 305, detail_str)

    # Footer Metadata Left
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(colors.HexColor("#334155"))
    c.drawString(60, 110, f"Issue Date: {issue_date.strftime('%B %d, %Y')}")
    c.drawString(60, 92, f"Certificate ID: {certificate_code}")
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#64748b"))
    c.drawString(60, 76, f"Recipient: {recipient_email}")
    c.drawString(60, 60, "Status: Verified & Authentic Record")

    # Center Gold Seal
    c.setStrokeColor(colors.HexColor("#d97706"))
    c.setFillColor(colors.HexColor("#fffbeb"))
    c.setLineWidth(2)
    c.circle(width / 2.0, 90, 32, fill=1, stroke=1)
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(colors.HexColor("#b45309"))
    c.drawCentredString(width / 2.0, 96, "CERTIFIED")
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(width / 2.0, 82, "EXCELLENCE")

    # Signatory Right
    c.setStrokeColor(colors.HexColor("#64748b"))
    c.setLineWidth(1)
    c.line(width - 240, 95, width - 60, 95)
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.HexColor("#0f172a"))
    sig_name = signatory_name if signatory_name else "Authorized Signatory"
    c.drawCentredString(width - 150, 78, sig_name)
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#64748b"))
    sig_desig = signatory_designation if signatory_designation else organization_name
    c.drawCentredString(width - 150, 64, sig_desig)

    c.save()


def generate_certificate_pdf(
    certificate_code: str,
    organization_name: str,
    certificate_title: str,
    recipient_name: str,
    recipient_email: str,
    course_name: str,
    issue_date: datetime,
    completion_date: datetime = None,
    signatory_name: str = None,
    signatory_designation: str = None,
    force_engine: str = None,
) -> tuple[bool, str | None, str | None]:
    """
    Generate PDF certificate file and save in GENERATED_CERTIFICATES_FOLDER.
    Returns: (success: bool, error_message: str | None, relative_filename: str | None)
    """
    try:
        filename = f"cert_{certificate_code}_{uuid.uuid4().hex[:8]}.pdf"
        full_filepath = OUTPUT_DIR / filename

        # Prefer WeasyPrint if available and not forced to reportlab
        weasyprint_success = False
        if force_engine != "reportlab":
            try:
                import weasyprint

                rendered_html = render_certificate_html(
                    organization_name=organization_name,
                    certificate_title=certificate_title,
                    recipient_name=recipient_name,
                    recipient_email=recipient_email,
                    course_name=course_name,
                    issue_date=issue_date,
                    certificate_code=certificate_code,
                    completion_date=completion_date,
                    signatory_name=signatory_name,
                    signatory_designation=signatory_designation,
                )
                html_doc = weasyprint.HTML(string=rendered_html)
                html_doc.write_pdf(target=str(full_filepath))
                weasyprint_success = True
            except (ImportError, OSError):
                # WeasyPrint or underlying C library (pango/cairo) not available, fall back
                weasyprint_success = False

        if not weasyprint_success:
            # Fall back to ReportLab
            generate_pdf_with_reportlab(
                output_path=str(full_filepath),
                organization_name=organization_name,
                certificate_title=certificate_title,
                recipient_name=recipient_name,
                recipient_email=recipient_email,
                course_name=course_name,
                issue_date=issue_date,
                certificate_code=certificate_code,
                completion_date=completion_date,
                signatory_name=signatory_name,
                signatory_designation=signatory_designation,
            )

        # Verify that file exists and has non-zero size
        if os.path.exists(full_filepath) and os.path.getsize(full_filepath) > 0:
            return True, None, filename
        else:
            return False, "Generated PDF file is empty or missing from disk.", None

    except Exception as e:
        return False, str(e), None
