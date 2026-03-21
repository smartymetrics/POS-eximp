# Product Requirements Document
## Eximp & Cloves Infrastructure Limited — Finance & Receipt System
### Remaining Features: Google Form Automation, Pending Verifications, Void Receipt

---

## 1. Project Context

This PRD covers the remaining features to be built on top of an existing FastAPI + Supabase + Resend finance system already in development. The existing system handles:

- Admin dashboard (HTML/CSS/JS served from FastAPI root)
- Invoice creation with auto-incrementing numbers (EC-000001, EC-000002...)
- Payment recording and status tracking
- PDF generation for Invoice, Receipt, and Statement of Account using `xhtml2pdf`
- Email sending via Resend API
- JWT-based admin authentication with Admin and Staff role hierarchy
- Client and property management
- Team member management (create, deactivate, archive, reset password)
- My Profile page (change name, change password)

**Tech stack:** Python + FastAPI, Supabase (PostgreSQL), xhtml2pdf, Resend API, HTML/CSS/JS frontend, hosted on Render free tier.

**Brand:** Eximp & Cloves Infrastructure Limited. Primary colour `#F5A623` (gold), dark colour `#1A1A1A`. RC 8311800. Address: 57B, Isaac John Street, Yaba, Lagos, Nigeria.

---

## 2. Features to Build

### Feature A — Google Form to Supabase Webhook
### Feature B — Pending Verifications Dashboard Section
### Feature C — Void / Reverse Receipt
### Feature D — Updated Invoice PDF with Full Price Breakdown, Co-owner, and Client Signature

---

## 3. Feature A — Google Form Automation

### 3.1 Overview

When a client submits the Google Form (a land subscription/KYC form), an Apps Script on the connected Google Sheet fires a webhook to the FastAPI backend. The backend automatically:

1. Creates or finds the client record in Supabase
2. Creates an invoice showing the full property price, deposit paid, and outstanding balance
3. Sends the invoice email to the client immediately
4. Creates a "pending verification" entry for the admin to review the payment proof
5. Sends an alert email to the admin/finance team notifying them of the new submission

No receipt is sent at this stage. Receipt is only sent after admin manually confirms the payment.

---

### 3.2 Google Sheet Column Mapping

The Google Form responses are stored in a Google Sheet. The Apps Script reads each row on form submission using the following column mapping. Column indices are **1-based**.

> **Important:** Column numbers must be verified against the actual sheet before deploying. The column names below are the exact question text from the form.

| Column # | Form Field Name | Variable Name in Script | Used For |
|---|---|---|---|
| 1 | Timestamp | `timestamp` | Record keeping |
| 2 | Email (form submitter email) | `submitterEmail` | Fallback email |
| 3 | Upload a passport photograph | `passportPhotoUrl` | Stored in DB |
| 4 | Title | `title` | Client name prefix (Mr., Mrs., etc.) |
| 5 | Customer first name | `firstName` | Client full name |
| 6 | Customer last name (surname) | `lastName` | Client full name |
| 7 | Customer middle name | `middleName` | Client full name |
| 8 | Gender | `gender` | Client record |
| 9 | Date of birth | `dob` | Client record |
| 10 | Client's residential address | `address` | Client record |
| 11 | Client's email address | `email` | **Primary email — documents sent here** |
| 12 | Marital Status | `maritalStatus` | Client record |
| 13 | Client's phone number (Whatsapp line) | `phone` | Client record |
| 14 | Occupation | `occupation` | Client record |
| 15 | NIN | `nin` | KYC — stored in DB |
| 16 | International Passport No/NIN Number | `idNumber` | KYC — stored in DB |
| 17 | Upload NIN/International Passport | `idDocumentUrl` | Stored in DB |
| 18 | Nationality | `nationality` | Client record |
| 19 | Property name | `propertyName` | Invoice line item |
| 20 | Next of kin's full name | `nokName` | Client record |
| 21 | Next of kin phone number | `nokPhone` | Client record |
| 22 | Next of kin's email address | `nokEmail` | Client record |
| 23 | Next of kin's occupation | `nokOccupation` | Client record |
| 24 | Relationship | `nokRelationship` | Client record |
| 25 | Next of kin's home address | `nokAddress` | Client record |
| 26 | Ownership Type | `ownershipType` | Invoice — determines if co-owner shown |
| 27 | Full name of the Second Owner | `coOwnerName` | Invoice — shown if co-ownership selected |
| 28 | Email address (Co-owner) | `coOwnerEmail` | Client record |
| 29 | Upload Signature | `signatureUrl` | Embedded on Invoice PDF |
| 30 | Plot size | `plotSize` | Invoice line item |
| 31 | Payment Duration | `paymentDuration` | Invoice payment terms |
| 32 | Deposit Made (In Naira) | `depositAmount` | Payment record — amount paid |
| 33 | Date of Payment/Deposit | `paymentDate` | Payment record |
| 34 | Upload receipt of payment/deposit | `paymentProofUrl` | Stored for admin verification |
| 35 | Outstanding Payment, if any | `outstandingAmount` | Invoice — balance due |
| 36 | Source of Income | `sourceOfIncome` | Client record |
| 37 | How did you get to know about our property | `referralSource` | Client record |
| 38 | Sales Rep / Marketer Name | `salesRepName` | Shown on invoice and receipt |
| 39 | Consent checkbox | `consent` | Stored — must equal "I Confirm and Agree" |

