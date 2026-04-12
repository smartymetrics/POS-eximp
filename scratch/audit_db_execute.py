
import os
import re

def audit_routers():
    router_dir = "routers"
    files = [f for f in os.listdir(router_dir) if f.endswith(".py")]
    
    report = []
    for filename in files:
        path = os.path.join(router_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            
        uses_db_execute = "db_execute(" in content
        imports_db_execute = re.search(r"from (database|\.) import.*db_execute", content)
        
        if uses_db_execute and not imports_db_execute:
            report.append(f"BROKEN {filename}: Uses db_execute but MISSING import.")
        elif uses_db_execute and imports_db_execute:
            report.append(f"OK {filename}: Correctly imports db_execute.")
        elif not uses_db_execute and imports_db_execute:
            report.append(f"UNUSED {filename}: Imports db_execute but DOES NOT use it.")
        else:
            report.append(f"NONE {filename}: No db_execute usage.")
            
    return "\n".join(report)

if __name__ == "__main__":
    print(audit_routers())
