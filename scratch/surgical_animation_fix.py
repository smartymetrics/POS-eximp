import os

path = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\hrm-portal\src\App.jsx'

try:
    with open(path, 'rb') as f:
        content = f.read().decode('utf-8', errors='ignore')
    
    # 1. Add CSS Animation (Safe way)
    scaleUp = 'const scaleUp = `@keyframes scaleUp { from { transform: scale(0.8); opacity: 0; } to { transform: scale(1); opacity: 1; } }`;'
    import_line = "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@700&display=swap');"
    if scaleUp not in content:
        content = content.replace('const GS = dark => {', f'const GS = dark => {{\n    {scaleUp}')
        content = content.replace(import_line, import_line + '\n      ${scaleUp}')

    # 2. Add States to PeerReviews360
    # Find PeerReviews360 start
    pr_start = content.find('function PeerReviews360')
    if pr_start != -1:
        view_review_state = 'const [viewReview, setViewReview] = useState(null);'
        pos = content.find(view_review_state, pr_start)
        if pos != -1:
            content = content[:pos+len(view_review_state)] + '\n    const [launching, setLaunching] = useState(false);\n    const [launched, setLaunched] = useState(false);' + content[pos+len(view_review_state):]

    # 3. Update launchReview function (Targeting the one inside PeerReviews360)
    old_launch_logic = """      try {
        await apiFetch(`${API_BASE}/hr/peer-reviews`, {
          method: "POST",
          body: JSON.stringify({ ...form, questions: qs })
        });
        setShowCreate(false);
        setForm({ reviewee_id: "", reviewer_ids: [], title: "", questions: ["""
    
    new_launch_logic = """      setLaunching(true);
      try {
        await apiFetch(`${API_BASE}/hr/peer-reviews`, {
          method: "POST",
          body: JSON.stringify({ ...form, questions: qs })
        });
        setLaunched(true);
        setTimeout(() => {
          setShowCreate(false);
          setLaunched(false);
          setForm({ reviewee_id: "", reviewer_ids: [], title: "", questions: ["""
    
    # Use index to ensure we are in PeerReviews360
    launch_func_pos = content.find('const launchReview = async () =>', pr_start)
    if launch_func_pos != -1:
        block_end = content.find('refresh();', launch_func_pos)
        content = content.replace(old_launch_logic, new_launch_logic)
        # Add finally block to THAT specific launchReview
        content = content.replace('refresh();\n      } catch (e) {', 'refresh();\n      } catch (e) { } finally { setLaunching(false); }')

    # 4. Update the Modal UI (Targeting the one inside PeerReviews360)
    # The modal follows the launchReview function
    modal_title = 'title="Launch 360' # Use partial to avoid character mangling issues
    modal_pos = content.find(modal_title, pr_start)
    if modal_pos != -1:
        div_pos = content.find('<div style={{ display: "flex", flexDirection: "column", gap: 16 }}>', modal_pos)
        if div_pos != -1:
            ui_replacement = """{launched ? (
              <div style={{ textAlign: "center", padding: "40px 0", animation: "scaleUp 0.5s ease" }}>
                <div style={{ fontSize: 60, marginBottom: 16 }}>🚀</div>
                <div style={{ fontSize: 20, fontWeight: 900, color: "#4ADE80" }}>Review Launched!</div>
                <div style={{ fontSize: 13, color: C.sub, marginTop: 8 }}>Notifications have been sent to reviewers.</div>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>"""
            content = content[:div_pos] + ui_replacement + content[div_pos+len('<div style={{ display: "flex", flexDirection: "column", gap: 16 }}>'):]
            
            # Close the launched ternary
            btn_text = 'Launch Review</button>'
            btn_pos = content.find(btn_text, modal_pos)
            if btn_pos != -1:
                # Find the next </div> after the button
                end_div_pos = content.find('</div>', btn_pos)
                if end_div_pos != -1:
                    content = content[:end_div_pos+len('</div>')] + '\n            )}' + content[end_div_pos+len('</div>'):]

    # 5. Fix submitReview in MyPeerReviews
    mpr_start = content.find('function MyPeerReviews')
    if mpr_start != -1:
        submit_pos = content.find('const submitReview = async () =>', mpr_start)
        if submit_pos != -1:
            old_catch = """      } catch (e) {
        // Even if API fails, mark as submitted locally so the UI updates
        setSubmitted(prev => ({ ...prev, [activeReview.id]: true }));
        setActiveReview(null);
        setAnswers({});
        window.dispatchEvent(new CustomEvent("peer-review-updated"));
      }"""
            new_catch = """      } catch (e) {
        alert("Submission failed: " + e.message);
      }"""
            content = content.replace(old_catch, new_catch)

    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    print("Surgical fix successful.")
except Exception as e:
    print(f"Error: {e}")