> **Note on Property Name field:** The form uses checkboxes with predefined estate names (Coinfield Estate, Xylara Court, Prime Circle Estate, Northstar Residence, Baclay Estate, Conrad Residence, Other). The value in the sheet may be a single estate name or a comma-separated string if multiple are somehow selected. Use the raw value as the property name on the invoice.

> **Note on Deposit Amount:** The raw value may include commas (e.g. `"200,000"`). Strip commas and convert to float before sending to the API.

> **Note on Outstanding Amount:** May contain the string `"N/A"` for outright payments. If `"N/A"` or empty, set `outstanding_amount` to `0` and `payment_terms` to `"Outright"`. Otherwise set `payment_terms` based on `paymentDuration`.

---

### 3.3 Apps Script Code

Create an Apps Script bound to the Google Sheet (Tools → Script Editor). The script is triggered on form submission (`onFormSubmit` trigger).

```javascript
const WEBHOOK_URL = "https://your-render-app.onrender.com/api/webhooks/form-submission";
const WEBHOOK_SECRET = "your-secret-key-here"; // Must match WEBHOOK_SECRET in .env

function onFormSubmit(e) {
  const row = e.values; // 1-based from trigger, 0-based in array

  // Parse deposit — strip commas, handle empty
  function parseAmount(val) {
    if (!val || val.trim() === "" || val.trim().toUpperCase() === "N/A") return 0;
    return parseFloat(val.toString().replace(/,/g, "").trim()) || 0;
  }

  const depositAmount = parseAmount(row[31]);   // col 32 → index 31
  const outstandingRaw = row[34];               // col 35 → index 34
  const outstandingAmount = parseAmount(outstandingRaw);
  const isOutright = outstandingRaw.trim().toUpperCase() === "N/A" || outstandingRaw.trim() === "";
  const totalAmount = depositAmount + outstandingAmount;

  const payload = {
    // Client
    title:           row[3],
    first_name:      row[4],
    last_name:       row[5],
    middle_name:     row[6],
    gender:          row[7],
    dob:             row[8],
    address:         row[9],
    email:           row[10],   // Primary email
    marital_status:  row[11],
    phone:           row[12],
    occupation:      row[13],
    nin:             row[14],
    id_number:       row[15],
    id_document_url: row[16],
    nationality:     row[17],

    // Property
    property_name:   row[18],
    plot_size:       row[29],

    // Next of kin
    nok_name:         row[19],
    nok_phone:        row[20],
    nok_email:        row[21],
    nok_occupation:   row[22],
    nok_relationship: row[23],
    nok_address:      row[24],

    // Ownership
    ownership_type:  row[25],
    co_owner_name:   row[26],
    co_owner_email:  row[27],
    signature_url:   row[28],

    // Payment
    payment_duration:    row[30],
    deposit_amount:      depositAmount,
    payment_date:        row[32],
    payment_proof_url:   row[33],
    outstanding_amount:  outstandingAmount,
    total_amount:        totalAmount,
    payment_terms:       isOutright ? "Outright" : row[30],

    // Other
    source_of_income:   row[35],
    referral_source:    row[36],
    sales_rep_name:     row[37],
    consent:            row[38],
    timestamp:          row[0],
    submitter_email:    row[1],
    passport_photo_url: row[2],
  };

  const options = {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify(payload),
    headers: { "X-Webhook-Secret": WEBHOOK_SECRET },
    muteHttpExceptions: true,
  };

  try {
    const response = UrlFetchApp.fetch(WEBHOOK_URL, options);
    Logger.log("Status: " + response.getResponseCode());
    Logger.log("Response: " + response.getContentText());
  } catch (err) {
    Logger.log("Error: " + err.toString());
  }
}
```

