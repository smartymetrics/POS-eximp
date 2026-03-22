import os
import resend
from dotenv import load_dotenv

load_dotenv()
resend.api_key = os.getenv("RESEND_API_KEY")

def test_send():
    print("Testing Resend with bytes...")
    try:
        r = resend.Emails.send({
            "from": "onboarding@resend.dev", # Use a verified domain or onboarding
            "to": "delivered@resend.dev",
            "subject": "Test Attachment",
            "html": "<strong>Testing attachment format</strong>",
            "attachments": [
                {
                    "filename": "test.pdf",
                    "content": b"PDF content"
                }
            ]
        })
        print("Success with bytes:", r)
    except Exception as e:
        print("Failed with bytes:", e)

    print("\nTesting Resend with list of ints...")
    try:
        r = resend.Emails.send({
            "from": "onboarding@resend.dev",
            "to": "delivered@resend.dev",
            "subject": "Test Attachment (List)",
            "html": "<strong>Testing attachment format</strong>",
            "attachments": [
                {
                    "filename": "test_list.pdf",
                    "content": list(b"PDF content")
                }
            ]
        })
        print("Success with list:", r)
    except Exception as e:
        print("Failed with list:", e)

if __name__ == "__main__":
    test_send()
