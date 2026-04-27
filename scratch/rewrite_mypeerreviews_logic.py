import os

path = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\hrm-portal\src\App.jsx'

try:
    with open(path, 'rb') as f:
        content = f.read().decode('utf-8', errors='ignore')
    
    # Let's find the start of MyPeerReviews and the start of useEffect
    start_marker = 'function MyPeerReviews'
    if start_marker not in content:
        print("Marker not found")
        exit()
        
    # I'll just replace the entire MyPeerReviews component to be safe
    # It starts at 'function MyPeerReviews' and ends before 'const openReview'
    
    component_start = content.find('function MyPeerReviews')
    logic_end = content.find('const openReview', component_start)
    
    new_component_logic = """function MyPeerReviews({ user }) {
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
      }).finally(() => setLoading(false));
    }, [user.id]);

    // When HR cancels a review, remove it from the employee's pending list immediately
    useEffect(() => {
      const handler = (e) => {
        const cancelledId = e.detail?.id;
        if (cancelledId) {
          setAssignedReviews(prev => prev.filter(r => String(r.id) !== String(cancelledId)));
          setActiveReview(prev => (prev && String(prev.id) === String(cancelledId) ? null : prev));
        }
      };
      window.addEventListener("peer-review-cancelled", handler);
      return () => window.removeEventListener("peer-review-cancelled", handler);
    }, []);

    """
    
    content = content[:component_start] + new_component_logic + content[logic_end:]

    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    print("Component logic completely replaced and fixed.")
except Exception as e:
    print(f"Error: {e}")