**Setup Instructions for the Apps Script:**
1. In Google Sheets, go to **Extensions → Apps Script**
2. Paste the script above, replacing `WEBHOOK_URL` and `WEBHOOK_SECRET`
3. Save the script
4. Go to **Triggers** (clock icon in sidebar) → **Add Trigger**
5. Choose function: `onFormSubmit`
6. Event source: `From spreadsheet`
7. Event type: `On form submit`
8. Save — grant permissions when prompted

---

### 3.4 New FastAPI Webhook Endpoint

**File:** `routers/webhooks.py` (new file)

**Endpoint:** `POST /api/webhooks/form-submission`

**Authentication:** Validates `X-Webhook-Secret` header against `WEBHOOK_SECRET` environment variable. Returns `403` if missing or incorrect.

**Logic (in order):**

1. **Validate secret** — check `X-Webhook-Secret` header
2. **Validate consent** — if `consent` field is not `"I Confirm and Agree"`, log and return `400`
3. **Upsert client** — search for existing client by `email`. If found, update record. If not found, create new client. Store all KYC fields.
4. **Create invoice** — generate invoice number via `generate_invoice_number()` DB function. Set:
   - `amount` = `total_amount` (full property price = deposit + outstanding)
   - `amount_paid` = `deposit_amount`
   - `balance_due` = `outstanding_amount`
   - `payment_terms` = `"Outright"` if outstanding is 0, else value from `payment_duration`
   - `property_name` = `property_name` from form
   - `plot_size_sqm` = parsed numeric value from `plot_size` (e.g. strip "SQM", "sqm")
   - `sales_rep_name` = `sales_rep_name` from form
   - `co_owner_name` = `co_owner_name` if ownership type is not sole
   - `signature_url` = `signature_url` from form
   - `payment_proof_url` = `payment_proof_url` from form
   - `passport_photo_url` = `passport_photo_url` from form
   - `source` = `"google_form"` (to distinguish from manually created invoices)
5. **Record deposit payment** — if `deposit_amount > 0`, insert a row into the `payments` table with `reference = payment_date + "_form_deposit"` and `amount = deposit_amount`
6. **Create pending verification** — insert a row into `pending_verifications` table (see schema below)
7. **Send invoice email** — call `send_invoice_email(invoice, client)` as a background task
8. **Send admin alert email** — call `send_admin_alert_email(invoice, client)` as a background task
9. **Return** `{"message": "Processed", "invoice_number": "EC-XXXXXX"}`

---

### 3.5 Database Schema Changes

Add the following to `schema.sql` and run in Supabase SQL Editor:

