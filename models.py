from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date, datetime
from decimal import Decimal
import uuid


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


class ClientUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None


# ─── PROPERTIES ──────────────────────────────────────────────
class PropertyCreate(BaseModel):
    name: str
    location: str
    estate_name: Optional[str] = None
    plot_size_sqm: Optional[Decimal] = None
    price_per_sqm: Optional[Decimal] = None
    total_price: Decimal
    description: Optional[str] = None


class PropertyUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    estate_name: Optional[str] = None
    plot_size_sqm: Optional[Decimal] = None
    price_per_sqm: Optional[Decimal] = None
    total_price: Optional[Decimal] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


# ─── INVOICES ────────────────────────────────────────────────
class InvoiceCreate(BaseModel):
    client_id: str
    property_id: Optional[str] = None
    property_name: Optional[str] = None
    property_location: Optional[str] = None
    plot_size_sqm: Optional[Decimal] = None
    amount: Decimal
    payment_terms: str = "Outright"
    invoice_date: date
    due_date: date
    notes: Optional[str] = None


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
    payment_date: date
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
