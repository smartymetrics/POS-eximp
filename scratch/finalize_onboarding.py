import re

path = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\hrm-portal\src\App.jsx'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove onboarding_checklists from sidebar
# Match the line and whitespace
content = re.sub(r'\s*{\s*id:\s*"onboarding_checklists",\s*icon:\s*"tasks",\s*label:\s*"Onboarding Checklists"\s*},?\n', '', content)

# 2. Add tab state to OnboardingHub
# Find the line after const [showNew, setShowNew] = useState(false);
pattern = r'(const \[showNew, setShowNew\] = useState\(false\);)'
content = re.sub(pattern, r'\1\n  const [tab, setTab] = useState("progress");', content)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Finalized Onboarding Hub unification.")