```sql
-- Add new columns to invoices table
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS sales_rep_name VARCHAR(255);
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS co_owner_name VARCHAR(255);
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS co_owner_email VARCHAR(255);
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS signature_url TEXT;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS payment_proof_url TEXT;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS passport_photo_url TEXT;
ALTER TABLE invoices ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'manual';

-- Add KYC columns to clients table
ALTER TABLE clients ADD COLUMN IF NOT EXISTS title VARCHAR(20);
ALTER TABLE clients ADD COLUMN IF NOT EXISTS middle_name VARCHAR(100);
ALTER TABLE clients ADD COLUMN IF NOT EXISTS gender VARCHAR(20);
ALTER TABLE clients ADD COLUMN IF NOT EXISTS dob VARCHAR(50);
ALTER TABLE clients ADD COLUMN IF NOT EXISTS marital_status VARCHAR(50);
ALTER TABLE clients ADD COLUMN IF NOT EXISTS occupation VARCHAR(100);
ALTER TABLE clients ADD COLUMN IF NOT EXISTS nin VARCHAR(50);
ALTER TABLE clients ADD COLUMN IF NOT EXISTS id_number VARCHAR(100);
ALTER TABLE clients ADD COLUMN IF NOT EXISTS id_document_url TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS nationality VARCHAR(100);
ALTER TABLE clients ADD COLUMN IF NOT EXISTS passport_photo_url TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS nok_name VARCHAR(255);
ALTER TABLE clients ADD COLUMN IF NOT EXISTS nok_phone VARCHAR(50);
ALTER TABLE clients ADD COLUMN IF NOT EXISTS nok_email VARCHAR(255);
ALTER TABLE clients ADD COLUMN IF NOT EXISTS nok_occupation VARCHAR(100);
ALTER TABLE clients ADD COLUMN IF NOT EXISTS nok_relationship VARCHAR(100);
ALTER TABLE clients ADD COLUMN IF NOT EXISTS nok_address TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS source_of_income VARCHAR(100);
ALTER TABLE clients ADD COLUMN IF NOT EXISTS referral_source VARCHAR(100);

-- PENDING VERIFICATIONS TABLE
CREATE TABLE IF NOT EXISTS pending_verifications (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    invoice_id UUID NOT NULL REFERENCES invoices(id),
    client_id UUID NOT NULL REFERENCES clients(id),
    payment_proof_url TEXT,
    deposit_amount DECIMAL(15,2),
    payment_date VARCHAR(100),
    sales_rep_name VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending'
        CHECK (status IN ('pending', 'confirmed', 'rejected')),
    reviewed_by UUID REFERENCES admins(id),
    reviewed_at TIMESTAMPTZ,
    rejection_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE pending_verifications ENABLE ROW LEVEL SECURITY;
```

---

### 3.6 New Environment Variable

Add to `.env` and Render environment settings:

```env
WEBHOOK_SECRET=your-long-random-secret-string
ADMIN_ALERT_EMAIL=finance@eximps-cloves.com  # or team email for notifications
```

---

### 3.7 Admin Alert Email

When a new form submission arrives, send an alert email to `ADMIN_ALERT_EMAIL` containing:

- Client full name and email
- Property name, plot size, deposit amount
- Invoice number generated
- Payment proof URL (clickable link to Google Drive file)
- A direct link to the Pending Verifications section of the dashboard

Subject: `New Subscription — [Client Name] — [Invoice Number]`

---

## 4. Feature B — Pending Verifications Dashboard Section

### 4.1 Overview

A new section in the admin dashboard where all unverified form submissions are listed. Admins review the payment proof and either confirm or reject each one.

### 4.2 Navigation

Add a **"Pending Verifications"** nav item in the sidebar. It should show a **badge count** of how many items are pending (e.g. a red dot with a number). Both Admin and Staff roles can access this section.

### 4.3 Pending Verifications Table

Each row shows:

| Column | Content |
|---|---|
| Client Name | Full name |
| Property | Property name + plot size |
| Deposit | Amount deposited |
| Payment Date | Date from form |
| Sales Rep | Who facilitated the sale |
| Submitted | Timestamp of form submission |
| Proof | "View Proof" button — opens payment proof URL in new tab |
| Actions | "Confirm Payment" button (green) + "Reject" button (red) |

Only show rows with `status = 'pending'`. Confirmed and rejected entries move to a collapsible "History" section below, sorted by most recent.

### 4.4 Confirm Payment Flow

When admin clicks **"Confirm Payment"**:

1. Open a confirmation modal showing:
   - Client name, invoice number, deposit amount
   - The payment proof image/link
   - A note: "Confirming this will mark the payment as verified and send the Receipt + Statement of Account to the client."
2. Admin clicks **"Confirm & Send Documents"**
3. Backend:
   - Updates `pending_verifications.status` to `'confirmed'`
   - Records `reviewed_by` and `reviewed_at`
   - Calls `send_receipt_and_statement_email()` — sends both PDFs in one email
4. Show success toast: "Payment confirmed. Receipt + Statement sent to [client email]."

### 4.5 Reject Payment Flow

When admin clicks **"Reject"**:

1. Open a rejection modal with:
   - Client name and invoice number
   - A required text field: "Reason for rejection" (e.g. "Payment proof blurry, cannot verify", "Amount on proof does not match deposit stated")
2. Admin clicks **"Reject Submission"**
3. Backend:
   - Updates `pending_verifications.status` to `'rejected'`
   - Stores `rejection_reason`, `reviewed_by`, `reviewed_at`
   - Marks the invoice `status` back to `'unpaid'`
   - Sends a polite rejection email to the client (see below)
