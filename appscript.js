// --- CONFIGURATION ---
const WEBHOOK_URL = "https://pos-eximp.onrender.com";
const WEBHOOK_SECRET = "eximp_cloves_form_web_2026_xyz";

function onFormSubmit(e) {
    try {
        const itemResponses = e.response.getItemResponses();
        const responses = {};

        // Helper to get response by question title
        itemResponses.forEach(itemResponse => {
            responses[itemResponse.getItem().getTitle().trim()] = itemResponse.getResponse();
        });

        // --- FIELD MAPPING ---
        // Change the keys on the left if your form question titles are different.
        const payload = {
            // Client Info
            title: responses["Title"] || "",
            first_name: responses["First Name"] || "",
            last_name: responses["Last Name"] || "",
            middle_name: responses["Middle Name"] || "",
            gender: responses["Gender"] || "",
            dob: responses["Date of Birth"] || "",
            address: responses["Residential Address"] || "",
            email: e.response.getRespondentEmail() || responses["Email Address"] || "",
            marital_status: responses["Marital Status"] || "",
            phone: responses["Phone Number"] || "",
            occupation: responses["Occupation"] || "",
            nin: responses["NIN"] || "",
            id_number: responses["ID Card Number"] || "",
            id_document_url: responses["Upload ID Card"] || "", // Usually a link to Drive
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
            signature_url: responses["Signature"] || "", // Link to the signature image

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
            consent: responses["Consent Checkbox"] || responses["Do you agree to the terms?"] || "I Confirm and Agree", // Fallback for testing
            submitter_email: e.response.getRespondentEmail() || "",
            timestamp: e.response.getTimestamp().toISOString()
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
