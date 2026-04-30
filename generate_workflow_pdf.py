"""
Generate PhysiologicPRISM Workflow Demo PDF
Groups screenshots by PRISM module with professional formatting
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib import colors
from reportlab.pdfgen import canvas
import os

# Screenshot groupings by PRISM module
SCREENSHOT_GROUPS = [
    {
        "module": "Module 1: Present History & Past Medical History",
        "description": "The clinical journey begins with comprehensive patient intake. Physiotherapists document the chief complaint, symptom behavior, and past medical history using AI-powered differential questioning to ensure nothing is missed.",
        "screenshots": list(range(1, 6)),  # 1-5
        "key_features": [
            "Structured present history documentation",
            "AI-suggested differential questions based on presentation",
            "Systematic past medical history screening"
        ]
    },
    {
        "module": "Module 2: Pathophysiological Mechanism Analysis",
        "description": "Understanding pain mechanisms guides treatment selection. The PRISM framework provides structured assessment of nociceptive, neuropathic, and nociplastic pain mechanisms with comprehensive dropdown options and AI reasoning assistance.",
        "screenshots": list(range(6, 16)),  # 6-15
        "key_features": [
            "Evidence-based pain mechanism classification",
            "Structured clinical reasoning for mechanism identification",
            "AI-powered mechanism analysis and differential considerations"
        ]
    },
    {
        "module": "Module 3: ICF-Based Patient Functioning Assessment",
        "description": "Built on the WHO International Classification of Functioning, Disability and Health (ICF), this module captures body structures, body functions, activity limitations, and participation restrictions using condition-specific ICF core sets.",
        "screenshots": list(range(16, 25)),  # 16-24
        "key_features": [
            "Evidence-based ICF core sets for common conditions",
            "Structured capture of activity limitations and participation restrictions",
            "AI suggestions for comprehensive functional assessment"
        ]
    },
    {
        "module": "Module 4: Patient Perspectives & Illness Perceptions",
        "description": "Using the Common Sense Model, this module systematically captures the patient's understanding of their condition—their beliefs about identity, timeline, consequences, control/cure, emotional response, and causal attributions.",
        "screenshots": list(range(25, 38)),  # 25-37
        "key_features": [
            "Common Sense Model framework integration",
            "Systematic capture of patient's illness beliefs",
            "AI-powered analysis of psychosocial factors influencing recovery"
        ]
    },
    {
        "module": "Module 5: Initial Assessment Planning",
        "description": "Before examining the patient, clinicians plan their objective assessment strategy. The system provides body region-specific, evidence-based test batteries with AI recommendations based on the clinical presentation.",
        "screenshots": list(range(38, 71)),  # 38-70
        "key_features": [
            "Evidence-based assessment planning by body region",
            "AI-suggested tests based on clinical hypotheses",
            "Comprehensive test battery selection across 7+ domains"
        ]
    },
    {
        "module": "Module 6: Chronic Disease Factors & Maintenance Analysis",
        "description": "For persistent conditions, systematic analysis of biological, psychological, and social factors that may maintain symptoms. Integrates Yellow Flags assessment with evidence-based biopsychosocial screening.",
        "screenshots": list(range(71, 73)),  # 71-72
        "key_features": [
            "Biopsychosocial factor assessment",
            "Fear-avoidance, catastrophizing, and self-efficacy screening",
            "AI-powered identification of modifiable maintenance factors"
        ]
    },
    {
        "module": "Module 7: Clinical Flags Screening",
        "description": "Systematic screening for red, yellow, blue, black, and orange flags ensures serious pathology is identified and psychosocial barriers to recovery are addressed early in the clinical encounter.",
        "screenshots": list(range(73, 75)),  # 73-74
        "key_features": [
            "5-flag systematic screening (red/yellow/blue/black/orange)",
            "AI-comprehensive flag identification",
            "Clinical decision support for referral considerations"
        ]
    },
    {
        "module": "Module 8: Objective Examination",
        "description": "Documentation of physical examination findings including observation, ROM, muscle testing, special tests, neurological screening, functional movement, and palpation.",
        "screenshots": list(range(75, 79)),  # 75-78
        "key_features": [
            "Structured objective examination documentation",
            "AI suggestions for test interpretation",
            "Integration with assessment plan from Module 5"
        ]
    },
    {
        "module": "Module 9: Provisional Diagnosis",
        "description": "Synthesizing all assessment data, clinicians document their primary diagnosis with ICF coding, contributing factors, clinical considerations, and differential diagnosis. AI assists in formulating comprehensive clinical impressions.",
        "screenshots": list(range(79, 101)),  # 79-100
        "key_features": [
            "ICF-coded primary diagnosis",
            "Structured contributing factors analysis",
            "AI-generated differential diagnosis and clinical considerations"
        ]
    },
    {
        "module": "Module 10: SMART Goals",
        "description": "Evidence-based goal setting using the SMART framework (Specific, Measurable, Achievable, Relevant, Time-bound). AI suggests patient-centered goals based on the functional limitations and patient priorities identified earlier.",
        "screenshots": list(range(101, 136)),  # 101-135
        "key_features": [
            "SMART goal framework integration",
            "Patient-centered goal suggestions",
            "AI-powered goal generation aligned with ICF functioning data"
        ]
    },
    {
        "module": "Module 11: Treatment Planning",
        "description": "Comprehensive treatment plan development including interventions, education strategies, home exercise programs, and progression criteria. AI provides evidence-based treatment recommendations.",
        "screenshots": list(range(136, 160)),  # 136-159
        "key_features": [
            "Evidence-based intervention selection",
            "Structured patient education planning",
            "AI treatment recommendations based on diagnosis and goals"
        ]
    },
    {
        "module": "Module 12: Follow-up & Outcomes Tracking",
        "description": "Complete the clinical documentation cycle with structured follow-up planning and outcomes measurement. The system generates comprehensive PDF reports for patients, referrers, and insurance documentation.",
        "screenshots": list(range(160, 162)),  # 160-161
        "key_features": [
            "Structured follow-up documentation",
            "Comprehensive PDF report generation",
            "Complete clinical reasoning documentation for legal defensibility"
        ]
    }
]

class NumberedCanvas(canvas.Canvas):
    """Custom canvas to add page numbers"""
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.grey)
        self.drawRightString(
            A4[0] - 1*cm, 1*cm,
            f"Page {self._pageNumber} of {page_count}"
        )

def create_cover_page(story, styles):
    """Create professional cover page"""
    # Add space from top
    story.append(Spacer(1, 2*inch))

    # Main title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=colors.HexColor('#1a5f5f'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    story.append(Paragraph("PhysiologicPRISM", title_style))

    # Subtitle
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=20,
        textColor=colors.HexColor('#2d8080'),
        spaceAfter=50,
        alignment=TA_CENTER,
        fontName='Helvetica'
    )
    story.append(Paragraph("Clinical Workflow Overview", subtitle_style))

    story.append(Spacer(1, 0.5*inch))

    # Description
    desc_style = ParagraphStyle(
        'CoverDesc',
        parent=styles['Normal'],
        fontSize=12,
        alignment=TA_CENTER,
        spaceAfter=12,
        leading=18
    )

    story.append(Paragraph(
        "A demonstration of the complete PRISM Clinical Reasoning Framework",
        desc_style
    ))
    story.append(Paragraph(
        "From patient intake to comprehensive PDF report generation",
        desc_style
    ))

    story.append(Spacer(1, 1*inch))

    # Key points
    key_points_style = ParagraphStyle(
        'KeyPoints',
        parent=styles['Normal'],
        fontSize=11,
        alignment=TA_LEFT,
        leftIndent=1.5*inch,
        rightIndent=1.5*inch,
        spaceAfter=8,
        leading=16
    )

    story.append(Paragraph("• 12 structured clinical reasoning modules", key_points_style))
    story.append(Paragraph("• ICF framework integration (WHO/WCPT endorsed)", key_points_style))
    story.append(Paragraph("• AI-powered clinical decision support", key_points_style))
    story.append(Paragraph("• Evidence-based assessment workflows", key_points_style))
    story.append(Paragraph("• Comprehensive documentation for legal defensibility", key_points_style))

    story.append(Spacer(1, 1.5*inch))

    # Footer
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    story.append(Paragraph("© 2025 PHYSIOLOGICPRISM LLP | Proprietary & Confidential", footer_style))

    story.append(PageBreak())

def create_intro_page(story, styles):
    """Create introduction page"""
    # Title
    title_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#1a5f5f'),
        spaceAfter=20,
        fontName='Helvetica-Bold'
    )
    story.append(Paragraph("What is the PRISM Framework?", title_style))

    # Body text
    body_style = ParagraphStyle(
        'BodyText',
        parent=styles['Normal'],
        fontSize=11,
        alignment=TA_JUSTIFY,
        spaceAfter=12,
        leading=16
    )

    story.append(Paragraph(
        "The <b>PRISM Clinical Reasoning Framework</b> is a copyrighted, proprietary methodology "
        "developed by a practicing physiotherapist to transform clinical reasoning into structured, "
        "repeatable, and legally defensible documentation.",
        body_style
    ))

    story.append(Paragraph(
        "While clinical reasoning is well-taught in physiotherapy education, it is often poorly "
        "documented in practice. PRISM bridges this gap by providing a 12-module workflow that "
        "guides clinicians through comprehensive assessment, diagnosis, goal-setting, and treatment planning.",
        body_style
    ))

    story.append(Spacer(1, 0.3*inch))

    # Key differentiators
    story.append(Paragraph("Key Differentiators", ParagraphStyle(
        'SubTitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2d8080'),
        spaceAfter=12,
        fontName='Helvetica-Bold'
    )))

    bullet_style = ParagraphStyle(
        'BulletText',
        parent=styles['Normal'],
        fontSize=11,
        leftIndent=20,
        spaceAfter=10,
        leading=15,
        bulletIndent=10
    )

    story.append(Paragraph(
        "<b>ICF Framework Integration:</b> Built on the International Classification of Functioning, "
        "Disability and Health (ICF)—the global standard endorsed by WHO and WCPT. Includes "
        "evidence-based ICF core sets for common musculoskeletal and neurological conditions.",
        bullet_style
    ))

    story.append(Paragraph(
        "<b>Biopsychosocial Completeness:</b> Systematically captures biological, psychological, "
        "and social factors using evidence-based models including the Common Sense Model, "
        "Pain Mechanism Classification, and Yellow Flags Assessment.",
        bullet_style
    ))

    story.append(Paragraph(
        "<b>AI-Powered Clinical Decision Support:</b> Intelligent suggestions at every module help "
        "reduce cognitive load, ensure comprehensive assessment, and maintain clinical reasoning quality "
        "during busy clinic hours.",
        bullet_style
    ))

    story.append(Paragraph(
        "<b>Clinical Defensibility:</b> Complete documentation demonstrates not just what was observed, "
        "but the clinical reasoning that led to diagnosis and treatment decisions—critical for professional "
        "liability protection.",
        bullet_style
    ))

    story.append(Spacer(1, 0.3*inch))

    story.append(Paragraph(
        "This demo walks through a complete patient case from intake to PDF report generation, "
        "showcasing how each module builds upon the previous to create comprehensive clinical documentation.",
        body_style
    ))

    story.append(PageBreak())

def add_screenshot_with_description(story, styles, screenshot_path, description, max_width=6*inch):
    """Add a screenshot with description"""
    if not os.path.exists(screenshot_path):
        print(f"Warning: Screenshot not found: {screenshot_path}")
        return

    try:
        # Add description if provided
        if description:
            desc_style = ParagraphStyle(
                'ScreenshotDesc',
                parent=styles['Normal'],
                fontSize=9,
                textColor=colors.HexColor('#555555'),
                spaceAfter=8,
                alignment=TA_LEFT,
                leading=12,
                italic=True
            )
            story.append(Paragraph(description, desc_style))

        # Add screenshot
        img = Image(screenshot_path, width=max_width, height=max_width*0.6, kind='proportional')
        story.append(img)
        story.append(Spacer(1, 0.2*inch))

    except Exception as e:
        print(f"Error adding screenshot {screenshot_path}: {e}")

def create_module_section(story, styles, group, screenshots_dir):
    """Create a section for each PRISM module"""
    # Module title
    module_style = ParagraphStyle(
        'ModuleTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1a5f5f'),
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    story.append(Paragraph(group['module'], module_style))

    # Description
    desc_style = ParagraphStyle(
        'ModuleDesc',
        parent=styles['Normal'],
        fontSize=11,
        alignment=TA_JUSTIFY,
        spaceAfter=12,
        leading=15
    )
    story.append(Paragraph(group['description'], desc_style))

    # Key features box
    if 'key_features' in group and group['key_features']:
        story.append(Spacer(1, 0.1*inch))

        # Create table for key features
        features_data = [["Key Features:"]]
        for feature in group['key_features']:
            features_data.append([f"• {feature}"])

        features_table = Table(features_data, colWidths=[5.5*inch])
        features_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8f4f4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1a5f5f')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#1a5f5f')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(features_table)
        story.append(Spacer(1, 0.2*inch))

    # Add representative screenshots (select key ones, not all)
    screenshot_files = [
        f for f in os.listdir(screenshots_dir)
        if f.endswith('.png') and any(f.startswith(f"{num} ") for num in group['screenshots'])
    ]
    screenshot_files.sort(key=lambda x: int(x.split(' ')[0]))

    # Select representative screenshots: first, middle, and ones with "AI" in name
    representative_screenshots = []
    if screenshot_files:
        # Always include first screenshot
        representative_screenshots.append(screenshot_files[0])

        # Add AI screenshots (max 2-3)
        ai_screenshots = [f for f in screenshot_files if 'AI' in f]
        if ai_screenshots:
            # Take first 1-2 AI screenshots
            representative_screenshots.extend(ai_screenshots[:2])

        # If we have very few screenshots, show them all; otherwise sample
        if len(screenshot_files) <= 5:
            for f in screenshot_files:
                if f not in representative_screenshots:
                    representative_screenshots.append(f)
        else:
            # Add one from middle if not already included
            mid_idx = len(screenshot_files) // 2
            if screenshot_files[mid_idx] not in representative_screenshots:
                representative_screenshots.append(screenshot_files[mid_idx])

    # Add the selected screenshots
    for idx, filename in enumerate(representative_screenshots[:4]):  # Max 4 per module
        screenshot_path = os.path.join(screenshots_dir, filename)
        # Extract description from filename
        desc = filename.replace('.png', '').split(' ', 1)[1] if ' ' in filename else ""
        add_screenshot_with_description(story, styles, screenshot_path, desc)

    # Add note if we didn't show all screenshots
    if len(screenshot_files) > len(representative_screenshots):
        note_style = ParagraphStyle(
            'Note',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.grey,
            alignment=TA_CENTER,
            italic=True
        )
        story.append(Paragraph(
            f"<i>({len(screenshot_files) - len(representative_screenshots)} additional workflow "
            f"screenshots available for this module)</i>",
            note_style
        ))

    story.append(PageBreak())

def create_summary_page(story, styles):
    """Create summary page"""
    title_style = ParagraphStyle(
        'SummaryTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1a5f5f'),
        spaceAfter=20,
        fontName='Helvetica-Bold'
    )
    story.append(Paragraph("Complete PRISM Workflow Summary", title_style))

    body_style = ParagraphStyle(
        'SummaryBody',
        parent=styles['Normal'],
        fontSize=11,
        alignment=TA_JUSTIFY,
        spaceAfter=12,
        leading=15
    )

    story.append(Paragraph(
        "The PRISM framework guides physiotherapists through 12 comprehensive modules, "
        "ensuring complete clinical documentation from initial intake to ongoing outcomes tracking:",
        body_style
    ))

    story.append(Spacer(1, 0.2*inch))

    # Create summary table
    modules_data = [
        ["Module", "Focus Area", "Key Output"],
        ["1", "Present & Past History", "Chief complaint, symptom behavior, medical screening"],
        ["2", "Pain Mechanisms", "Nociceptive/neuropathic/nociplastic classification"],
        ["3", "ICF Functioning Assessment", "Body structures, functions, activities, participation"],
        ["4", "Patient Perspectives", "Illness perceptions (Common Sense Model)"],
        ["5", "Assessment Planning", "Evidence-based test selection strategy"],
        ["6", "Chronic Disease Factors", "Biopsychosocial maintenance factors"],
        ["7", "Clinical Flags", "Red/yellow/blue/black/orange flag screening"],
        ["8", "Objective Examination", "Physical examination findings"],
        ["9", "Provisional Diagnosis", "ICF-coded diagnosis, differential diagnosis"],
        ["10", "SMART Goals", "Patient-centered, measurable goals"],
        ["11", "Treatment Planning", "Evidence-based intervention selection"],
        ["12", "Follow-up & Outcomes", "Progress tracking, outcomes measurement"],
    ]

    modules_table = Table(modules_data, colWidths=[0.7*inch, 2*inch, 3*inch])
    modules_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5f5f')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f8f8')]),
    ]))
    story.append(modules_table)

    story.append(Spacer(1, 0.3*inch))

    # PDF Report Output
    output_title = ParagraphStyle(
        'OutputTitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2d8080'),
        spaceAfter=12,
        fontName='Helvetica-Bold'
    )
    story.append(Paragraph("Comprehensive PDF Report Output", output_title))

    story.append(Paragraph(
        "Upon completing the PRISM workflow, the system generates a professional PDF report containing:",
        body_style
    ))

    bullet_style = ParagraphStyle(
        'SummaryBullet',
        parent=styles['Normal'],
        fontSize=10,
        leftIndent=30,
        spaceAfter=6,
        leading=14,
        bulletIndent=15
    )

    story.append(Paragraph("• Complete patient assessment findings across all 12 modules", bullet_style))
    story.append(Paragraph("• ICF-coded diagnosis with clinical reasoning documentation", bullet_style))
    story.append(Paragraph("• SMART goals aligned with patient priorities", bullet_style))
    story.append(Paragraph("• Evidence-based treatment plan with progression criteria", bullet_style))
    story.append(Paragraph("• Home exercise program and patient education materials", bullet_style))
    story.append(Paragraph("• Professional formatting suitable for patients, referrers, and insurance", bullet_style))

    story.append(Spacer(1, 0.3*inch))

    story.append(Paragraph(
        "This comprehensive documentation ensures clinical defensibility, supports continuity of care, "
        "and demonstrates adherence to best-practice guidelines endorsed by WCPT and other professional bodies.",
        body_style
    ))

    story.append(Spacer(1, 0.5*inch))

    # Contact/Footer
    footer_style = ParagraphStyle(
        'SummaryFooter',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#1a5f5f'),
        alignment=TA_CENTER,
        spaceAfter=8
    )

    story.append(Paragraph(
        "<b>PhysiologicPRISM</b> — Structured Clinical Documentation for Physiotherapists",
        footer_style
    ))
    story.append(Paragraph(
        "www.physiologicprism.com",
        ParagraphStyle('Link', parent=footer_style, fontSize=9, textColor=colors.HexColor('#2d8080'))
    ))

def generate_pdf(output_path, screenshots_dir):
    """Generate the complete PDF"""
    # Create PDF document
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=1*cm,
        leftMargin=1*cm,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm
    )

    # Container for PDF elements
    story = []

    # Get styles
    styles = getSampleStyleSheet()

    # Create document sections
    print("Creating cover page...")
    create_cover_page(story, styles)

    print("Creating introduction...")
    create_intro_page(story, styles)

    # Add each module section
    for idx, group in enumerate(SCREENSHOT_GROUPS):
        print(f"Processing {group['module']}...")
        create_module_section(story, styles, group, screenshots_dir)

    print("Creating summary page...")
    create_summary_page(story, styles)

    # Build PDF with custom canvas for page numbers
    print(f"Building PDF: {output_path}")
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[SUCCESS] PDF generated successfully: {output_path}")

if __name__ == "__main__":
    # Paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    screenshots_dir = os.path.join(script_dir, "Screenshots")
    docs_dir = os.path.join(script_dir, "docs")

    # Create docs directory if it doesn't exist
    os.makedirs(docs_dir, exist_ok=True)

    output_path = os.path.join(docs_dir, "prism-workflow-demo.pdf")

    # Generate PDF
    print("=" * 60)
    print("PhysiologicPRISM Workflow Demo PDF Generator")
    print("=" * 60)

    if not os.path.exists(screenshots_dir):
        print(f"ERROR: Screenshots directory not found: {screenshots_dir}")
        exit(1)

    generate_pdf(output_path, screenshots_dir)

    print("=" * 60)
    print("PDF generation complete!")
    print("=" * 60)
