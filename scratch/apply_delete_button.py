import os

def main():
    filepath = "templates/professional_crm.html"
    if not os.path.exists(filepath):
        print(f"Error: {filepath} not found.")
        return

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Resilient Markup Insertion
    marker = 'onclick="openEditLeadForm()"'
    if marker not in content:
        print("Error: Could not find onclick=\"openEditLeadForm()\" in crm HTML.")
        return

    # Find the closing </button> of the edit button
    idx = content.find(marker)
    closing_btn_idx = content.find("</button>", idx)
    if closing_btn_idx == -1:
        print("Error: Could not find closing </button> tag.")
        return
    
    insert_pos = closing_btn_idx + len("</button>")

    # Detect if we should use CRLF
    newline = "\r\n" if "\r\n" in content else "\n"
    
    # Indentation of edit button
    # Let's see if we can find the leading spaces on that line
    line_start = content.rfind("\n", 0, idx)
    if line_start == -1:
        line_start = 0
    else:
        line_start += 1
    
    line = content[line_start:idx]
    spaces = ""
    for char in line:
        if char.isspace():
            spaces += char
        else:
            break

    delete_btn_html = (
        f"{newline}{spaces}<button id=\"detail-delete-btn\" class=\"btn text-red-500 hover:bg-red-500/10 border border-red-500/20\" style=\"width: 100%; margin-top: 10px; display: none;\" onclick=\"deleteLead()\">"
        f"{newline}{spaces}    <i class=\"fas fa-trash mr-1\"></i> Delete Contact"
        f"{newline}{spaces}</button>"
    )

    # Insert button
    content = content[:insert_pos] + delete_btn_html + content[insert_pos:]
    print("Success: Inserted Delete Contact button markup dynamically.")

    # 2. Add role check visibility in openLeadDetails
    # We will search for a unique substring in openLeadDetails
    target_rep_text = 'detail-lead-rep'
    if target_rep_text not in content:
        print("Error: Could not find detail-lead-rep in javascript.")
        return
    
    # Let's find the end of that statement (usually the semicolon or newline after assigning textContent)
    rep_idx = content.find(target_rep_text)
    stmt_end = content.find(";", rep_idx)
    if stmt_end == -1:
        print("Error: Could not find end of detail-lead-rep statement.")
        return
    
    insert_js_pos = stmt_end + 1
    
    js_logic = (
        f"{newline}{newline}{spaces}// Show/hide Delete button based strictly on super_admin role"
        f"{newline}{spaces}const deleteBtn = document.getElementById(\"detail-delete-btn\");"
        f"{newline}{spaces}if (deleteBtn) {{"
        f"{newline}{spaces}    if (adminData && adminData.role) {{"
        f"{newline}{spaces}        const roles = adminData.role.toLowerCase().split(',').map(r => r.trim());"
        f"{newline}{spaces}        if (roles.includes(\"super_admin\")) {{"
        f"{newline}{spaces}            deleteBtn.style.display = \"block\";"
        f"{newline}{spaces}        }} else {{"
        f"{newline}{spaces}            deleteBtn.style.display = \"none\";"
        f"{newline}{spaces}        }}"
        f"{newline}{spaces}    }} else {{"
        f"{newline}{spaces}        deleteBtn.style.display = \"none\";"
        f"{newline}{spaces}    }}"
        f"{newline}{spaces}}}"
    )

    content = content[:insert_js_pos] + js_logic + content[insert_js_pos:]
    print("Success: Inserted role visibility logic dynamically.")

    # 3. Add deleteLead JS function near saveLeadDetails
    target_save_details = "async function saveLeadDetails("
    if target_save_details not in content:
        print("Error: Could not find async function saveLeadDetails.")
        return
    
    func_idx = content.find(target_save_details)
    
    delete_func_js = (
        f"async function deleteLead() {{"
        f"{newline}{spaces}    const id = document.getElementById(\"leadDetailModal\").dataset.id;"
        f"{newline}{spaces}    const name = document.getElementById(\"detail-lead-name\").textContent;"
        f"{newline}{spaces}    "
        f"{newline}{spaces}    if (!confirm(`Are you sure you want to permanently delete lead/contact \"${{name}}\"?\\n\\nThis will clean up their logs and outreach records. This action cannot be undone.`)) {{"
        f"{newline}{spaces}        return;"
        f"{newline}{spaces}    }}"
        f"{newline}{spaces}    "
        f"{newline}{spaces}    try {{"
        f"{newline}{spaces}        showPageLoader(\"Deleting lead...\");"
        f"{newline}{spaces}        const res = await fetch(`/api/clients/${{id}}`, {{"
        f"{newline}{spaces}            method: \"DELETE\","
        f"{newline}{spaces}            headers: {{ \"Authorization\": `Bearer ${{token}}` }}"
        f"{newline}{spaces}        }});"
        f"{newline}{spaces}        hidePageLoader();"
        f"{newline}{spaces}        "
        f"{newline}{spaces}        if (res.ok) {{"
        f"{newline}{spaces}            alert(\"Lead deleted successfully.\");"
        f"{newline}{spaces}            closeLeadDetailModal();"
        f"{newline}{spaces}            // Reload appropriate views"
        f"{newline}{spaces}            loadPipeline();"
        f"{newline}{spaces}            loadLeads();"
        f"{newline}{spaces}            if (document.getElementById(\"contacts-list\").classList.contains(\"active\")) {{"
        f"{newline}{spaces}                loadContactsList();"
        f"{newline}{spaces}            }}"
        f"{newline}{spaces}        }} else {{"
        f"{newline}{spaces}            const data = await res.json();"
        f"{newline}{spaces}            alert(\"Failed to delete lead: \" + (data.detail || \"Unknown error\"));"
        f"{newline}{spaces}        }}"
        f"{newline}{spaces}    }} catch (err) {{"
        f"{newline}{spaces}        hidePageLoader();"
        f"{newline}{spaces}        console.error(\"Delete Error:\", err);"
        f"{newline}{spaces}        alert(\"Failed to delete lead due to network error.\");"
        f"{newline}{spaces}    }}"
        f"{newline}{spaces}}}"
        f"{newline}{newline}{spaces}"
    )

    content = content[:func_idx] + delete_func_js + content[func_idx:]
    print("Success: Inserted deleteLead JS function dynamically.")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print("All professional_crm.html frontend changes applied successfully!")

if __name__ == "__main__":
    main()
