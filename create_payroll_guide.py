#!/usr/bin/env python3
"""
Generate a user-friendly PDF guide for payroll operations.
No technical jargon - written for HR staff.
"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from datetime import datetime

# Create PDF
pdf_path = "Payroll_User_Guide.pdf"
doc = SimpleDocTemplate(pdf_path, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
story = []

# Define styles
styles = getSampleStyleSheet()
title_style = ParagraphStyle(
    'CustomTitle',
    parent=styles['Heading1'],
    fontSize=28,
    textColor=colors.HexColor('#1F2937'),
    spaceAfter=12,
    alignment=TA_CENTER,
    fontName='Helvetica-Bold'
)

heading_style = ParagraphStyle(
    'CustomHeading',
    parent=styles['Heading2'],
    fontSize=16,
    textColor=colors.HexColor('#374151'),
    spaceAfter=10,
    spaceBefore=12,
    fontName='Helvetica-Bold'
)

subheading_style = ParagraphStyle(
    'SubHeading',
    parent=styles['Heading3'],
    fontSize=13,
    textColor=colors.HexColor('#4B5563'),
    spaceAfter=8,
    spaceBefore=8,
    fontName='Helvetica-Bold'
)

body_style = ParagraphStyle(
    'CustomBody',
    parent=styles['BodyText'],
    fontSize=11,
    alignment=TA_JUSTIFY,
    spaceAfter=6,
    leading=14
)

bullet_style = ParagraphStyle(
    'BulletStyle',
    parent=styles['BodyText'],
    fontSize=11,
    leftIndent=20,
    spaceAfter=5,
    leading=13
)

highlight_style = ParagraphStyle(
    'Highlight',
    parent=styles['BodyText'],
    fontSize=11,
    textColor=colors.HexColor('#D97706'),
    fontName='Helvetica-Bold',
    spaceAfter=6
)

table_header_style = ParagraphStyle(
    'TableHeader',
    parent=styles['BodyText'],
    fontSize=11,
    fontName='Helvetica-Bold',
    textColor=colors.whitesmoke,
    leading=14,
    spaceAfter=0,
    spaceBefore=0,
)

# Title Page
story.append(Spacer(1, 1.5*inch))
story.append(Paragraph("HR Payroll System", title_style))
story.append(Spacer(1, 0.2*inch))
story.append(Paragraph("User Guide", ParagraphStyle('Subtitle', parent=styles['Heading2'], fontSize=20, alignment=TA_CENTER, textColor=colors.HexColor('#6B7280'))))
story.append(Spacer(1, 0.1*inch))
story.append(Paragraph("Send Payslips • Mark as Paid • Email Operations", ParagraphStyle('SubtitleSmall', parent=styles['Normal'], fontSize=12, alignment=TA_CENTER, textColor=colors.HexColor('#9CA3AF'))))
story.append(Spacer(1, 1*inch))
story.append(Paragraph(f"Last Updated: {datetime.now().strftime('%B %d, %Y')}", ParagraphStyle('Footer', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER, textColor=colors.HexColor('#D1D5DB'))))

story.append(PageBreak())

# Table of Contents
story.append(Paragraph("Table of Contents", heading_style))
story.append(Spacer(1, 0.15*inch))
contents = [
    "1. Getting Started",
    "2. Sending Payslips to Employees",
    "3. Marking Payslips as Paid",
    "4. Sending Email When Marking as Paid",
    "5. Tips & Troubleshooting",
]
for item in contents:
    story.append(Paragraph(item, bullet_style))

story.append(PageBreak())

# Section 1: Getting Started
story.append(Paragraph("1. Getting Started", heading_style))
story.append(Spacer(1, 0.1*inch))

story.append(Paragraph("What is the Payroll System?", subheading_style))
story.append(Paragraph(
    "The Payroll System helps you manage employee payslips efficiently. You can send payslips to multiple employees at once, mark them as paid, and automatically email them to staff—all in one place.",
    body_style
))
story.append(Spacer(1, 0.1*inch))

story.append(Paragraph("Where do I find the payroll tools?", subheading_style))
story.append(Paragraph(
    "Look for the green toolbar buttons at the top of the payroll list:",
    body_style
))
story.append(Spacer(1, 0.08*inch))
story.append(Paragraph("<b>📧 Send Payslips</b> – Email payslips to employees", bullet_style))
story.append(Paragraph("<b>✓ Mark As Paid</b> – Mark payslips as paid and optionally email them", bullet_style))
story.append(Spacer(1, 0.1*inch))

story.append(Paragraph("Before You Start", subheading_style))
story.append(Paragraph(
    "Make sure you have at least one payroll record for the period you're working with. You should be logged in as an HR Administrator.",
    body_style
))

story.append(PageBreak())

# Section 2: Sending Payslips
story.append(Paragraph("2. Sending Payslips to Employees", heading_style))
story.append(Spacer(1, 0.1*inch))

story.append(Paragraph("What does this do?", subheading_style))
story.append(Paragraph(
    "Sends a payslip document to an employee via email. You can send to one person, a whole department, or everyone at once.",
    body_style
))
story.append(Spacer(1, 0.1*inch))

story.append(Paragraph("Step-by-Step Instructions", subheading_style))
story.append(Spacer(1, 0.08*inch))

steps = [
    ("<b>Step 1:</b> Go to the Payroll page and view your payslip list", "Look at the list of all payslips for the current period."),
    ("<b>Step 2:</b> Choose which payslips to send", "You have three options (see next section for details)."),
    ("<b>Step 3:</b> Click the <b>📧 Send Payslips</b> button", "A popup window will appear."),
    ("<b>Step 4:</b> Select your scope and confirm", "Choose from 'Selected', 'By Department', or 'All Payslips'."),
    ("<b>Step 5:</b> Wait for confirmation", "You'll see a message saying how many payslips were queued to send."),
]

for title, desc in steps:
    story.append(Paragraph(title, body_style))
    story.append(Paragraph(desc, bullet_style))
    story.append(Spacer(1, 0.05*inch))

story.append(Spacer(1, 0.1*inch))
story.append(Paragraph("Choosing Your Sending Scope", subheading_style))
story.append(Spacer(1, 0.08*inch))

scope_data = [
    [Paragraph("Scope", table_header_style), Paragraph("What It Does", table_header_style), Paragraph("When To Use", table_header_style)],
    [Paragraph("Selected Payslips", body_style), Paragraph("Sends to only the payslips you checked on the list", body_style), Paragraph("When you want to send to 2-3 specific people", body_style)],
    [Paragraph("By Department", body_style), Paragraph("Sends to all payslips from one department (e.g., Finance, HR, Sales)", body_style), Paragraph("When you want to send to an entire team", body_style)],
    [Paragraph("All Payslips", body_style), Paragraph("Sends to every payslip in the current period", body_style), Paragraph("When you want to send to everyone at once", body_style)],
]

scope_table = Table(scope_data, colWidths=[1.4*inch, 3.1*inch, 2.0*inch])
scope_table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#374151')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 11),
    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
    ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ('FONTSIZE', (0, 1), (-1, -1), 10),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
]))

story.append(scope_table)
story.append(Spacer(1, 0.15*inch))

story.append(Paragraph("📌 Tip: Selecting Individual Payslips", highlight_style))
story.append(Paragraph(
    "To send to specific people, check the boxes next to their names in the payroll table, then click 📧 Send Payslips and select \"Selected Payslips\".",
    bullet_style
))

story.append(PageBreak())

# Section 3: Marking as Paid
story.append(Paragraph("3. Marking Payslips as Paid", heading_style))
story.append(Spacer(1, 0.1*inch))

story.append(Paragraph("What does this do?", subheading_style))
story.append(Paragraph(
    "Updates the payslip status from 'Pending' to 'Paid' in the system. This records that you've released the payment to the employee. Like sending payslips, you can do this for selected staff, a department, or everyone.",
    body_style
))
story.append(Spacer(1, 0.1*inch))

story.append(Paragraph("Step-by-Step Instructions", subheading_style))
story.append(Spacer(1, 0.08*inch))

mark_steps = [
    ("<b>Step 1:</b> Select payslips to mark as paid", "Either check boxes or select a department/all."),
    ("<b>Step 2:</b> Click the <b>✓ Mark As Paid</b> button", "The button is green and located next to 'Send Payslips'."),
    ("<b>Step 3:</b> Choose your scope", "Same three options: 'Selected', 'By Department', or 'All Payslips'."),
    ("<b>Step 4:</b> (Optional) Check the email option", "See Section 4 below for details."),
    ("<b>Step 5:</b> Confirm", "Click 'Mark as Paid' to complete the action."),
    ("<b>Step 6:</b> Verify completion", "The payslip list will refresh, and the status should show 'Paid'."),
]

for title, desc in mark_steps:
    story.append(Paragraph(title, body_style))
    story.append(Paragraph(desc, bullet_style))
    story.append(Spacer(1, 0.05*inch))

story.append(Spacer(1, 0.1*inch))
story.append(Paragraph("Status Labels", subheading_style))
story.append(Spacer(1, 0.08*inch))

status_data = [
    ["Status", "Meaning"],
    ["Pending", "Payslip created but not yet marked as paid"],
    ["Paid", "Payment has been released to the employee"],
    ["Cancelled", "Payment was cancelled"],
]

status_table = Table(status_data, colWidths=[1.5*inch, 4*inch])
status_table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#374151')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 11),
    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ('FONTSIZE', (0, 1), (-1, -1), 10),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
]))

story.append(status_table)

story.append(PageBreak())

# Section 4: Email Option
story.append(Paragraph("4. Sending Email When Marking as Paid", heading_style))
story.append(Spacer(1, 0.1*inch))

story.append(Paragraph("What does this do?", subheading_style))
story.append(Paragraph(
    "When you mark payslips as paid, you have the option to automatically send the payslip document to employees via email at the same time. This is optional.",
    body_style
))
story.append(Spacer(1, 0.1*inch))

story.append(Paragraph("How to Use", subheading_style))
story.append(Spacer(1, 0.08*inch))

email_steps = [
    "Click ✓ Mark As Paid",
    "Select your scope (Selected, By Department, or All)",
    "Look for the checkbox that says: <b>'Also email payslip after marking as paid'</b>",
    "Check the box if you want to email payslips",
    "Click 'Mark as Paid'",
]

for i, step in enumerate(email_steps, 1):
    story.append(Paragraph(f"<b>{i}.</b> {step}", bullet_style))

story.append(Spacer(1, 0.15*inch))

story.append(Paragraph("When Should I Use This?", subheading_style))
story.append(Spacer(1, 0.08*inch))

when_email = [
    "✓ When you've just released the payment and want to notify employees immediately",
    "✓ When you haven't already sent payslips earlier in the month",
    "✗ When you already sent payslips separately (don't send twice!)",
    "✗ If you prefer to send payslips at a different time from marking as paid",
]

for item in when_email:
    story.append(Paragraph(item, bullet_style))

story.append(Spacer(1, 0.15*inch))

story.append(Paragraph("📌 Tip: Two-Step vs. One-Step", highlight_style))
story.append(Paragraph(
    "<b>Two-step process:</b> First send payslips with '📧 Send Payslips', then later mark as paid with '✓ Mark As Paid' (without email). This is useful if you want to give employees a few days' notice before marking as paid.",
    bullet_style
))
story.append(Spacer(1, 0.08*inch))
story.append(Paragraph(
    "<b>One-step process:</b> Use '✓ Mark As Paid' with the email option checked to do both in one action. Faster and simpler if timing doesn't matter.",
    bullet_style
))

story.append(PageBreak())

# Section 5: Tips & Troubleshooting
story.append(Paragraph("5. Tips & Troubleshooting", heading_style))
story.append(Spacer(1, 0.1*inch))

story.append(Paragraph("Common Questions", subheading_style))
story.append(Spacer(1, 0.08*inch))

faq = [
    ("What if I accidentally mark a payslip as paid?", 
     "Contact your HR Administrator. They may be able to change the status back to 'Pending' if needed."),
    
    ("How do I know if an email was sent successfully?", 
     "The system will show a confirmation message. If there's an error, you'll see an alert with more details."),
    
    ("Can I send to multiple departments at once?", 
     "Not in a single action. Use 'All Payslips' to send to everyone, or send to each department separately."),
    
    ("What if a payslip row is disabled or grayed out?", 
     "It may have already been marked as paid, or there might be an issue with the payslip data. Contact HR support if you're unsure."),
    
    ("Can I undo an action?", 
     "Once you click the button and see the confirmation, the action is processed. Email actions cannot be undone, but status changes may be reversible—ask your HR Administrator."),
    
    ("Why do some buttons appear disabled?", 
     "Buttons become disabled when the required selections aren't made (e.g., 'Send Payslips' is disabled if you haven't selected any payslips in 'Selected' mode)."),
]

for q, a in faq:
    story.append(Paragraph(f"<b>Q: {q}</b>", body_style))
    story.append(Paragraph(f"<b>A:</b> {a}", bullet_style))
    story.append(Spacer(1, 0.08*inch))

story.append(PageBreak())

# Best Practices
story.append(Paragraph("Best Practices", subheading_style))
story.append(Spacer(1, 0.08*inch))

practices = [
    "Always double-check your selection before clicking any button.",
    "Send payslips early in the month so employees have time to review before the payday.",
    "Mark payslips as paid only after confirming payments have been made.",
    "Keep a record of when you sent payslips and marked them as paid.",
    "If you're new to this system, start with 'Selected' scope to practice with one or two payslips.",
    "Contact HR Admin if you see error messages or unexpected behavior.",
]

for practice in practices:
    story.append(Paragraph(f"• {practice}", bullet_style))

story.append(Spacer(1, 0.2*inch))

# Build PDF
doc.build(story)
print(f"✅ PDF Guide created successfully: {pdf_path}")
print(f"📄 Location: {pdf_path}")
