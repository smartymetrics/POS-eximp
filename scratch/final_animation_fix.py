import os

path = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\hrm-portal\src\App.jsx'

try:
    with open(path, 'rb') as f:
        content = f.read().decode('utf-8', errors='ignore')
    
    # 1. Add states to PeerReviews360
    content = content.replace('const [viewReview, setViewReview] = useState(null);', 
                              'const [viewReview, setViewReview] = useState(null);\n    const [launching, setLaunching] = useState(false);\n    const [launched, setLaunched] = useState(false);')

    # 2. Update launchReview function
    old_launch = """      try {
        await apiFetch(`${API_BASE}/hr/peer-reviews`, {
          method: "POST",
          body: JSON.stringify({ ...form, questions: qs })
        });
        setShowCreate(false);
        setForm({ reviewee_id: "", reviewer_ids: [], title: "", questions: ["How would you rate this person's communication skills?", "How effectively does this person collaborate with the team?", "What is this person's greatest strength?", "What area should this person focus on improving?", "Would you recommend this person for a leadership role? Why?"], deadline: "", is_anonymous: true });
        refresh();"""

    new_launch = """      setLaunching(true);
      try {
        await apiFetch(`${API_BASE}/hr/peer-reviews`, {
          method: "POST",
          body: JSON.stringify({ ...form, questions: qs })
        });
        setLaunched(true);
        setTimeout(() => {
          setShowCreate(false);
          setLaunched(false);
          setForm({ reviewee_id: "", reviewer_ids: [], title: "", questions: ["How would you rate this person's communication skills?", "How effectively does this person collaborate with the team?", "What is this person's greatest strength?", "What area should this person focus on improving?", "Would you recommend this person for a leadership role? Why?"], deadline: "", is_anonymous: true });
          refresh();
        }, 1500);"""
    
    content = content.replace(old_launch, new_launch)
    
    # Add finally block
    content = content.replace('refresh();\n      } catch (e) {', 'refresh();\n      } catch (e) { } finally { setLaunching(false); }')

    # 3. Update the modal UI to use launched state
    content = content.replace('title="Launch 360A Peer Review" width={680}>\n            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>', 
                              'title="Launch 360A Peer Review" width={680}>\n            {launched ? (\n              <div style={{ textAlign: "center", padding: "40px 0", animation: "scaleUp 0.5s ease" }}>\n                <div style={{ fontSize: 60, marginBottom: 16 }}>🚀</div>\n                <div style={{ fontSize: 20, fontWeight: 900, color: "#4ADE80" }}>Review Launched!</div>\n                <div style={{ fontSize: 13, color: C.sub, marginTop: 8 }}>Notifications have been sent to reviewers.</div>\n              </div>\n            ) : (\n              <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>')

    # Fix button and close div
    content = content.replace('Launch Review</button>\n            </div>', 'Launch Review</button>\n              </div>\n            )}')

    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    print("Animation and logic fully integrated.")
except Exception as e:
    print(f"Error: {e}")