4. Show toast: "Submission rejected. Client has been notified."

### 4.6 Rejection Email to Client

**Subject:** `Action Required — Payment Verification Issue | Eximp & Cloves`

**Body:**
> Dear [Client Name],
>
> Thank you for your subscription to [Property Name].
>
> Unfortunately, we were unable to verify your payment proof for Invoice [EC-XXXXXX]. Reason: [rejection_reason].
>
> Please contact us or resubmit your payment evidence at your earliest convenience so we can process your subscription.
>
> We apologise for any inconvenience.

Signed with company footer (address, phone, website).

---

## 5. Feature C — Void / Reverse Receipt

### 5.1 Overview

Admins can void a receipt that was issued incorrectly (e.g. after a payment was confirmed but later found to be fraudulent, or entered in error).

### 5.2 Where to Access

On the **Invoices** table, add a **"Void"** action button that is only visible when `invoice.status = 'paid'` or `'partial'`. Only users with `role = 'admin'` can see and use this button.

### 5.3 Void Flow

1. Admin clicks **"Void Receipt"** on an invoice
2. A modal opens showing:
   - Invoice number, client name, amount paid so far
   - A required **"Reason for voiding"** text field
   - A warning: "This will reverse all payments on this invoice, mark it as unpaid, and log the action. This cannot be undone."
3. Admin clicks **"Void Receipt"**
4. Backend:
   - Inserts a row into a new `void_log` table (see schema below)
   - Soft-deletes all payments on this invoice by setting `is_voided = true` on each payment row
   - Recalculates `amount_paid = 0` and sets `invoice.status = 'unpaid'`
   - If the invoice originated from a Google Form, also sets the associated `pending_verifications.status` back to `'pending'`
5. Show toast: "Receipt voided successfully. Invoice [EC-XXXXXX] is now marked as unpaid."
6. Optionally (admin can tick a checkbox in the modal): **Send void notification email to client**

### 5.4 Void Notification Email to Client (Optional)

**Subject:** `Important Notice — Receipt Correction | Eximp & Cloves`

**Body:**
> Dear [Client Name],
>
> We are writing to inform you that Receipt [EC-XXXXXX], issued on [date], has been voided due to an administrative correction.
>
> Reason: [void_reason]
>
> Please contact our office immediately so we can resolve this matter.

### 5.5 Database Schema for Void Log

```sql
-- Add is_voided column to payments table
ALTER TABLE payments ADD COLUMN IF NOT EXISTS is_voided BOOLEAN DEFAULT false;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS voided_by UUID REFERENCES admins(id);
ALTER TABLE payments ADD COLUMN IF NOT EXISTS voided_at TIMESTAMPTZ;

-- VOID LOG TABLE
CREATE TABLE IF NOT EXISTS void_log (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    invoice_id UUID NOT NULL REFERENCES invoices(id),
    client_id UUID NOT NULL REFERENCES clients(id),
    voided_by UUID NOT NULL REFERENCES admins(id),
    reason TEXT NOT NULL,
    amount_reversed DECIMAL(15,2),
    notify_client BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE void_log ENABLE ROW LEVEL SECURITY;
```

---

## 6. Feature D — Updated Invoice PDF

### 6.1 Full Price Breakdown

The invoice PDF must show the complete financial picture, not just the deposit. Layout for the totals section:

```
Property:           [Property Name] — [Plot Size]
─────────────────────────────────────────────
Total Property Price:          NGN X,XXX,XXX.00
Deposit Paid:              (−) NGN   XXX,XXX.00
─────────────────────────────────────────────
Balance Due:                   NGN   XXX,XXX.00
Payment Plan:                  [Outright / X Months Installment]
```

For outright payments where `outstanding = 0`, the Balance Due line shows `NGN 0.00` and a green "PAID IN FULL" badge appears next to it.

### 6.2 Co-owner Display

When `co_owner_name` is present and `ownership_type` is not sole ownership, add a co-owner line in the "Bill To" section:

```
Primary Owner:    Mr. Adebayo Okonkwo
Co-owner:         Mrs. Chioma Okonkwo
```

### 6.3 Sales Rep Block

