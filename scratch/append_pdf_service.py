import os

new_code = """

def generate_matter_pdf(matter_id: str, html_content: str, css_content: str) -> bytes:
    \"\"\"
    Generates a professional PDF for a personnel matter.
    Injects global CSS for multi-page headers/footers and branded frames.
    \"\"\"
    # Create the full HTML document with Print-specific styles
    full_html = f\"\"\"
    <html>
    <head>
        <style>
            @page {{
                size: A4;
                margin: 0;
            }}
            body {{
                margin: 0;
                padding: 0;
                font-family: 'Inter', sans-serif;
            }}
            /* Global Footer on every page */
            .page-footer-segment {{
                position: fixed;
                bottom: 0;
                left: 0;
                right: 0;
                width: 100%;
                height: 12px;
                display: block;
                z-index: 1000;
            }}
            .footer-black {{ float: left; width: 50%; height: 100%; background: #000; }}
            .footer-gold {{ float: left; width: 50%; height: 100%; background: #C47D0A; }}
            
            .page-content {{
                padding: 0;
                position: relative;
            }}
            {css_content}
        </style>
    </head>
    <body>
        <div class="page-content">
            {html_content}
        </div>
        <!-- Multi-page footer segments -->
        <div class="page-footer-segment">
            <div class="footer-black"></div>
            <div class="footer-gold"></div>
        </div>
    </body>
    </html>
    \"\"\"
    return _render_with_weasyprint(full_html)
"""

with open('pdf_service.py', 'a', encoding='utf-8') as f:
    f.write(new_code)
print("Updated successfully")
