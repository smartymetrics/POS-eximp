**EXIMP & CLOVES INFRASTRUCTURE LIMITED**

RC 8311800

**PRODUCT REQUIREMENTS DOCUMENT 5**

**Contract of Sale Automation &**

**Digital Signing Portal**

Version 1.0

March 2026

*Read alongside PRD 1, PRD 2, PRD 3, PRD 4, and the Addendum*

**1. Overview**

This PRD covers the complete automation of the Contract of Sale process
for Eximp & Cloves Infrastructure Limited. The existing system already
generates invoices, receipts, and statements of account. This document
extends that system to generate, circulate, and execute Contracts of
Sale with legally valid digital signatures from all required parties.

The four parties who must sign each Contract of Sale are:

  ------------------------------------------------------------------------
  **Party**        **Who**               **How Signature is Captured**
  ---------------- --------------------- ---------------------------------
  Purchaser        The land buyer        Already captured from Google Form
                                         --- stored as signature_base64 on
                                         invoices table

  Director         Eximp & Cloves        Stored once in system ---
                   Director              auto-embedded on every contract

  Secretary        Eximp & Cloves        Stored once in system ---
                   Secretary             auto-embedded on every contract

  Witness 1 & 2    Purchaser\'s chosen   Unique signing link sent to
                   witnesses             purchaser who shares with
                                         witnesses
  ------------------------------------------------------------------------

> *The purchaser signature is already being collected from the Google
> Form and working correctly. The Director and Secretary signatures are
> stored once and reused. Only the witness signatures require the new
> signing portal described in this PRD.*

Legal basis in Nigeria:

-   Evidence Act 2011, Section 84 --- electronic documents are
    admissible as evidence

-   Cybercrimes Act 2015 --- electronic signatures are legally
    recognised

-   NITDA Guidelines --- digital transactions between parties are valid

This approach is used by Landwey, Purple Group, and PropertyPro for
their digital contract executions.

**2. End-to-End Contract Workflow**

**2.1 Complete Flow**

The complete contract lifecycle from form submission to executed
document:

  -----------------------------------------------------------------------------
  **Step**   **Who**              **Action**
  ---------- -------------------- ---------------------------------------------
  1          System (auto)        Client submits Google Form --- invoice
                                  created, invoice email sent

  2          Admin                Reviews form submission, verifies payment
                                  proof in Pending Verifications

  3          Admin                Confirms payment --- receipt + statement sent
                                  to client automatically

  4          Admin                Clicks \"Generate Contract\" on the invoice
                                  --- system creates a draft Contract of Sale
                                  PDF

  5          System (auto)        Unique signing token generated --- signing
                                  session created in database

  6          System (auto)        Email sent to client with the signing link
                                  and instructions for witnesses

  7          Client               Forwards the unique signing link to Witness 1
                                  and Witness 2

  8          Witness 1 & 2        Open the link, enter their details, draw or
                                  upload their signature, submit

  9          System (auto)        Once both witnesses have signed --- admin is
                                  notified

  10         Admin                Reviews and clicks \"Generate Final
                                  Contract\" --- all 5 signatures embedded

  11         System (auto)        Final executed Contract of Sale PDF emailed
                                  to client and stored in system
  -----------------------------------------------------------------------------

**2.2 Why This Approach Is Professional**

  -----------------------------------------------------------------------
  **Feature**             **Google Form**         **This Signing Portal**
  ----------------------- ----------------------- -----------------------
  Branded experience      No                      Yes --- Eximp & Cloves
                                                  branded

  Live signature drawing  No                      Yes --- canvas pad +
                                                  upload option

  Linked to specific      No                      Yes --- unique token
  contract                                        per contract

  Link expiry             No                      Yes --- 7 days

  Audit trail (IP +       No                      Yes --- full log per
  timestamp)                                      signature

  Auto-generates final    No                      Yes
  PDF                                             

  Witness sees what they  No                      Yes --- contract
  sign                                            summary shown

  Legal appearance        No                      Yes --- professional
                                                  portal
  -----------------------------------------------------------------------