Already exists in the current system. Ensure `sales_rep_name` from the form is passed through to the PDF template. The block shows:

```
SALES REPRESENTATIVE
[Sales Rep Name]
Sales Team · Eximp & Cloves Infrastructure Limited
```

### 6.4 Client Signature on Invoice

The `signature_url` field contains a Google Drive link to the client's uploaded signature image. The invoice PDF should:

1. Attempt to download the image from the URL and embed it in the PDF
2. If the download fails or the URL is empty, show a blank signature line instead
3. Display it in the footer area under "Client Signature" on the left side, with "Authorized Signature" on the right side (existing)

**Important:** Google Drive "open" links (`https://drive.google.com/open?id=XXX`) must be converted to direct download links (`https://drive.google.com/uc?export=download&id=XXX`) before attempting to embed. Extract the file ID from the URL and reconstruct it.

```python
def drive_url_to_direct(url: str) -> str:
    """Convert Google Drive share URL to direct download URL."""
    import re
    match = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', url)
    if match:
        file_id = match.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    return url
```

### 6.5 Next of Kin Section on Invoice

Add a small "Next of Kin" section to the invoice PDF below the client details block:

```
NEXT OF KIN
[NOK Full Name] — [Relationship]
[NOK Phone]
```

This makes the invoice a more complete subscription document.

---

## 7. New API Endpoints Summary

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| POST | `/api/webhooks/form-submission` | Receives Google Form data | Webhook secret header |
| GET | `/api/verifications/` | List all pending verifications | JWT |
| PATCH | `/api/verifications/{id}/confirm` | Confirm payment + send docs | JWT |
| PATCH | `/api/verifications/{id}/reject` | Reject + notify client | JWT |
| POST | `/api/invoices/{id}/void` | Void a receipt | JWT — Admin only |
| GET | `/api/verifications/count` | Returns count of pending items (for badge) | JWT |

---

## 8. Updated Pydantic Models

Add to `models.py`:

```python
class WebhookFormPayload(BaseModel):
    # Client
    title: Optional[str] = None
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    gender: Optional[str] = None
    dob: Optional[str] = None
    address: Optional[str] = None
    email: str
    marital_status: Optional[str] = None
    phone: Optional[str] = None
    occupation: Optional[str] = None
    nin: Optional[str] = None
    id_number: Optional[str] = None
    id_document_url: Optional[str] = None
    nationality: Optional[str] = None
    passport_photo_url: Optional[str] = None
    # Next of kin
    nok_name: Optional[str] = None
    nok_phone: Optional[str] = None
    nok_email: Optional[str] = None
    nok_occupation: Optional[str] = None
    nok_relationship: Optional[str] = None
    nok_address: Optional[str] = None
    # Ownership
    ownership_type: Optional[str] = None
    co_owner_name: Optional[str] = None
    co_owner_email: Optional[str] = None
    signature_url: Optional[str] = None
    # Property
    property_name: str
    plot_size: Optional[str] = None
    # Payment
    payment_duration: Optional[str] = None
    deposit_amount: float = 0
    payment_date: Optional[str] = None
    payment_proof_url: Optional[str] = None
    outstanding_amount: float = 0
    total_amount: float = 0
    payment_terms: str = "Outright"
    # Other
    source_of_income: Optional[str] = None
    referral_source: Optional[str] = None
    sales_rep_name: Optional[str] = None
    consent: Optional[str] = None
    timestamp: Optional[str] = None
    submitter_email: Optional[str] = None


class VerificationConfirm(BaseModel):
    pass  # No body needed — invoice_id is in the URL


class VerificationReject(BaseModel):
    reason: str


class VoidReceiptRequest(BaseModel):
    reason: str
    notify_client: bool = False
```

---

## 9. Register New Router in main.py

```python
from routers import auth, clients, properties, invoices, payments, webhooks, verifications

app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])
app.include_router(verifications.router, prefix="/api/verifications", tags=["verifications"])
```

---

## 10. Dashboard UI Changes Summary

### Sidebar additions
- Add **"Pending Verifications"** nav item with a live count badge (red circle with number, updates on load)
- Badge should disappear when count is 0

### Pending Verifications section (new)
- Table of pending items (columns described in Feature B)
- "View Proof" button opens Google Drive URL in new tab
- "Confirm Payment" button → confirmation modal → sends Receipt + Statement
- "Reject" button → rejection modal with required reason field
- Collapsible "History" section below showing confirmed/rejected entries

