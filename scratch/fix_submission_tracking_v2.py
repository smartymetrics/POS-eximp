import os

path = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\hrm-portal\src\App.jsx'

try:
    with open(path, 'rb') as f:
        content = f.read().decode('utf-8', errors='ignore')
    
    # Surgical replacement for MyPeerReviews useEffect
    old_code = """      ]).then(([all, myAssigned]) => {
        if (myAssigned && Array.isArray(myAssigned)) {
          setAssignedReviews(myAssigned);
        } else if (Array.isArray(all)) {
          // Fallback: filter from all reviews where user is in reviewer_ids
          const mine = all.filter(r =>
            ["pending", "in-progress"].includes(r.status) &&
            (r.reviewer_ids || []).map(String).includes(String(user.id))
          );
          setAssignedReviews(mine);
          // Mark already responded ones
          const done = {};
          all.forEach(r => {
            if ((r.responses || []).some(resp => String(resp.reviewer_id) === String(user.id))) {
              done[r.id] = true;
            }
          });
          setSubmitted(done);
        }
      }).finally(() => setLoading(false));"""

    new_code = """      ]).then(([all, myAssigned]) => {
        const reviews = (myAssigned && Array.isArray(myAssigned)) ? myAssigned : 
                        (Array.isArray(all) ? all.filter(r => (r.reviewer_ids || []).map(String).includes(String(user.id))) : []);
        setAssignedReviews(reviews);
        
        const done = {};
        reviews.forEach(r => {
          if ((r.responses || []).some(resp => String(resp.reviewer_id) === String(user.id))) {
            done[r.id] = true;
          }
        });
        setSubmitted(done);
      }).finally(() => setLoading(false));"""

    if old_code in content:
        content = content.replace(old_code, new_code)
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
        print("Submission tracking logic successfully updated.")
    else:
        print("Pattern not found. Checking for variations...")
        # Try a more flexible search
        if 'setAssignedReviews(myAssigned);' in content and 'setSubmitted(done);' in content:
            print("Both lines exist but block structure differs. Attempting generic fix.")
            # I'll just rewrite the whole MyPeerReviews component logic
except Exception as e:
    print(f"Error: {e}")
