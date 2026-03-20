# Eximp & Cloves — Finance & Receipt System

A full-stack receipt, invoice, and statement of account system for Eximp & Cloves Infrastructure Limited.

---

## What This System Does

- **Admin Dashboard** served at the root URL `/`
- **Create Invoices** with auto-incrementing numbers (EC-000001, EC-000002...)
- **Record Payments** and track balances automatically
- **Generate PDFs** for Invoice, Payment Receipt, and Statement of Account
- **Send branded emails** via Resend with PDF attachments
- **Full audit trail** — every document, payment, and email is logged in Supabase

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python + FastAPI |
| Database | Supabase (PostgreSQL) |
| PDF Generation | WeasyPrint |
| Email Sending | Resend API |
| Auth | JWT (HS256) |
| Hosting | Render (free tier) |
| Keep-alive | UptimeRobot |

---

## Project Structure

```
eximp-cloves/
├── main.py                  # FastAPI entry — serves frontend + API
├── database.py              # Supabase client
├── models.py                # Pydantic request/response models
├── email_service.py         # Resend email logic
├── pdf_service.py           # WeasyPrint PDF generation
├── seed_admin.py            # One-time admin account creation script
├── schema.sql               # Full Supabase database schema
├── requirements.txt
├── render.yaml              # Render deployment config
├── .env.example             # Environment variable template
│
├── routers/
│   ├── auth.py              # Login, JWT, admin management
│   ├── clients.py           # Client CRUD
│   ├── properties.py        # Property catalogue
│   ├── invoices.py          # Invoice creation, PDF, send
│   └── payments.py          # Payment recording
│
├── templates/               # Jinja2 HTML (admin UI)
│   ├── login.html
│   └── dashboard.html
│
└── pdf_templates/           # HTML templates rendered to PDF
    ├── invoice.html
    ├── receipt.html
    └── statement.html
```

---

## Setup Guide (Step by Step)

### Step 1 — Create a Supabase Project

1. Go to [supabase.com](https://supabase.com) and create a free account
2. Create a new project (name it `eximp-cloves`)
3. Once created, go to **Settings → API** and copy:
   - **Project URL** → `SUPABASE_URL`
   - **service_role key** (secret) → `SUPABASE_SERVICE_KEY`
4. Go to the **SQL Editor** in Supabase and paste + run the entire contents of `schema.sql`

---

### Step 2 — Set Up Resend

1. Go to [resend.com](https://resend.com) and create a free account
2. Add your domain `eximps-cloves.com` and verify DNS records
3. Create an API key → `RESEND_API_KEY`
4. Your FROM email will be `finance@eximps-cloves.com`

---

### Step 3 — Configure Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

```env
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGci...
JWT_SECRET=some-very-long-random-secret-string-here
RESEND_API_KEY=re_xxxxxxxxxxxx
FROM_EMAIL=finance@eximps-cloves.com
```

---

### Step 4 — Install & Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Create your first admin account
python seed_admin.py

# Start the server
uvicorn main:app --reload --port 8000
```

Visit `http://localhost:8000` — you'll be redirected to `/login`

---

### Step 5 — Deploy to Render

1. Push your code to a GitHub repository
2. Go to [render.com](https://render.com) and connect your GitHub repo
3. Create a new **Web Service**
4. Render will auto-detect `render.yaml` — click **Deploy**
5. Go to **Environment** in Render and add all your `.env` variables

Your app will be live at `https://eximp-cloves-finance.onrender.com`

---

### Step 6 — Set Up UptimeRobot

1. Go to [uptimerobot.com](https://uptimerobot.com) — free account
2. Add a new monitor:
   - **Type:** HTTP(s)
   - **URL:** `https://your-app.onrender.com/health`
   - **Interval:** Every 5 minutes
3. This prevents Render's free tier from spinning down

---

## API Endpoints

### Auth
| Method | URL | Description |
|---|---|---|
| POST | `/auth/login` | Login, returns JWT token |
| GET | `/auth/me` | Get current admin info |
| POST | `/auth/register` | Create new admin (admin only) |

### Clients
| Method | URL | Description |
|---|---|---|
| GET | `/api/clients/` | List all clients |
| POST | `/api/clients/` | Create new client |
| GET | `/api/clients/{id}` | Get client details |
| GET | `/api/clients/{id}/invoices` | Get all invoices for a client |

### Invoices
| Method | URL | Description |
|---|---|---|
| GET | `/api/invoices/` | List all invoices |
| POST | `/api/invoices/` | Create new invoice |
| GET | `/api/invoices/{id}` | Get invoice with payments |
| POST | `/api/invoices/send` | Send email(s) to client |
| GET | `/api/invoices/{id}/pdf/invoice` | Download invoice PDF |
| GET | `/api/invoices/{id}/pdf/receipt` | Download receipt PDF |
| GET | `/api/invoices/{id}/pdf/statement` | Download statement PDF |

### Payments
| Method | URL | Description |
|---|---|---|
| POST | `/api/payments/` | Record a payment |
| GET | `/api/payments/invoice/{id}` | Get payments for an invoice |

### Properties
| Method | URL | Description |
|---|---|---|
| GET | `/api/properties/` | List all properties |
| POST | `/api/properties/` | Add a property |

---

## How the Invoice Number Works

- Stored in a `invoice_sequences` table in Supabase
- A PostgreSQL function `generate_invoice_number()` atomically increments and returns the next number
- Format: `EC-000001`, `EC-000002`, ... `EC-099999`
- Thread-safe — no duplicate numbers even with concurrent requests

---

## Workflow for Admin Staff

1. **Add client** → Clients section → Add Client
2. **Create invoice** → Click "New Invoice" → fill details → check "Send now" to email immediately
3. **Client pays** → Click "Record Payment" → select invoice → enter amount and reference → check "Send receipt"
4. **Send statement** → Invoices table → click Send → check Statement of Account

---

## Notes

- WeasyPrint requires some system dependencies on Linux. On Render, add this build command:
  ```
  apt-get install -y libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf2.0-0 libffi-dev && pip install -r requirements.txt
  ```
  Or use a `Dockerfile` for more control.

- For WeasyPrint on Render, you may need to use a custom Dockerfile. See the WeasyPrint docs for Linux system dependencies.
