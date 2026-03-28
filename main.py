from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from contextlib import asynccontextmanager

from routers import auth, clients, properties, invoices, payments, webhooks, verifications, analytics, sales_reps, reports, commission, contracts, signing
from database import init_db
from scheduler import start_scheduler, stop_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Start the background scheduler
    await start_scheduler()
    yield
    # Stop the background scheduler
    await stop_scheduler()

app = FastAPI(title="Eximp & Cloves - Finance System", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(clients.router, prefix="/api/clients", tags=["clients"])
app.include_router(properties.router, prefix="/api/properties", tags=["properties"])
app.include_router(invoices.router, prefix="/api/invoices", tags=["invoices"])
app.include_router(payments.router, prefix="/api/payments", tags=["payments"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])
app.include_router(verifications.router, prefix="/api/verifications", tags=["verifications"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(sales_reps.router, prefix="/api/sales-reps", tags=["sales-reps"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(commission.router, prefix="/api/commission", tags=["commission"])
app.include_router(contracts.router, prefix="/api/contracts", tags=["contracts"])
app.include_router(signing.router, tags=["signing"])




@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return RedirectResponse(url="/dashboard")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/clients", response_class=HTMLResponse)
async def clients_page(request: Request):
    return templates.TemplateResponse("clients.html", {"request": request})


@app.get("/invoices", response_class=HTMLResponse)
async def invoices_page(request: Request):
    return templates.TemplateResponse("invoices.html", {"request": request})


@app.get("/new-transaction", response_class=HTMLResponse)
async def new_transaction_page(request: Request):
    return templates.TemplateResponse("new_transaction.html", {"request": request})


@app.head("/health")
@app.get("/health")
async def health():
    return {"status": "ok", "service": "Eximp & Cloves Finance System"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
