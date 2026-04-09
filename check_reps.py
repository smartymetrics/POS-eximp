from database import get_db

def list_reps():
    db = get_db()
    res = db.table("sales_reps").select("name, email").limit(5).execute()
    print(res.data)

if __name__ == "__main__":
    list_reps()
