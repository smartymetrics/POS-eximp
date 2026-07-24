import re

path = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\hrm-portal\src\App.jsx'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

start = content.find('function HRCalendarView')
end = content.find('function ', start + 10)
print(content[start:end])
