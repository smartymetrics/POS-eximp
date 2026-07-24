import sys
import os

# Adjust path to import from pos-eximp-fresh
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from marketing_service import optimize_html_for_mobile

def test_responsive():
    # Mock HTML with nested non-responsive image
    html_input = """
    <html>
      <head>
        <title>Test Email</title>
      </head>
      <body>
        <h1>Coinfield Estate Launch</h1>
        <img src="https://images.unsplash.com/photo-1500382017468-9049fee74a62" width="100%" style="display:block;border:none;" alt="Coinfield Estate" />
        <img src="logo.png" style="height:36px; margin-bottom:16px;" />
      </body>
    </html>
    """
    
    output = optimize_html_for_mobile(html_input)
    print("PROCESSED HTML OUTPUT:")
    print(output)
    
    # Assertions
    assert "max-width: 100% !important" in output, "Should inject max-width in full-width image style"
    assert "height: auto !important" in output, "Should inject height: auto in full-width image style"
    assert "viewport" in output, "Should inject viewport meta tag"
    assert "-webkit-text-size-adjust" in output, "Should inject text-size-adjust styles"
    
    # Make sure logo image (not 100% width) is NOT modified to override height: auto !important
    assert 'logo.png" style="height:36px; margin-bottom:16px;"' in output or 'logo.png" style="height:36px; margin-bottom:16px;' in output
    print("\n[SUCCESS] Verification Successful!")

if __name__ == '__main__':
    test_responsive()
