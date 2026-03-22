// --- CONFIGURATION ---
const WEBHOOK_URL = "https://pos-eximp.onrender.com/api/webhooks/form-submission";
const WEBHOOK_SECRET = "eximp_cloves_form_web_2026_xyz";

function onFormSubmit(e) {
    try {
        // --- DATA EXTRACTION ---
        // For Spreadsheet-bound scripts, we use e.namedValues
        // For Form-bound scripts, we use e.response
        let responses = {};
        let submitterEmail = "";
        
        if (e.namedValues) {
            // Spreadsheet Trigger
            for (let key in e.namedValues) {
                responses[key.trim()] = e.namedValues[key][0]; // namedValues returns arrays
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

        // --- FIELD MAPPING ---
        const payload = {
            // Client Info
            title: responses["Title"] || "",
            first_name: responses["First Name"] || "",
            last_name: responses["Last Name"] || "",
            middle_name: responses["Middle Name"] || "",
            gender: responses["Gender"] || "",
            dob: responses["Date of Birth"] || "",
            address: responses["Residential Address"] || "",
            email: submitterEmail || responses["Email Address"] || "",
            marital_status: responses["Marital Status"] || "",
            phone: responses["Phone Number"] || "",
            occupation: responses["Occupation"] || "",
            nin: responses["NIN"] || "",
            id_number: responses["ID Card Number"] || "",
            id_document_url: responses["Upload ID Card"] || "", 
            nationality: responses["Nationality"] || "",
            passport_photo_url: responses["Upload Passport Photo"] || "",

            // Next of Kin
            nok_name: responses["Next of Kin Name"] || "",
            nok_phone: responses["Next of Kin Phone"] || "",
            nok_email: responses["Next of Kin Email"] || "",
            nok_occupation: responses["Next of Kin Occupation"] || "",
            nok_relationship: responses["Relationship with Next of Kin"] || "",
            nok_address: responses["Next of Kin Address"] || "",

            // Ownership & Signature
            ownership_type: responses["Type of Ownership"] || "",
            co_owner_name: responses["Co-owner full Name (if applicable)"] || "",
            co_owner_email: responses["Co-owner Email"] || "",
            signature_url: responses["Signature"] || "", 

            // Property Info
            property_name: responses["Property Name"] || "",
            plot_size: responses["Plot Size"] || "",

            // Payment Info
            payment_duration: responses["Payment Duration"] || "",
            deposit_amount: parseFloat(stripCurrency(responses["Deposit Amount"] || 0)),
            total_amount: parseFloat(stripCurrency(responses["Total Selling Price"] || responses["Property Price"] || 0)),
            payment_date: responses["Payment Date"] || "",
            payment_proof_url: responses["Upload Payment Proof"] || "",
            payment_terms: responses["Payment Terms"] || "Outright",

            // Other
            source_of_income: responses["Source of Income"] || "",
            referral_source: responses["How did you hear about us?"] || "",
            sales_rep_name: responses["Name of Sales Rep"] || "",
            sales_rep_phone: responses["Sales Rep Phone Number"] || "",
            consent: responses["Consent Checkbox"] || responses["Do you agree to the terms?"] || "I Confirm and Agree",
            submitter_email: submitterEmail,
            timestamp: e.range ? new Date().toISOString() : (e.response ? e.response.getTimestamp().toISOString() : new Date().toISOString())
        };

        // Helper to strip currency symbols and commas
        function stripCurrency(val) {
            if (!val) return "0";
            return val.toString().replace(/[^\d.]/g, "");
        }

        // --- SEND TO WEBHOOK ---
        const options = {
            method: "post",
            contentType: "application/json",
            headers: {
                "X-Webhook-Secret": WEBHOOK_SECRET
            },
            payload: JSON.stringify(payload),
            muteHttpExceptions: true
        };

        const response = UrlFetchApp.fetch(WEBHOOK_URL, options);
        Logger.log("Response: " + response.getContentText());

    } catch (err) {
        Logger.log("Error: " + err.toString());
    }
}
