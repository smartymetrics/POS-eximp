import sys

try:
    with open("routers/payouts.py", "r", encoding="utf-8") as f:
        content = f.read()

    content = content.replace(
        "from routers.auth import verify_token, has_any_role",
        "from routers.auth import verify_token, has_any_role, require_roles"
    )
    content = content.replace(
        "Depends(verify_token)", 
        "Depends(require_roles(['admin', 'super_admin']))"
    )

    with open("routers/payouts.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Success")
except Exception as e:
    print("Error:", str(e))
