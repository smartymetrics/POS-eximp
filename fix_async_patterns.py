"""
Targeted fix for the exact two broken patterns created by the automation scripts.

Pattern 1 (missing ) before .data/.count):
    (await db_execute(lambda: EXPR.execute().data or []
    → (await db_execute(lambda: EXPR.execute())).data or []

Pattern 2 (missing ) on query builder line):
    query = query.method(arg
    → query = query.method(arg)
    where the next line is blank or starts with something else

Pattern 3 (extra ) in result):
    query.execute()))).data → query.execute())).data (already fixed but check)
"""
import re, os

def count_parens(s):
    opens = s.count('(')
    closes = s.count(')')
    return opens - closes  # positive = needs more closing

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    original = content

    # Fix Pattern 1: `(await db_execute(lambda: ...execute().data`
    # → `(await db_execute(lambda: ...execute())).data`
    def fix_pattern1(m):
        prefix = m.group(1)
        expr = m.group(2)
        suffix = m.group(3)
        # expr ends with .execute() — we need to add )) before .data
        return f"{prefix}{expr})){suffix}"

    # Matches: (await db_execute(lambda: EXPR.execute().ATTR
    content = re.sub(
        r'(\(await db_execute\(lambda: )(.+?\.execute\(\))(\.(?:data|count))',
        fix_pattern1,
        content
    )

    # Fix Pattern 2: query builder line missing closing paren
    # e.g.  `        query = query.eq("is_paid", is_paid\n\n    res = await`
    # The line ends without ) but has unbalanced open parens
    lines = content.split('\n')
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Check if this is an assignment where the RHS has unbalanced parens
        m = re.match(r'^(\s*)(\w[\w.]*\s*=\s*.+)$', line)
        if m and not line.strip().startswith('#') and not line.strip().startswith('"""'):
            imbalance = count_parens(line)
            if imbalance > 0 and not line.rstrip().endswith('\\'):
                # Check that the next non-empty line is NOT a continuation
                next_content = ''
                for j in range(i+1, min(i+3, len(lines))):
                    stripped = lines[j].strip()
                    if stripped:
                        next_content = stripped
                        break
                # If next line doesn't start with . or ) or \, this is a standalone broken line
                if next_content and not next_content.startswith('.') and not next_content.startswith(')') and not next_content.startswith('\\'):
                    line = line + ')' * imbalance
                    new_lines.append(line)
                    i += 1
                    continue
        new_lines.append(line)
        i += 1

    content = '\n'.join(new_lines)

    # Fix double-paren execute followed by .data/_count
    content = content.replace('.execute()))).data', '.execute())).data')
    content = content.replace('.execute()))).count', '.execute())).count')

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False


if __name__ == '__main__':
    routers_dir = 'routers'
    fixed = []
    for filename in sorted(os.listdir(routers_dir)):
        if filename.endswith('.py'):
            path = os.path.join(routers_dir, filename)
            if fix_file(path):
                fixed.append(filename)
    print(f"Fixed {len(fixed)} files: {', '.join(fixed)}")
