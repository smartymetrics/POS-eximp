import re

path = r'c:\Users\HP USER\Documents\Data Analyst\pos-eximp-fresh\routers\marketing_webhooks.py'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace db.table with await db_execute(lambda: db.table
# and \n        await db_execute(lambda: }).eq with \n        }).eq
# Wait, it's easier to use regex.

# We want to match:
# db.table("...")(.update|.insert)({
#   ...
# await db_execute(lambda: })...execute())

pattern = re.compile(r'(?P<indent>[ \t]*)db\.table\((?P<args>.*?)\)\.(?P<method>update|insert)\(\{(?P<inside>.*?)(?P<indent2>[ \t]*)await db_execute\(lambda: \}\)', re.DOTALL)

def repl(m):
    indent = m.group('indent')
    args = m.group('args')
    method = m.group('method')
    inside = m.group('inside')
    indent2 = m.group('indent2')
    
    return f"{indent}await db_execute(lambda: db.table({args}).{method}({{{inside}{indent2}}})"

new_content = pattern.sub(repl, content)

with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Fixed syntax errors in marketing_webhooks.py")