**3. The Witness Signing Page**

**3.1 URL Structure**

The signing page is served directly from the existing FastAPI
application --- no new hosting needed.

> app.eximps-cloves.com/sign/{unique_token}

Each token is a unique UUID generated when the admin initiates a
contract. It expires automatically after 7 days. After a witness submits
their signature, the link shows \"Signature already submitted\" if
accessed again.

**3.2 What the Witness Sees**

The page is clean, mobile-friendly, and Eximp & Cloves branded. It
contains:

-   Company logo and branding at the top

-   A clear title: \"Contract Witness Signing --- \[Estate Name\]\"

-   A brief summary of what they are witnessing: Purchaser name,
    property, date

-   A legal notice: \"By signing below, you confirm you have personally
    witnessed the execution of this Contract of Sale\"

-   Form fields: Full Name (required), Address (required), Occupation
    (required)

-   Signature input --- two options (see Section 3.3)

-   A Submit button --- disabled until all fields are filled and a
    signature is provided

-   After submission: a confirmation screen --- \"Thank you. Your
    signature has been recorded.\"

**3.3 Signature Input --- Two Options**

The witness page must support BOTH methods for capturing signatures.
This is important because some devices (especially older phones) may not
support canvas drawing reliably.

  -----------------------------------------------------------------------
  **Method**    **Option A --- Draw          **Option B --- Upload
                Signature**                  Signature**
  ------------- ---------------------------- ----------------------------
  **Library**   signature_pad.js (open       Standard HTML file input:
                source --- used by DocuSign  accept=\"image/\*\"
                and Adobe)                   

  **How it      Witness draws signature with Witness takes a photo of
  works**       finger (mobile) or mouse     their handwritten signature
                (desktop) on a canvas        or uploads an image file
                element                      

  **Output**    PNG image as base64 data URI Image file converted to
                --- extracted from canvas    base64 on the frontend using
                via toDataURL()              FileReader API

  **Best for**  Touchscreen phones, tablets, Older phones, witnesses who
                modern laptops with trackpad prefer physical signature,
                                             poor touchscreen

  **Stored as** signature_base64 in          Same --- converted to base64
                witness_signatures table --- before sending to API
                identical format to          
                purchaser signature          
  -----------------------------------------------------------------------

The UI should show a tab switcher at the top of the signature section:

> \[ Draw Signature \] \[ Upload Signature \]

Switching tabs clears the other input. Only one method can be active at
a time. Both methods produce identical base64 output stored in the same
database column.

**3.4 Signature Pad Implementation**

Use signature_pad.js loaded from CDN:

> https://cdn.jsdelivr.net/npm/signature_pad@4.1.7/dist/signature_pad.umd.min.js

Canvas element setup:

> \<canvas id=\"sig-pad\" width=\"400\" height=\"150\"
> style=\"border:1px solid #ddd; border-radius:6px;
> touch-action:none;\"\>\</canvas\>
>
> *The touch-action:none CSS is critical --- without it, drawing on
> mobile causes the page to scroll instead of drawing the signature.*

JavaScript initialisation:

