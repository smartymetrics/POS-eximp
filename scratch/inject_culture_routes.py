
import os

file_path = r"c:\Users\HP USER\Documents\Data Analyst\pos-eximp-cloves\routers\hr.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

culture_routes = """
# ─── ENGAGEMENT & CULTURE ─────────────────────────────────────────────────────

class SurveyCreate(BaseModel):
    title: str
    description: Optional[str] = None
    questions: list # list of strings

class SurveyResponseSubmit(BaseModel):
    answers: dict
    is_anonymous: bool = True

@router.get("/culture/surveys")
async def get_surveys(current_admin: dict = Depends(verify_token)):
    db = get_db()
    
    # 1. Fetch active surveys
    surveys = await db_execute(lambda: db.table("engagement_surveys").select("*").order("created_at", desc=True).execute())
    
    # 2. Fetch responses if HR to calculate completion rates
    user_roles = current_admin.get("role", "").split(",")
    is_hr = any(r in ["admin", "hr_admin", "operations"] for r in user_roles)
    
    if is_hr:
        responses = await db_execute(lambda: db.table("survey_responses").select("survey_id, answers").execute())
        resp_map = {}
        for r in responses.data:
            sid = r["survey_id"]
            if sid not in resp_map: resp_map[sid] = []
            resp_map[sid].append(r["answers"])
            
        for s in surveys.data:
            s["responses"] = resp_map.get(s["id"], [])
    
    return surveys.data

@router.post("/culture/surveys", status_code=status.HTTP_201_CREATED)
async def create_survey(survey: SurveyCreate, current_admin: dict = Depends(verify_token)):
    user_roles = current_admin.get("role", "").split(",")
    if "admin" not in user_roles and "hr_admin" not in user_roles:
         raise HTTPException(status_code=403, detail="HR only")
         
    db = get_db()
    res = await db_execute(lambda: db.table("engagement_surveys").insert({
        "title": survey.title,
        "description": survey.description,
        "questions": survey.questions
    }).execute())
    return res.data[0]

@router.post("/culture/surveys/{survey_id}/respond", status_code=status.HTTP_201_CREATED)
async def submit_survey_response(survey_id: str, response: SurveyResponseSubmit, current_admin: dict = Depends(verify_token)):
    db = get_db()
    
    # Check if already responded (if not anonymous, or strictly enforce one per staff)
    # We will just allow it, but in a real app you'd enforce unique limits if not anonymous.
    
    payload = {
        "survey_id": survey_id,
        "answers": response.answers,
        "is_anonymous": response.is_anonymous,
        "staff_id": None if response.is_anonymous else current_admin["sub"]
    }
    
    res = await db_execute(lambda: db.table("survey_responses").insert(payload).execute())
    return res.data[0]
"""

if "ENGAGEMENT & CULTURE" not in content:
    content += "\n" + culture_routes + "\n"

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Injected Engagement & Culture routes")