### Invoices table additions
- "Void" button visible only on paid/partial invoices, visible only to Admin role
- Void modal with required reason field and optional "notify client" checkbox

### Pending Verifications confirm modal
- Shows client name, invoice number, deposit amount
- Shows payment proof as a clickable link (not embedded — just a link since it's a Google Drive URL)
- Warning text explaining what will happen
- "Confirm & Send Documents" primary button
- "Cancel" ghost button

---

## 11. Email Templates Summary

### New emails to build

| Email | Trigger | Recipient |
|---|---|---|
| Admin alert | New form submission | `ADMIN_ALERT_EMAIL` env var |
| Rejection notice | Admin rejects verification | Client |
| Void notification | Admin voids receipt (optional) | Client |

All emails follow the existing style: dark `#1A1A1A` header with gold `#F5A623` accent bar, company footer with address and contact details.

---

## 12. Security Considerations

- The webhook endpoint does **not** require a JWT token — it is called by Google Apps Script, not a logged-in admin. It is secured instead by the `X-Webhook-Secret` header.
- The secret must be a long random string stored in `.env` as `WEBHOOK_SECRET` and set in Render environment variables. It must also be hardcoded in the Apps Script (see Section 3.3).
- The webhook should validate that `consent == "I Confirm and Agree"` before processing — reject silently if not.
- Voiding a receipt is Admin-only — the backend must enforce `role == "admin"` even if the frontend button is hidden from Staff.
- Google Drive URLs in `signature_url` and `payment_proof_url` are stored as-is. They are not downloaded and re-hosted — only the signature is downloaded at PDF generation time and only in a try/except block so a failed download never breaks PDF generation.

---

## 13. Error Handling

| Scenario | Behaviour |
|---|---|
| Webhook secret missing/wrong | Return `403 Forbidden` |
| Consent not given | Return `400 Bad Request`, log the row |
| Client email already exists | Upsert — update existing record, create new invoice |
| `deposit_amount` is 0 | Still create invoice and pending verification, do not create payment record |
| Signature image download fails | Use blank signature line on PDF, do not crash |
| Google Drive URL malformed | Skip signature embed, log warning |
| `total_amount` is 0 | Return `400` — cannot create an invoice with zero value |
| Admin confirms already-confirmed verification | Return `400 Already confirmed` |

---

## 14. File Structure Changes

```
eximp-cloves/
├── routers/
│   ├── webhooks.py        ← NEW — handles Google Form submissions
│   └── verifications.py   ← NEW — pending verification CRUD
├── templates/
│   └── dashboard.html     ← UPDATE — add pending verifications section + void modal
├── pdf_templates/
│   └── invoice.html       ← UPDATE — full price breakdown, co-owner, NOK, signature
├── email_service.py       ← UPDATE — add admin alert, rejection, void notification emails
├── models.py              ← UPDATE — add new Pydantic models
├── main.py                ← UPDATE — register new routers
└── schema.sql             ← UPDATE — add new columns and tables
```

---

## 15. Testing Checklist

Before going live, verify the following manually:

- [ ] Submit the Google Form with a test entry → confirm webhook fires and invoice is created
- [ ] Check the invoice email arrives at the client's email address
- [ ] Check the admin alert email arrives at `ADMIN_ALERT_EMAIL`
- [ ] Confirm the pending verification appears in the dashboard
- [ ] Click "View Proof" — confirm it opens the Google Drive file
- [ ] Click "Confirm Payment" → confirm receipt + statement email sent to client
- [ ] Click "Reject" with a reason → confirm rejection email sent to client
- [ ] Void a paid invoice → confirm invoice status resets to unpaid
- [ ] Submit a form with `Outstanding = N/A` → confirm `payment_terms = "Outright"`
- [ ] Submit a form with a co-owner → confirm both names appear on invoice PDF
- [ ] Submit a form with a signature → confirm signature appears on invoice PDF
- [ ] Submit a form with a missing signature URL → confirm PDF generates without crashing
- [ ] Try hitting the webhook with wrong secret → confirm `403` response
- [ ] Try voiding as a Staff user → confirm it is blocked

---

*End of PRD — Eximp & Cloves Infrastructure Limited Finance System v2*