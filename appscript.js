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
            first_name: responses["Customer first name"] || responses["First Name"] || "",
            last_name: responses["Customer last name (surname)"] || responses["Last Name"] || "",
            middle_name: responses["Customer middle name"] || responses["Middle Name"] || "",
            gender: responses["Gender"] || "",
            dob: responses["Date of Birth"] || "",
            address: responses["Client's residential address"] || responses["Residential Address"] || "",
            city: responses["City"] || "",
            state: responses["State"] || "",
            email: submitterEmail || responses["Client's email address"] || responses["Email"] || "",
            marital_status: responses["Marital Status"] || "",
            phone: responses["Client's phone number\n(Whatsapp line)"] || responses["Phone Number"] || "",
            occupation: responses["Occupation"] || "",
            nin: responses['NIN \n(This data is strictly utilized for our Know-Your-Customer (KYC) verification, in accordance with the requirements of the Nigerian government.)\n\nNIN Lookup: Use the phone number linked to your NIN registration and:\n\nDial *346#.\n\nSelect \'1\' for ""NIN Retrieval"" from the service options.\n\nComplete the process by following the on-screen instructions and providing the requested information.'] || responses["NIN"] || "",
            id_number: responses["International Passport No/NIN Number"] || responses["ID Card Number"] || "",
            id_document_url: responses["Upload NIN/International Passport "] || responses["Upload ID Card"] || "",
            nationality: responses["Nationality"] || "",
            passport_photo_url: responses["Upload a passport photograph"] || responses["Upload Passport Photo"] || "",

            // Next of Kin
            nok_name: responses["Next of kin's full name"] || responses["Next of Kin Name"] || "",
            nok_phone: responses["Next of kin phone number"] || responses["Next of Kin Phone"] || "",
            nok_email: responses["Next of kin's email address"] || responses["Next of Kin Email"] || "",
            nok_occupation: responses["Next of kin's occupation"] || responses["Next of Kin Occupation"] || "",
            nok_relationship: responses["Relationship"] || responses["Relationship with Next of Kin"] || "",
            nok_address: responses["Next of kin's home address"] || responses["Next of Kin Address"] || "",

            // Ownership & Signature
            ownership_type: responses["Ownership Type"] || "",
            co_owner_name: responses["Full name of the Second Owner\n(Surname, First name, Other Name)"] || responses["Full name of the Second Owner"] || "",
            co_owner_email: responses["Email address (Co-owner)"] || "",
            signature_url: responses["Upload Signature"] || "",
            signature_base64: getFileBase64(responses["Upload Signature"] || ""),

            // Property Info
            property_name: responses["Property name"] || "",
            plot_size: responses["Plot size"] || "",
            quantity: parseInt(responses["Quantity"] || 1),

            // Payment Info
            payment_duration: responses["Payment Duration"] || "",
            deposit_amount: parseFloat(stripCurrency(responses["Deposit Made (In Naira)"] || 0)),
            total_amount: parseFloat(stripCurrency(responses["Total Selling Price"] || responses["Property Price"] || 0)),
            payment_date: responses["Date of Payment/Deposit "] || responses["Payment Date"] || "",
            payment_proof_url: responses["Upload receipt of payment/deposit"] || responses["Upload Payment Proof"] || "",
            payment_terms: responses["Payment Duration"] || "Outright",

            // Other
            source_of_income: responses["Source of Income"] || "",
            referral_source: responses["How did you hear about us?"] || "",
            sales_rep_name: responses["Sales Rep / Marketer Name  "] || responses["Name of Sales Rep"] || "",
            sales_rep_phone: responses["Sales Rep Phone Number"] || "",
            consent: responses["By checking this box, I confirm that I have read, understand, and consent to all of the following Land Republic documents: Terms and Conditions, Payment Protection Promise, and Resale and Refund Policies. I accept full responsibility for all legal implications and interpretations of this agreement. I understand that this subscription form becomes binding on all parties immediately upon the company's receipt of my payment.  "] || responses["Consent Checkbox"] || responses["Do you agree to the terms?"] || "I Confirm and Agree",
            submitter_email: submitterEmail,
            timestamp: new Date().toISOString()
        };

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
                // If it's a Drive URL, extract ID
                if (fileId.indexOf("id=") > -1) {
                    fileId = fileId.split("id=")[1].split("&")[0];
                } else if (fileId.indexOf("/d/") > -1) {
                    fileId = fileId.split("/d/")[1].split("/")[0];
                }
                
                // If multiple files (array), take the first
                if (Array.isArray(fileId)) fileId = fileId[0];

                const file = DriveApp.getFileById(fileId);
                const blob = file.getBlob();
                const mimeType = blob.getContentType() || "";
                
                // Only encode if it's an image
                if (mimeType.indexOf("image/") === -1) {
                    Logger.log("Skipping non-image file: " + mimeType);
                    return "";
                }
                
                const base64 = Utilities.base64Encode(blob.getBytes());
                return "data:" + mimeType + ";base64," + base64;
            } catch (err) {
                Logger.log("Base64 conversion failed: " + err.toString());
                return "";
            }
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
