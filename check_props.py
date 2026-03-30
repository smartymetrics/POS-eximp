import os
from database import get_db

db = get_db()
try:
    res = db.table("properties").select("*").limit(1).execute()
    print("Properties data:", res.data)
except Exception as e:
    print("Error:", e)
