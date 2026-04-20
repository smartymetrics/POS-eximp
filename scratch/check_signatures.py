from database import get_db
import json

def check_sigs():
    db = get_db()
    res = db.table("company_signatures").select("*").eq("is_active", True).execute()
    print(json.dumps(res.data, indent=2))

if __name__ == "__main__":
    check_sigs()
