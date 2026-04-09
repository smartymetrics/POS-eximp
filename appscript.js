// --- CONFIGURATION ---
const WEBHOOK_URL = "https://pos-eximp.onrender.com/api/webhooks/form-submission";
const WEBHOOK_SECRET = "eximp_cloves_form_web_2026_xyz";

function onFormSubmit(e) {
    try {
        let responses = {};
        let submitterEmail = "";

        if (e.namedValues) {
            // Spreadsheet Trigger
            for (let key in e.namedValues) {
                responses[key.trim()] = e.namedValues[key][0];
            }
            submitterEmail = responses["Email Address"] || responses["Email"] || "";
        } else if (e.response) {
            // Form Trigger
            const itemResponses = e.response.getItemResponses();
            itemResponses.forEach(itemResponse => {
                responses[itemResponse.getItem().getTitle().trim()] = itemResponse.getResponse();
            });
            submitterEmail = e.response.getRespondentEmail();
        }

        // --- ROBUST MAPPING HELPER ---
        function getVal(primaryKey, keywords) {
            // Try exact match first
            if (responses[primaryKey]) return responses[primaryKey];
            
            // Try keyword safety net
            for (let key in responses) {
                let match = true;
                for (let word of keywords) {
                    if (key.toLowerCase().indexOf(word.toLowerCase()) === -1) {
                        match = false;
                        break;
                    }
                }
                if (match) {
                    Logger.log("Keyword Match Found: '" + key + "' mapped to keywords [" + keywords.join(",") + "]");
                    return responses[key];
                }
            }
            return "";
        }

        // --- FIELD MAPPING ---
        const payload = {
            // Client Info
            title: getVal("Title", ["Title"]),
            first_name: getVal("Customer first name", ["First Name"]),
            last_name: getVal("Customer last name (surname)", ["Last Name"]),
            middle_name: getVal("Customer middle name", ["Middle Name"]),
            gender: getVal("Gender", ["Gender"]),
            dob: getVal("Date of Birth", ["Date", "Birth"]),
            address: getVal("Client's residential address", ["Residential Address", "Address"]),
            city: getVal("City", ["City"]),
            state: getVal("State", ["State"]),
            email: submitterEmail || getVal("Client's email address", ["Email"]),
            marital_status: getVal("Marital Status", ["Marital"]),
            phone: getVal("Client's phone number\n(Whatsapp line)", ["Phone", "Whatsapp"]),
            occupation: getVal("Occupation", ["Occupation"]),
            
            // KYC Fields (The problematic ones)
            nin: getVal("NIN", ["NIN", "Retrieval"]),
            id_number: getVal("International Passport No/NIN Number", ["Passport", "Number"]),
            id_document_url: getVal("Upload NIN/International Passport", ["Upload", "NIN"]),
            nationality: getVal("Nationality", ["Nationality"]),
            passport_photo_url: getVal("Upload a passport photograph", ["Upload", "Passport Photo"]),

            // Next of Kin
            nok_name: getVal("Next of kin's full name", ["Next of Kin", "Name"]),
            nok_phone: getVal("Next of kin phone number", ["Next of Kin", "Phone"]),
            nok_email: getVal("Next of kin's email address", ["Next of Kin", "Email"]),
            nok_occupation: getVal("Next of kin's occupation", ["Next of Kin", "Occupation"]),
            nok_relationship: getVal("Relationship", ["Relationship"]),
            nok_address: getVal("Next of kin's home address", ["Next of Kin", "Address"]),

            // Ownership & Signature
            ownership_type: getVal("Ownership Type", ["Ownership"]),
            co_owner_name: getVal("Full name of the Second Owner", ["Full name", "Second Owner"]),
            co_owner_email: getVal("Email address (Co-owner)", ["Email", "Co-owner"]),
            signature_url: getVal("Upload Signature", ["Upload Signature"]),
            signature_base64: getFileBase64(getVal("Upload Signature", ["Upload Signature"])),

            // Property Info
            property_name: getVal("Property name", ["Property name"]),
            plot_size: getVal("Plot size", ["Plot size"]),
            quantity: parseInt(getVal("Quantity", ["Quantity"]) || 1),

            // Payment Info
            payment_duration: getVal("Payment Duration", ["Payment Duration"]),
            deposit_amount: parseFloat(stripCurrency(getVal("Deposit Made (In Naira)", ["Deposit"]))),
            total_amount: parseFloat(stripCurrency(getVal("Total Selling Price", ["Total", "Price"]))),
            payment_date: getVal("Date of Payment/Deposit", ["Payment Date"]),
            payment_proof_url: getVal("Upload receipt of payment/deposit", ["Upload", "Proof"]),
            payment_terms: getVal("Payment Duration", ["Payment", "Duration"]) || "Outright",

            // Other
            source_of_income: getVal("Source of Income", ["Source", "Income"]),
            referral_source: getVal("How did you hear about us?", ["How", "hear"]),
            purchase_purpose: getVal("Is this property being purchased:", ["Purchase", "Purpose"]),
            sales_rep_name: getVal("Sales Rep / Marketer Name", ["Sales Rep"]),
            sales_rep_phone: getVal("Sales Rep Phone Number", ["Sales Rep", "Phone"]),
            consent: getVal("Consent Checkbox", ["Consent", "confirm"]),
            
            submitter_email: submitterEmail,
            timestamp: new Date().toISOString()
        };

        // --- SEND TO WEBHOOK ---
        const options = {
            method: "post",
            contentType: "application/json",
            headers: { "X-Webhook-Secret": WEBHOOK_SECRET },
            payload: JSON.stringify(payload),
            muteHttpExceptions: true
        };

        const response = UrlFetchApp.fetch(WEBHOOK_URL, options);
        Logger.log("Response: " + response.getContentText());

    } catch (err) {
        Logger.log("Error: " + err.toString());
    }
}

// Helper to strip currency symbols and commas
function stripCurrency(val) {
    if (!val) return "0";
    return val.toString().replace(/[^\d.]/g, "");
}

// Helper to get File content as Base64 from Drive
function getFileBase64(fileIdOrUrl) {
    if (!fileIdOrUrl) return "";
    try {
        let fileId = fileIdOrUrl;
        if (fileId.indexOf("id=") > -1) {
            fileId = fileId.split("id=")[1].split("&")[0];
        } else if (fileId.indexOf("/d/") > -1) {
            fileId = fileId.split("/d/")[1].split("/")[0];
        }
        if (Array.isArray(fileId)) fileId = fileId[0];

        const file = DriveApp.getFileById(fileId);
        const blob = file.getBlob();
        const mimeType = blob.getContentType() || "";
        
        if (mimeType.indexOf("image/") === -1) return "";
        
        const base64 = Utilities.base64Encode(blob.getBytes());
        return "data:" + mimeType + ";base64," + base64;
    } catch (err) {
        return "";
    }
}
