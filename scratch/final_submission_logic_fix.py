import os

path = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\hrm-portal\src\App.jsx'

try:
    with open(path, 'rb') as f:
        content = f.read().decode('utf-8', errors='ignore')
    
    # Corrected MyPeerReviews useEffect to process 'done' state regardless of the list source
    corrected_logic = """      ]).then(([all, myAssigned]) => {
        const reviews = (myAssigned && Array.isArray(myAssigned)) ? myAssigned : (Array.isArray(all) ? all.filter(r => (r.reviewer_ids || []).map(String).includes(String(user.id))) : []);
        setAssignedReviews(reviews);
        
        const done = {};
        reviews.forEach(r => {
          if (r.submitted_by_me || (r.responses || []).some(resp => String(resp.reviewer_id) === String(user.id))) {
            done[r.id] = true;
          }
        });
        setSubmitted(done);
      }).finally(() => setLoading(false));"""

    # We'll replace the block from Promise.all down to finally
    old_logic_pattern = """      Promise.all([
        apiFetch(`${API_BASE}/hr/peer-reviews`).catch(() => []),
        apiFetch(`${API_BASE}/hr/peer-reviews/my-assignments?staff_id=${user.id}`).catch(() => null),
      ]).then(([all, myAssigned]) => {
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
            if (r.submitted_by_me || (r.responses || []).some(resp => String(resp.reviewer_id) === String(user.id))) {
              done[r.id] = true;
            }
          });
          setSubmitted(done);
        }
      }).finally(() => setLoading(false));"""

    if old_logic_pattern in content:
        content = content.replace(old_logic_pattern, """      Promise.all([
        apiFetch(`${API_BASE}/hr/peer-reviews`).catch(() => []),
        apiFetch(`${API_BASE}/hr/peer-reviews/my-assignments?staff_id=${user.id}`).catch(() => null),
      ]).then(([all, myAssigned]) => {
        const reviews = (myAssigned && Array.isArray(myAssigned)) ? myAssigned : (Array.isArray(all) ? all.filter(r => (r.reviewer_ids || []).map(String).includes(String(user.id))) : []);
        setAssignedReviews(reviews);
        
        const done = {};
        reviews.forEach(r => {
          if (r.submitted_by_me || (r.responses || []).some(resp => String(resp.reviewer_id) === String(user.id))) {
            done[r.id] = true;
          }
        });
        setSubmitted(done);
      }).finally(() => setLoading(false));""")
        
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
        print("Final submission tracking fix applied.")
    else:
        print("Pattern not found. Using generic component rewrite.")
        # I'll just rewrite the whole component again but with more care
        start = content.find('function MyPeerReviews')
        end = content.find('const openReview', start)
        if start != -1 and end != -1:
            new_comp = """function MyPeerReviews({ user }) {
    const { dark } = useTheme(); const C = dark ? DARK : LIGHT;
    const [assignedReviews, setAssignedReviews] = useState([]);
    const [loading, setLoading] = useState(true);
    const [activeReview, setActiveReview] = useState(null); 
    const [answers, setAnswers] = useState({});
    const [submitting, setSubmitting] = useState(false);
    const [submitted, setSubmitted] = useState({});

    useEffect(() => {
      Promise.all([
        apiFetch(`${API_BASE}/hr/peer-reviews`).catch(() => []),
        apiFetch(`${API_BASE}/hr/peer-reviews/my-assignments?staff_id=${user.id}`).catch(() => null),
      ]).then(([all, myAssigned]) => {
        const reviews = (myAssigned && Array.isArray(myAssigned)) ? myAssigned : (Array.isArray(all) ? all.filter(r => (r.reviewer_ids || []).map(String).includes(String(user.id))) : []);
        setAssignedReviews(reviews);
        
        const done = {};
        reviews.forEach(r => {
          if (r.submitted_by_me || (r.responses || []).some(resp => String(resp.reviewer_id) === String(user.id))) {
            done[r.id] = true;
          }
        });
        setSubmitted(done);
      }).finally(() => setLoading(false));
    }, [user.id]);

    """
            content = content[:start] + new_comp + content[end:]
            with open(path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(content)
            print("Component rewritten successfully.")

except Exception as e:
    print(f"Error: {e}")
