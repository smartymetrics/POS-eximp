from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID


# ─── AUTH ────────────────────────────────────────────────────
class AdminLogin(BaseModel):
    email: EmailStr
    password: str


class AdminCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: str = "staff"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin: dict


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ResetPasswordRequest(BaseModel):
    new_password: str


class UpdateProfileRequest(BaseModel):
    full_name: str


# ─── CLIENTS ─────────────────────────────────────────────────
class ClientCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    title: Optional[str] = None
    middle_name: Optional[str] = None
    gender: Optional[str] = None
    dob: Optional[str] = None


class ClientUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    title: Optional[str] = None
    middle_name: Optional[str] = None
    gender: Optional[str] = None
    dob: Optional[str] = None
    occupation: Optional[str] = None
    marital_status: Optional[str] = None
    nationality: Optional[str] = None
    nok_name: Optional[str] = None
    nok_phone: Optional[str] = None
    nok_email: Optional[str] = None
    nok_occupation: Optional[str] = None
    nok_relationship: Optional[str] = None
    nok_address: Optional[str] = None
    nin: Optional[str] = None
    id_number: Optional[str] = None
    passport_photo_url: Optional[str] = None
    id_document_url: Optional[str] = None


# ─── PROPERTIES ──────────────────────────────────────────────
class PropertyCreate(BaseModel):
    name: str
    location: str
    estate_name: Optional[str] = None
    plot_size_sqm: Optional[Decimal] = None
    price_per_sqm: Optional[Decimal] = None
    starting_price: Decimal
    description: Optional[str] = None
    available_plot_sizes: Optional[str] = None
    is_active: bool = True


class PropertyUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    estate_name: Optional[str] = None
    plot_size_sqm: Optional[Decimal] = None
    price_per_sqm: Optional[Decimal] = None
    starting_price: Optional[Decimal] = None
    description: Optional[str] = None
    available_plot_sizes: Optional[str] = None
    is_active: Optional[bool] = None
    is_archived: Optional[bool] = None


# ─── INVOICES ────────────────────────────────────────────────
class InvoiceCreate(BaseModel):
    client_id: str
    property_id: Optional[str] = None
    property_name: Optional[str] = None
    property_location: Optional[str] = None
    plot_size_sqm: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    amount: Decimal
    quantity: int = 1
    payment_terms: str = "Outright"
    invoice_date: date
    due_date: date
    notes: Optional[str] = None
    co_owner_name: Optional[str] = None
    co_owner_email: Optional[str] = None

class InvoiceUpdate(BaseModel):
    due_date: Optional[date] = None
    payment_terms: Optional[str] = None
    sales_rep_name: Optional[str] = None
    sales_rep_id: Optional[str] = None
    property_name: Optional[str] = None
    quantity: Optional[int] = None
    unit_price: Optional[Decimal] = None
    amount_paid: Optional[Decimal] = None
    notes: Optional[str] = None
    reason: Optional[str] = None # For due date changes
    co_owner_name: Optional[str] = None
    co_owner_email: Optional[str] = None

class SendDocumentRequest(BaseModel):
    invoice_id: str
    document_types: list[str]  # ["invoice", "receipt", "statement"]


# ─── PAYMENTS ────────────────────────────────────────────────
class PaymentCreate(BaseModel):
    invoice_id: str
    client_id: str
    reference: str
    amount: Decimal
    payment_method: str = "Bank Transfer"
    payment_type: str = "payment" # payment or refund
    payment_date: date
    notes: Optional[str] = None

class PaymentUpdate(BaseModel):
    payment_date: Optional[date] = None
    reference: Optional[str] = None
    payment_method: Optional[str] = None
    payment_type: Optional[str] = None
    amount: Optional[Decimal] = None
    notes: Optional[str] = None


# ─── WEBHOOKS & VERIFICATIONS ────────────────────────────────
class WebhookFormPayload(BaseModel):
    # Client
    title: Optional[str] = None
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    gender: Optional[str] = None
    dob: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
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
    signature_base64: Optional[str] = None
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
    quantity: int = 1
    payment_terms: str = "Outright"
    # Other
    source_of_income: Optional[str] = None
    referral_source: Optional[str] = None
    purchase_purpose: Optional[str] = None
    sales_rep_name: Optional[str] = None
    sales_rep_phone: Optional[str] = None
    consent: Optional[str] = None
    timestamp: Optional[str] = None
    submitter_email: Optional[str] = None


class VerificationConfirm(BaseModel):
    pass  # No body needed — invoice_id is in the URL


