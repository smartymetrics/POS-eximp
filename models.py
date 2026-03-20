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
