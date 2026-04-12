"""
SAFE async migration v2 - handles all execute() patterns including .data/.count suffixes.
Self-verifying: reverts any file that fails to compile after modification.
"""
import re, os, py_compile, shutil

ROUTERS_DIR = 'routers'
SKIP_FILES = {
    'crm_professional_old.py', 'crm_professional_old_2.py',
    'crm_professional_olsld_v3.py', 'sales_reps_old.py'
}

# Patterns that indicate a line is a CLOSING LINE of an already-wrapped multi-line lambda
# (starts with whitespace + `}` or `]` or `)` or `.method(`)
CONTINUATION_PREFIXES = (
    '}).', '})', '].', '])', ').', '))',
    '}).execute', '].execute', ').execute',
)

def is_closing_continuation(stripped):
    """True if this line is the end of a multi-line db_execute(lambda: ...) block"""
    for prefix in CONTINUATION_PREFIXES:
        if stripped.startswith(prefix):
            return True
    # Also: lines starting with .method() are backslash continuations
    if stripped.startswith('.'):
        return True
    return False

def is_safe_to_wrap(line_content):
    stripped = line_content.strip()
    if not stripped or stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
        return False
    if 'await db_execute' in line_content:
        return False
    if 'supabase' in line_content or 'supabase_admin' in line_content:
        return False
    # Must have an execute() call somewhere
    if '.execute()' not in line_content:
        return False
    # Must reference a db operation
    if not any(x in line_content for x in ['db.table(', 'db.rpc(', 'query.']):
        return False
    # Not a closing continuation line
    if is_closing_continuation(stripped):
        return False
    # Paren balance: opens == closes (self-contained line)
    opens = line_content.count('(')
    closes = line_content.count(')')
    if opens != closes:
        return False
    return True

def wrap_line(line_content):
    stripped = line_content.strip()
    indent = line_content[:len(line_content) - len(line_content.lstrip())]

    # Pattern: `var = EXPR.execute()` → `var = await db_execute(lambda: EXPR.execute())`
    m = re.match(r'^(\w[\w.]*)\s*=\s*(.+\.execute\(\))$', stripped)
    if m:
        var, expr = m.group(1), m.group(2)
        return f"{indent}{var} = await db_execute(lambda: {expr})\n"

    # Pattern: `var = (EXPR.execute()).data` → `var = (await db_execute(lambda: EXPR.execute())).data`
    m = re.match(r'^(\w[\w.]*)\s*=\s*\((.+\.execute\(\))\)(\.[\w\[\]"\'0-9]+.*)$', stripped)
    if m:
        var, expr, suffix = m.group(1), m.group(2), m.group(3)
        return f"{indent}{var} = (await db_execute(lambda: {expr})){suffix}\n"

    # Pattern: `var = EXPR.execute().data` → `var = (await db_execute(lambda: EXPR.execute())).data`
    m = re.match(r'^(\w[\w.]*)\s*=\s*(.+\.execute\(\))(\.[\w\[\]"\'0-9]+.*)$', stripped)
    if m:
        var, expr, suffix = m.group(1), m.group(2), m.group(3)
        return f"{indent}{var} = (await db_execute(lambda: {expr})){suffix}\n"

    # Pattern: standalone call like `db.table(...).update({...}).execute()`
    m = re.match(r'^(db\.|query\.)(.+\.execute\(\))$', stripped)
    if m:
        return f"{indent}await db_execute(lambda: {stripped})\n"

    # Fallback: wrap whatever's there
    return f"{indent}await db_execute(lambda: {stripped})\n"

def process_file(filepath, filename):
    shutil.copy(filepath, filepath + '.bak')
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines, changes = [], 0
    for line in lines:
        if is_safe_to_wrap(line):
            new_lines.append(wrap_line(line))
            changes += 1
        else:
            new_lines.append(line)

    if changes == 0:
        os.remove(filepath + '.bak')
        return 0

    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    try:
        py_compile.compile(filepath, doraise=True)
        os.remove(filepath + '.bak')
        return changes
    except py_compile.PyCompileError as e:
        print(f"  SYNTAX ERROR in {filename}, reverting: {e}")
        shutil.copy(filepath + '.bak', filepath)
        os.remove(filepath + '.bak')
        return 0

def main():
    total, files_changed = 0, []
    for filename in sorted(os.listdir(ROUTERS_DIR)):
        if not filename.endswith('.py') or filename in SKIP_FILES:
            continue
        filepath = os.path.join(ROUTERS_DIR, filename)
        changes = process_file(filepath, filename)
        if changes > 0:
            print(f"  {filename}: {changes} wraps applied")
            total += changes
            files_changed.append(filename)

    print(f"\nTotal: {total} db calls secured in {len(files_changed)} files")

    import subprocess
    result = subprocess.run(['python', '-m', 'compileall', 'routers/', '-q'], capture_output=True, text=True)
    if result.returncode == 0:
        print("All files compile successfully! ✓")
    else:
        print("COMPILE ERRORS:")
        print(result.stdout + result.stderr)

if __name__ == '__main__':
    main()