class VerificationReject(BaseModel):
    reason: str

class VerificationUpdate(BaseModel):
    payment_proof_url: Optional[str] = None
    deposit_amount: Optional[Decimal] = None
    payment_date: Optional[str] = None


class VoidReceiptRequest(BaseModel):
    reason: str
    notify_client: bool = False

# --- ANALYTICS MODELS (PRD 1) ---

class KPIDelta(BaseModel):
    total_revenue: Optional[float] = None
    amount_collected: Optional[float] = None
    new_clients: Optional[float] = None
    total_refunds: Optional[float] = None

class KPISummary(BaseModel):
    total_revenue: Optional[float] = None
    amount_collected: Optional[float] = None
    total_refunds: float = 0.0
    outstanding_balance: Optional[float] = None
    new_clients: int
    plots_sold: int
    avg_deal_size: Optional[float] = None
    collection_rate: Optional[float] = None
    pending_verifications: int
    overdue_count: int = 0
    partial_count: int = 0
    delta: Optional[KPIDelta] = None

class RevenueTrend(BaseModel):
    labels: list[str]
    invoiced: list[float]
    collected: list[float]
    refunds: list[float] = []

class EstateStat(BaseModel):
    name: str
    revenue: float
    deals: int

class PaymentStatusStats(BaseModel):
    paid: int
    partial: int
    unpaid: int
    overdue: int = 0

class ReferralSourceStat(BaseModel):
    source: str
    count: int

class RepLeaderboardEntry(BaseModel):
    rep_name: str
    deals: int
    total_value: float
    avg_deal_size: float
    top_estate: str
    collected: float
    collection_rate: float

class ActivityLogEntry(BaseModel):
    id: str
    event_type: str
    description: str
    client_id: Optional[str] = None
    invoice_id: Optional[str] = None
    performed_by_name: Optional[str] = None
    created_at: str

# --- SALES REP MODELS (PRD 2) ---

class SalesRepCreate(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    commission_rate: Decimal = Decimal("5.0")

class SalesRepUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    commission_rate: Optional[Decimal] = None
    is_active: Optional[bool] = None

class ResolveUnmatchedRequest(BaseModel):
    unmatched_id: str
    target_rep_id: str  # The ID of the existing/newly created rep to map to

# --- REPORT MODELS (PRD 2) ---

class ReportScheduleCreate(BaseModel):
    report_type: str
    frequency: str  # "daily", "weekly", "monthly"
    recipients: list[EmailStr]
    format: str = "pdf"

class ReportEmailRequest(BaseModel):
    report_type: str
    start_date: str = ""
    end_date: str = ""
    format: str = "pdf"
    emails: str
    message: Optional[str] = None

# --- COMMISSION MODELS (PRD 4) ---

class CommissionRateCreate(BaseModel):
    sales_rep_id: str
    estate_name: str
    rate: Decimal
    effective_from: date
    reason: Optional[str] = None

class CommissionAdjustment(BaseModel):
    adjusted_amount: Decimal
    adjustment_reason: str

class CommissionPayout(BaseModel):
    sales_rep_id: str
    earning_ids: list[str]
    reference: Optional[str] = None
    notes: Optional[str] = None
    total_amount: Optional[Decimal] = None  # If set, distribute as partial payment; else pay all in full

class DefaultRateUpdate(BaseModel):
    rate: Decimal
    reason: Optional[str] = None


class CommissionVoidRequest(BaseModel):
    reason: str

class CommissionEarning(BaseModel):
    id: UUID
    sales_rep_id: UUID
    invoice_id: UUID
    payment_id: UUID
    client_id: UUID
    estate_name: str
    payment_amount: Decimal
    commission_rate: Decimal
    commission_amount: Decimal
    final_amount: Decimal
    is_paid: bool
    paid_at: Optional[datetime] = None
    is_voided: bool = False
    voided_at: Optional[datetime] = None
    void_reason: Optional[str] = None
    created_at: datetime

# --- PRD 5: CONTRACT SIGNING PORTAL ---

class WitnessSignatureSubmit(BaseModel):
    witness_number: Optional[int] = None  # 1 or 2, optional for auto-assignment
    full_name: str
    address: str
    occupation: str
    signature_base64: str  # data:image/...;base64,...
    signature_method: str = "drawn"  # "drawn" or "uploaded"

class CompanySignatureUpload(BaseModel):
    role: str  # "director" or "secretary"
    full_name: Optional[str] = None
    signature_base64: str

class ExtendSigningLink(BaseModel):
    days: int = 7
