import os
import re

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    execute_matches = [m for m in re.finditer(r'\.execute\(\)', content)]
    
    if not execute_matches:
        return 0
        
    replacements = []
    for match in execute_matches:
        end_pos = match.end()
        i = match.start()
        
        db_pos_1 = content.rfind("db.table", 0, i)
        db_pos_2 = content.rfind("db.rpc", 0, i)
        db_pos_3 = content.rfind("query.", 0, i)
        
        db_pos = max(db_pos_1, db_pos_2, db_pos_3)
        
        if db_pos == -1:
            continue
            
        between = content[db_pos:end_pos]
        
        if between.count('.execute()') > 1:
            continue
            
        # Exclude instances where the chain is broken by newlines without backslashes or parentheses wrapping
        # But python allows newline after parenthesis `(`. It's complex. Let's just trust `between`.
        
        # Check if it was already wrapped in lambda:
        before_db = content[max(0, db_pos-30):db_pos]
        if "lambda:" in before_db or "lambda : " in before_db:
            continue
            
        replacements.append((db_pos, end_pos, between))

    if not replacements:
        return 0

    count = 0
    # Apply replacements from back to front
    for start_pos, end_pos, between in reversed(replacements):
        before_db = content[max(0, start_pos-30):start_pos]
        if "lambda:" in before_db:
            continue
            
        new_str = f"await db_execute(lambda: {between})"
        content = content[:start_pos] + new_str + content[end_pos:]
        count += 1

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
        
    return count

def main():
    routers_dir = 'routers'
    total_fixed = 0
    for file in os.listdir(routers_dir):
        if file.endswith('.py'):
            fixed = fix_file(os.path.join(routers_dir, file))
            if fixed > 0:
                print(f"Fixed {fixed} instances in {file}")
                total_fixed += fixed
                
    # Also fix main directories like email_service.py if any? Or leave standard.
    # The routers are the main request handlers
    print(f"\nTotal fixed queries across all routers: {total_fixed}")

if __name__ == '__main__':
    main()
