from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from contextlib import asynccontextmanager

from routers import (
    auth,
    clients,
    properties,
    invoices,
    payments,
    webhooks,
    verifications,
    analytics,
    sales_reps,
    reports,
    commission,
    contracts,
    signing,
    marketing_contacts,
    marketing_campaigns,
    marketing_segments,
    marketing_analytics,
    marketing_sequences,
    marketing_webhooks,
    marketing_media,
    marketing_events
)
from routers.auth import require_roles
from database import init_db
from scheduler import start_scheduler, stop_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Start the background scheduler
    # await start_scheduler()
    yield
    # Stop the background scheduler
    # await stop_scheduler()

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
marketing_roles = ["admin", "super_admin", "operations", "marketing"]

app.include_router(marketing_contacts.router, prefix="/api/marketing/contacts", tags=["marketing"], dependencies=[Depends(require_roles(marketing_roles))])
app.include_router(marketing_campaigns.router, prefix="/api/marketing/campaigns", tags=["marketing"], dependencies=[Depends(require_roles(marketing_roles))])
app.include_router(marketing_segments.router, prefix="/api/marketing/segments", tags=["marketing"], dependencies=[Depends(require_roles(marketing_roles))])
app.include_router(marketing_analytics.router, prefix="/api/marketing/analytics", tags=["marketing"], dependencies=[Depends(require_roles(marketing_roles))])
app.include_router(marketing_sequences.router, prefix="/api/marketing/sequences", tags=["marketing"], dependencies=[Depends(require_roles(marketing_roles))])
app.include_router(marketing_webhooks.router, tags=["webhooks"])  # tracking at root level, public
app.include_router(marketing_media.router, prefix="/api/marketing/media", tags=["marketing"], dependencies=[Depends(require_roles(marketing_roles))])
app.include_router(marketing_events.router, prefix="/api/marketing/events", tags=["marketing"], dependencies=[Depends(require_roles(marketing_roles))])




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


@app.get("/marketing", response_class=HTMLResponse)
async def marketing_dashboard_page(request: Request):
    return templates.TemplateResponse("marketing_dashboard.html", {"request": request})


@app.get("/marketing/editor", response_class=HTMLResponse)
async def marketing_editor_page(request: Request, id: str):
    return templates.TemplateResponse("marketing_editor.html", {"request": request, "campaign_id": id})


@app.get("/legal", response_class=HTMLResponse)
async def legal_dashboard_page(request: Request):
    return templates.TemplateResponse("legal_dashboard.html", {"request": request})


@app.get("/legal/editor", response_class=HTMLResponse)
async def legal_editor_page(request: Request, id: str):
    return templates.TemplateResponse("legal_editor.html", {"request": request, "invoice_id": id})
@app.get("/legal/{tag:path}")
async def handle_legal_placeholders(tag: str):
    """
    Catch-all for Jinja placeholders like {{ signatures.witness1 }} when viewed 
    literally in the browser editor. Returns a 1x1 transparent PNG for quiet logs.
    Also handles legacy PDF download redirects for backward compatibility.
    """
    # 1. Signature Placeholder Interception
    if "{{" in tag and "signatures" in tag:
        import base64
        from fastapi.responses import Response
        # Return a 1x1 transparent PNG
        return Response(content=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="), media_type="image/png")
    
    # 2. Legacy Redirects for common PDF calls
    if "api/invoices/pdf/" in tag:
        from fastapi.responses import RedirectResponse
        sub_id = tag.split("/")[-1]
        return RedirectResponse(url=f"/api/invoices/{sub_id}/pdf/invoice")
    
    if "api/receipts/pdf/" in tag:
        from fastapi.responses import RedirectResponse
        sub_id = tag.split("/")[-1]
        return RedirectResponse(url=f"/api/invoices/{sub_id}/pdf/receipt")

    # 3. Fall through to 404
    raise HTTPException(status_code=404, detail="Not Found")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Returns a transparent 1x1 pixel for favicon requests to keep logs clean."""
    import base64
    from fastapi.responses import Response
    return Response(content=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="), media_type="image/png")


@app.head("/health")
@app.get("/health")
async def health():
    return {"status": "ok", "service": "Eximp & Cloves Finance System"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
