import sys, os
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage_service import generate_signed_url

path = "portal_claims/2cecedd1-2209-47aa-aa30-6d67e4ba7a0a_c4fea747b2754c0fb2ebcd2753f781d1.png"
url = generate_signed_url("Cloud Infrastructure", path)

print("Raw generated URL:", repr(url))
print("Contains raw space ' ':", " " in url)
print("Contains '%20':", "%20" in url)
