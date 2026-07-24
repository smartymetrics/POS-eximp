import os

path = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\hrm-portal\src\App.jsx'

try:
    with open(path, 'rb') as f:
        content = f.read().decode('utf-8', errors='ignore')
    
    # Fix the useEffect in MyPeerReviews to correctly identify submitted reviews
    old_code = """      ]).then(([all, myAssigned]) => {
        if (myAssigned && Array.isArray(myAssigned)) {
          setAssignedReviews(myAssigned);
        } else if (Array.isArray(all)) {"""
        
    new_code = """      ]).then(([all, myAssigned]) => {
        const reviewsToProcess = (myAssigned && Array.isArray(myAssigned)) ? myAssigned : (Array.isArray(all) ? all : []);
        setAssignedReviews(reviewsToProcess);
        
        // Correctly mark which ones are already responded to
        const done = {};
        reviewsToProcess.forEach(r => {
          if ((r.responses || []).some(resp => String(resp.reviewer_id) === String(user.id))) {
            done[r.id] = true;
          }
        });
        setSubmitted(done);
        
        if (!myAssigned && Array.isArray(all)) {"""

    # Actually the logic in App.jsx currently is:
    # if (myAssigned && Array.isArray(myAssigned)) {
    #   setAssignedReviews(myAssigned);
    # } else if (Array.isArray(all)) {
    #   const mine = all.filter(r => ...);
    #   setAssignedReviews(mine);
    #   ...
    # }

    # Let's simplify and make it robust.
    
    target_pattern = r'Promise\.all\(\[\s+apiFetch\(`${API_BASE}/hr/peer-reviews`\)\.catch\(\(\) => \[\]\),\s+apiFetch\(`${API_BASE}/hr/peer-reviews/my-assignments\?staff_id=\${user\.id}`\)\.catch\(\(\) => null\),\s+\]\)\.then\(\(\[all, myAssigned\]\) => \{'
    
    replacement = """Promise.all([
        apiFetch(`${API_BASE}/hr/peer-reviews`).catch(() => []),
        apiFetch(`${API_BASE}/hr/peer-reviews/my-assignments?staff_id=${user.id}`).catch(() => null),
      ]).then(([all, myAssigned]) => {
        const targetReviews = (myAssigned && Array.isArray(myAssigned)) ? myAssigned : 
                             (Array.isArray(all) ? all.filter(r => (r.reviewer_ids || []).map(String).includes(String(user.id))) : []);
        
        setAssignedReviews(targetReviews);
        
        const done = {};
        targetReviews.forEach(r => {
          if ((r.responses || []).some(resp => String(resp.reviewer_id) === String(user.id))) {
            done[r.id] = true;
          }
        });
        setSubmitted(done);
      })"""

    # I'll use a simpler replace
    content = content.replace('      ]).then(([all, myAssigned]) => {\n        if (myAssigned && Array.isArray(myAssigned)) {\n          setAssignedReviews(myAssigned);\n        } else if (Array.isArray(all)) {', 
                              '      ]).then(([all, myAssigned]) => {\n        const reviews = (myAssigned && Array.isArray(myAssigned)) ? myAssigned : (Array.isArray(all) ? all.filter(r => (r.reviewer_ids || []).map(String).includes(String(user.id))) : []);\n        setAssignedReviews(reviews);\n        const done = {};\n        reviews.forEach(r => {\n          if ((r.responses || []).some(resp => String(resp.reviewer_id) === String(user.id))) {\n            done[r.id] = true;\n          }\n        });\n        setSubmitted(done);\n        if (false) { // Skip old logic')

    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    print("Fix applied")
except Exception as e:
    print(f"Error: {e}")
