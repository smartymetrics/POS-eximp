import os

path = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\hrm-portal\src\App.jsx'

try:
    with open(path, 'rb') as f:
        content = f.read().decode('utf-8', errors='ignore')
    
    # 1. Add Animation for Launch Review
    # I'll add a 'launching' state and a nice visual feedback
    content = content.replace('const [launching, setLaunching] = useState(false);', 'const [launching, setLaunching] = useState(false);\n  const [launched, setLaunched] = useState(false);')
    # Wait, launching was likely already there. Let's check.
    
    # I'll modify launchReview to show a success state
    old_launch = """      await apiFetch(`${API_BASE}/hr/peer-reviews`, { method: "POST", body: JSON.stringify(form) });
      setForm({ title: "", reviewee_id: "", reviewer_ids: [], questions: ["What are this person's key strengths?", "What areas could they improve upon?", "How well do they collaborate with the team?"], deadline: "", is_anonymous: true });
      setShowCreate(false); refresh();
    } catch (e) { alert(e.message); } finally { setLaunching(false); }
  };"""
    
    new_launch = """      await apiFetch(`${API_BASE}/hr/peer-reviews`, { method: "POST", body: JSON.stringify(form) });
      setLaunched(true);
      setTimeout(() => {
        setForm({ title: "", reviewee_id: "", reviewer_ids: [], questions: ["What are this person's key strengths?", "What areas could they improve upon?", "How well do they collaborate with the team?"], deadline: "", is_anonymous: true });
        setShowCreate(false); setLaunched(false); refresh();
      }, 1500);
    } catch (e) { alert(e.message); } finally { setLaunching(false); }
  };"""
    content = content.replace(old_launch, new_launch)

    # Add the "Launched" success UI in the modal
    modal_check = '{launched ? (\n            <div style={{ textAlign: "center", padding: "40px 0", animation: "scaleUp 0.5s ease" }}>\n              <div style={{ fontSize: 60, marginBottom: 16 }}>🚀</div>\n              <div style={{ fontSize: 18, fontWeight: 800, color: "#4ADE80" }}>Review Launched!</div>\n              <div style={{ fontSize: 13, color: C.sub, marginTop: 8 }}>Notifications have been sent to reviewers.</div>\n            </div>\n          ) : (\n            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>'
    
    content = content.replace('<div style={{ display: "flex", flexDirection: "column", gap: 16 }}>', modal_check)
    # Close the div
    content = content.replace('<button className="bp" onClick={launchReview} disabled={launching}>{launching ? "Launching..." : "Launch Review"}</button>\n            </div>', 
                              '<button className="bp" onClick={launchReview} disabled={launching}>{launching ? "Launching..." : "Launch Review"}</button>\n            </div>\n          )}')

    # 2. Fix the submitReview error handling (DON'T mark as submitted if it fails)
    old_submit = """      } catch (e) {
        // Even if API fails, mark as submitted locally so the UI updates
        setSubmitted(prev => ({ ...prev, [activeReview.id]: true }));
        setActiveReview(null);
        setAnswers({});
        window.dispatchEvent(new CustomEvent("peer-review-updated"));
      }"""
    
    new_submit = """      } catch (e) {
        alert("Submission failed: " + e.message);
        // Do NOT mark as submitted locally if it failed
      }"""
    content = content.replace(old_submit, new_submit)

    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    print("Frontend updated with animation and error reporting.")
except Exception as e:
    print(f"Error: {e}")