> const canvas = document.getElementById(\"sig-pad\"); const
> signaturePad = new SignaturePad(canvas, { backgroundColor: \"rgb(255,
> 255, 255)\", penColor: \"rgb(0, 0, 0)\" }); // Extract base64 when
> submitting: const base64 = signaturePad.toDataURL(\"image/png\");

**3.5 Upload Option Implementation**

> \<input type=\"file\" id=\"sig-upload\" accept=\"image/\*\"
> capture=\"environment\"\> // Convert to base64:
> document.getElementById(\"sig-upload\").onchange = (e) =\> { const
> file = e.target.files\[0\]; const reader = new FileReader();
> reader.onload = (ev) =\> { uploadedBase64 = ev.target.result; //
> data:image/jpeg;base64,\... }; reader.readAsDataURL(file); };
>
> *The capture=\"environment\" attribute on mobile opens the camera
> directly, allowing witnesses to photograph their handwritten signature
> immediately.*

**4. Database Schema**

**4.1 New Tables**

Run the following SQL in the Supabase SQL Editor:

**contract_signing_sessions**

> CREATE TABLE IF NOT EXISTS contract_signing_sessions ( id UUID DEFAULT
> gen_random_uuid() PRIMARY KEY, invoice_id UUID NOT NULL REFERENCES
> invoices(id), token VARCHAR(64) UNIQUE NOT NULL, expires_at
> TIMESTAMPTZ NOT NULL, status VARCHAR(50) DEFAULT \'pending\' CHECK
> (status IN (\'pending\', \'partial\', \'completed\', \'expired\')),
> created_by UUID REFERENCES admins(id), created_at TIMESTAMPTZ DEFAULT
> NOW() ); ALTER TABLE contract_signing_sessions ENABLE ROW LEVEL
> SECURITY;

**witness_signatures**

> CREATE TABLE IF NOT EXISTS witness_signatures ( id UUID DEFAULT
> gen_random_uuid() PRIMARY KEY, session_id UUID NOT NULL REFERENCES
> contract_signing_sessions(id), witness_number INTEGER NOT NULL CHECK
> (witness_number IN (1, 2)), full_name VARCHAR(255) NOT NULL, address
> TEXT NOT NULL, occupation VARCHAR(100) NOT NULL, signature_base64 TEXT
> NOT NULL, signature_method VARCHAR(20) DEFAULT \'drawn\' CHECK
> (signature_method IN (\'drawn\', \'uploaded\')), ip_address
> VARCHAR(50), user_agent TEXT, signed_at TIMESTAMPTZ DEFAULT NOW(),
> UNIQUE(session_id, witness_number) ); ALTER TABLE witness_signatures
> ENABLE ROW LEVEL SECURITY;

**company_signatures**

> CREATE TABLE IF NOT EXISTS company_signatures ( id UUID DEFAULT
> gen_random_uuid() PRIMARY KEY, role VARCHAR(50) NOT NULL CHECK (role
> IN (\'director\', \'secretary\')), full_name VARCHAR(255) NOT NULL,
> signature_base64 TEXT NOT NULL, uploaded_by UUID REFERENCES
> admins(id), is_active BOOLEAN DEFAULT true, created_at TIMESTAMPTZ
> DEFAULT NOW() ); ALTER TABLE company_signatures ENABLE ROW LEVEL
> SECURITY;

**contract_documents**

> CREATE TABLE IF NOT EXISTS contract_documents ( id UUID DEFAULT
> gen_random_uuid() PRIMARY KEY, invoice_id UUID NOT NULL REFERENCES
> invoices(id), session_id UUID REFERENCES
> contract_signing_sessions(id), document_type VARCHAR(50) DEFAULT
> \'draft\' CHECK (document_type IN (\'draft\', \'executed\')),
> generated_by UUID REFERENCES admins(id), emailed_to VARCHAR(255),
> created_at TIMESTAMPTZ DEFAULT NOW() ); ALTER TABLE contract_documents
> ENABLE ROW LEVEL SECURITY;

**4.2 Column Added to invoices Table**

The invoices table already has signature_base64 (purchaser signature
from Google Form). No new columns are needed on the invoices table. All
contract data is stored in the new tables above.

**5. New API Endpoints**

  -----------------------------------------------------------------------------------------------
  **Method**   **Endpoint**                              **Auth**    **Description**
  ------------ ----------------------------------------- ----------- ----------------------------
  POST         /api/contracts/{invoice_id}/initiate      JWT         Generate signing session +
                                                                     unique token. Creates draft
                                                                     contract PDF.

  GET          /api/contracts/{invoice_id}/status        JWT         Check signing progress ---
                                                                     how many witnesses have
                                                                     signed

  POST         /api/contracts/{invoice_id}/generate      JWT         Generate final executed PDF
                                                                     with all 5 signatures
                                                                     embedded

  POST         /api/contracts/{invoice_id}/resend-link   JWT         Resend the signing link
                                                                     email to the client

  GET          /sign/{token}                             None        Render the witness signing
                                                         (public)    page --- validates token,
                                                                     shows contract summary

  POST         /api/sign/{token}/witness                 None        Submit a witness signature
                                                         (public)    --- full name, address,
                                                                     occupation, base64 signature

  GET          /api/company-signatures                   JWT Admin   List active Director and
                                                                     Secretary signatures

  POST         /api/company-signatures                   JWT Admin   Upload or replace Director /
                                                                     Secretary signature

  DELETE       /api/company-signatures/{id}              JWT Admin   Remove a company signature
  -----------------------------------------------------------------------------------------------

**5.1 Token Generation Logic**

> import secrets from datetime import datetime, timedelta def
> generate_signing_token(): return secrets.token_urlsafe(32) \# 43-char
> URL-safe random string def create_signing_session(invoice_id,
> admin_id, db): token = generate_signing_token() expires_at =
> datetime.utcnow() + timedelta(days=7) session =
> db.table(\"contract_signing_sessions\").insert({ \"invoice_id\":
> invoice_id, \"token\": token, \"expires_at\": expires_at.isoformat(),
> \"status\": \"pending\", \"created_by\": admin_id }).execute() return
> token

**5.2 Witness Submission Validation**

Before accepting a witness signature, the backend must validate:

1.  Token exists in contract_signing_sessions table

2.  Token has not expired (expires_at \> now)

3.  Session status is \"pending\" or \"partial\" --- not \"completed\"
    or \"expired\"

4.  witness_number is 1 or 2

5.  This witness_number has not already submitted for this session
    (UNIQUE constraint)

6.  All required fields are present: full_name, address, occupation,
    signature_base64

7.  signature_base64 starts with \"data:image/\" --- basic format
    validation

After a successful submission, update the session status:

-   1 witness signed → status = \"partial\"

-   2 witnesses signed → status = \"completed\", notify admin

**6. Contract PDF Generation**

**6.1 Draft Contract**

When admin clicks \"Generate Contract\" on an invoice, the system
generates a DRAFT contract PDF. This is the same layout as the Tokyo
contract you shared, but filled with the client\'s data. The draft
shows:

-   All client details from the invoices and clients tables

-   Property details --- estate name, size, location, purchase price

-   Purchaser signature already embedded (from Google Form)

-   Director and Secretary signature placeholders (filled from
    company_signatures table)

-   Witness 1 and Witness 2 placeholders --- blank lines labelled
    \"Pending\"

-   A watermark: \"DRAFT --- PENDING WITNESS SIGNATURES\"

> *The draft PDF is not sent to the client. It is for admin review only.
> Only the final executed contract is sent.*

**6.2 Final Executed Contract**

Once both witnesses have signed, admin clicks \"Generate Final
Contract\". The system:

8.  Fetches client signature from invoices.signature_base64

9.  Fetches Witness 1 details + signature from witness_signatures

10. Fetches Witness 2 details + signature from witness_signatures

11. Fetches active Director signature from company_signatures where role
    = \"director\"

12. Fetches active Secretary signature from company_signatures where
    role = \"secretary\"

13. Renders the contract HTML template with all 5 signatures embedded as
    base64 \<img\> tags

14. Converts to PDF using xhtml2pdf (same engine used for invoices and
    receipts)

15. Emails the final PDF to the client

16. Stores a record in contract_documents table with document_type =
    \"executed\"

17. Logs the event in activity_log

**6.3 Contract PDF Template**

Create a new file: pdf_templates/contract.html

The template follows the same structure as the Tokyo contract but is an
HTML file rendered by Jinja2. Key sections:

  -------------------------------------------------------------------------
  **Section**   **Content**                  **Data Source**
  ------------- ---------------------------- ------------------------------
  Cover page    Contract title, between      invoices + clients tables
                parties, property            
                description, prepared by     

  Recitals      Standard legal recitals      Template static text +
                (1a--1e) --- largely static  property details
                text                         

  Covenants     Standard covenants (3A--3H)  Template static text
                --- static legal text        

  Execution     Company seal section with    company_signatures table
  page          Director + Secretary         
                signatures                   

  Purchaser     Purchaser name + drawn       invoices.signature_base64
  signature     signature image              

  Witness 1     Name, address, occupation,   witness_signatures
  block         signature image              (witness_number=1)

  Witness 2     Name, address, occupation,   witness_signatures
  block         signature image              (witness_number=2)
  -------------------------------------------------------------------------

**6.4 Signature Image Rendering in PDF**

All signatures are embedded as inline base64 images. Use this pattern in
the HTML template:

> {% if witness1_signature %} \<img src=\"{{ witness1_signature }}\"
> style=\"max-width:180px; max-height:70px; display:block;\"\> {% else
> %} \<div style=\"border-bottom:1px solid #ccc; width:180px;
> height:40px;\"\>\</div\> {% endif %} \<p style=\"font-size:9px;
> color:#888; margin-top:4px;\"\>{{ witness1_name }}\</p\>
>
> *Always wrap signature images in a try/except block in pdf_service.py.
> If a signature fails to render, the PDF must still generate --- show a
> blank line instead of crashing.*

**7. Email Templates**

**7.1 Signing Link Email to Client**

Sent when admin initiates the contract. Goes to the client\'s email
address.

Subject: Your Contract of Sale is Ready --- Eximp & Cloves

> Dear \[Client Name\], Your Contract of Sale for \[Estate Name\] ---
> \[Plot Size\] is ready for execution. To complete the process, please
> forward the witness signing link below to TWO witnesses of your
> choice. Each witness must: 1. Open the link on their phone or computer
> 2. Enter their full name, address, and occupation 3. Draw or upload
> their signature 4. Click Submit WITNESS SIGNING LINK:
> \[https://app.eximps-cloves.com/sign/{token}\] IMPORTANT: This link
> expires in 7 days ({expiry_date}). Each witness must sign separately
> using the same link. Once both witnesses have signed, we will send you
> the final executed Contract of Sale. \[Company footer\]

**7.2 Admin Notification --- All Witnesses Signed**

Sent to ADMIN_ALERT_EMAIL when both witnesses have completed signing.

Subject: Contract Ready for Execution --- \[Client Name\] --- \[Invoice
No\]

> Both witnesses have signed the contract for: Client: \[Client Name\]
> Invoice: \[EC-XXXXXX\] Property: \[Estate Name\] --- \[Plot Size\]
> Witness 1: \[Name\] --- \[Occupation\] Witness 2: \[Name\] ---
> \[Occupation\] Log in to the dashboard to review and generate the
> final executed Contract of Sale. \[Direct link to invoice in
> dashboard\]

**7.3 Final Contract Email to Client**

Sent when admin generates and approves the final executed contract.

Subject: Your Executed Contract of Sale --- Eximp & Cloves

> Dear \[Client Name\], Congratulations! Your Contract of Sale has been
> fully executed. Please find your signed Contract of Sale attached to
> this email. This is a legally binding document. Please keep it in a
> safe place. Property: \[Estate Name\] Plot Size: \[Size\] sqm
> Location: \[Location\] Purchase Price: NGN \[Amount\] Contract Date:
> \[Date\] Next Steps: - You will be contacted regarding survey and
> documentation - For any questions, contact us at +234 912 686 4383
> \[Company footer\]

**8. Dashboard UI Changes**

**8.1 Company Signatures Page (Admin Only)**

A new page accessible from the sidebar under Admin: \"Company
Signatures\"

This page allows admin to upload and manage the Director and Secretary
signatures that are auto-embedded on every contract. It shows:

-   Current Director signature --- preview image + name + upload date +
    \"Replace\" button

-   Current Secretary signature --- same layout

-   \"Upload Signature\" modal --- same draw/upload dual-option as the
    witness signing page

-   A warning if either signature is missing: \"Director signature not
    set --- contracts cannot be generated until this is uploaded\"

> *Only Admin role can access the Company Signatures page. Staff cannot
> upload or view company signatures.*

**8.2 Invoice Table --- Contract Actions**

Add two new action buttons to the invoice table row, visible only when
the invoice status is \"paid\" or \"partial\":

  -----------------------------------------------------------------------
  **Button**       **Visible When**        **Action**
  ---------------- ----------------------- ------------------------------
  Generate         No contract session     Initiates signing session,
  Contract         exists for this invoice generates draft, sends link to
                                           client

  View Contract    A signing session       Opens contract status modal
                   exists                  showing witness signing
                                           progress
  -----------------------------------------------------------------------

**8.3 Contract Status Modal**

Opens when admin clicks \"View Contract\" on an invoice. Shows:

-   Invoice number and client name

-   Signing session status: Pending / Partial / Completed / Expired

-   Link expiry date

-   Witness 1 status: Signed (with name and timestamp) or Awaiting

-   Witness 2 status: Signed (with name and timestamp) or Awaiting

-   \"Resend Link\" button --- resends the signing link email to the
    client

-   \"Generate Final Contract\" button --- only enabled when both
    witnesses have signed

-   \"Extend Link\" button --- extends expiry by 7 more days if the
    original link expired

**8.4 Contracts Section (Optional --- Future)**

A dedicated \"Contracts\" section in the sidebar that lists all
contracts across all clients with their status. Not required for the
initial build --- can be added in a follow-up sprint once the core
signing flow is working.

**9. File Structure Changes**

> eximp-cloves/ ├── routers/ │ ├── contracts.py ← NEW --- initiate,
> status, generate, resend │ └── signing.py ← NEW --- public signing
> page + witness submission ├── pdf_templates/ │ └── contract.html ← NEW
> --- Contract of Sale HTML template ├── templates/ │ ├── sign.html ←
> NEW --- Witness signing page (public, no auth) │ └── dashboard.html ←
> UPDATE --- add contract buttons + modals ├── email_service.py ← UPDATE
> --- add 3 new email functions ├── pdf_service.py ← UPDATE --- add
> generate_contract_pdf() ├── models.py ← UPDATE --- add contract models
> ├── main.py ← UPDATE --- register new routers └── schema.sql ← UPDATE
> --- add 4 new tables

**9.1 New Pydantic Models**

> class WitnessSignatureSubmit(BaseModel): witness_number: int \# 1 or 2
> full_name: str address: str occupation: str signature_base64: str \#
> data:image/\...;base64,\... signature_method: str = \"drawn\" \#
> \"drawn\" or \"uploaded\" class CompanySignatureUpload(BaseModel):
> role: str \# \"director\" or \"secretary\" full_name: str
> signature_base64: str class ExtendSigningLink(BaseModel): days: int =
> 7 \# number of days to extend by

**9.2 Register New Routers in main.py**

> from routers import contracts, signing
> app.include_router(contracts.router, prefix=\"/api/contracts\",
> tags=\[\"contracts\"\]) app.include_router(signing.router,
> tags=\[\"signing\"\]) \# no prefix --- /sign/{token} is at root

**10. Edge Cases and Rules**

  -----------------------------------------------------------------------
  **Scenario**             **Behaviour**
  ------------------------ ----------------------------------------------
  Admin tries to generate  Return error: \"Company signatures not set.
  contract before          Upload Director and Secretary signatures from
  Director/Secretary       the Company Signatures page before generating
  signatures are uploaded  contracts.\"

  Witness opens an expired Show: \"This signing link has expired. Please
  link                     ask \[Client Name\] to request a new link from
                           Eximp & Cloves.\"

  Witness tries to submit  Show: \"You have already submitted your
  after already signing    signature for this contract. Thank you.\"

  Same person tries to     Not technically preventable by the system ---
  sign as both Witness 1   this is a legal/operational responsibility.
  and Witness 2            The UNIQUE constraint only prevents double
                           submission of the same witness_number.

  Client shares link       The token is not guessable (32 bytes of
  publicly and a random    randomness). Risk is negligible. IP address is
  person submits           logged for audit.

  Signature image is       Validate on frontend: max file size 2MB for
  corrupted or too large   uploads. If rendering fails in xhtml2pdf, show
                           blank line --- never crash the PDF.

  Admin generates final    Always fetch company signatures fresh at
  contract but one company generation time --- never cache. The latest
  signature was replaced   active signature is always used.
  since draft              

  Admin needs to void a    No automatic void --- admin contacts client
  contract after it was    directly. A future \"Contract Status\" section
  sent                     can add a manual void/cancel flag.

  Link expiry needs to be  \"Extend Link\" button in the Contract Status
  extended                 modal --- updates expires_at by 7 more days,
                           does not generate a new token.
  -----------------------------------------------------------------------

**11. Testing Checklist**

**11.1 Company Signatures**

-   Admin uploads Director signature --- preview shows correctly in
    Company Signatures page

-   Admin uploads Secretary signature --- preview shows correctly

-   Attempting to generate a contract without signatures shows correct
    error message

-   Replacing a signature --- new one used on next contract, old
    contracts unaffected

**11.2 Contract Initiation**

-   Admin clicks \"Generate Contract\" on a paid/partial invoice →
    signing session created

-   Client receives signing link email with correct link and expiry date

-   Draft contract PDF has correct client details, property, price,
    purchaser signature

-   Draft contract has \"DRAFT --- PENDING WITNESS SIGNATURES\"
    watermark

-   \"Generate Contract\" button changes to \"View Contract\" after
    initiation

**11.3 Witness Signing Page**

-   Valid token → signing page loads with correct contract summary

-   Expired token → \"link has expired\" message shown

-   Already completed session → \"signatures already collected\" message
    shown

-   Draw tab: signature pad renders on desktop (mouse) and mobile
    (touch)

-   Draw tab: touch-action:none prevents page scrolling while drawing on
    mobile

-   Upload tab: file picker opens on click, camera opens on mobile
    (capture attribute)

-   Switching tabs clears the other input

-   Submit button disabled until all fields filled AND signature
    provided

-   Submit with valid data → success confirmation screen shown

-   Submitting same witness_number twice → error message shown

-   IP address and user_agent recorded in witness_signatures table

**11.4 After Both Witnesses Sign**

-   Session status updates to \"completed\"

-   Admin notification email arrives at ADMIN_ALERT_EMAIL with both
    witness names

-   \"Generate Final Contract\" button becomes enabled in Contract
    Status modal

-   Final contract PDF contains all 5 signatures in correct positions

-   Witness names, addresses, and occupations appear correctly in the
    contract

-   Final contract PDF emailed to client

-   Record saved in contract_documents table with document_type =
    \"executed\"

-   Activity log entry created

**11.5 Edge Cases**

-   Corrupt/oversized signature upload → PDF still generates with blank
    line fallback

-   Link expiry extension → expires_at updated, same token still works

-   Resend link → same token, new email sent to client

-   Final contract generation --- always fetches fresh company
    signatures

*End of PRD 5 --- Eximp & Cloves Infrastructure Limited*

*Read alongside PRD 1, PRD 2, PRD 3, PRD 4, and the Addendum*
