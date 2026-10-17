from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional


@dataclass
class ParsedXMLMetadata:
    form_number: Optional[str] = None
    invoice_series: Optional[str] = None
    invoice_number: Optional[str] = None
    issue_date: Optional[str] = None
    tax_authority_code: Optional[str] = None
    currency: str = "VND"
    exchange_rate: Optional[Decimal] = None
    payment_method: Optional[str] = None


@dataclass
class ParsedXMLParty:
    name: Optional[str] = None
    tax_id: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    bank_account: Optional[str] = None
    bank_name: Optional[str] = None


@dataclass
class ParsedXMLLineItem:
    line_number: int
    product_code: Optional[str] = None
    description: str = ""
    unit: Optional[str] = None
    quantity: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    discount_rate: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None
    amount_before_tax: Decimal = Decimal("0")
    vat_rate: Optional[str] = None
    vat_amount: Optional[Decimal] = None


@dataclass
class ParsedXMLSummary:
    subtotal: Decimal = Decimal("0")
    vat_amount: Decimal = Decimal("0")
    total_amount: Decimal = Decimal("0")
    amount_in_words: Optional[str] = None


@dataclass
class ParsedXMLSignature:
    signature_present: bool = False
    digest_valid: bool = False
    certificate_valid: bool = False
    subject_name: Optional[str] = None
    serial_number: Optional[str] = None
    issuer: Optional[str] = None
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    status: str = "NOT_PRESENT"
    message: Optional[str] = None


@dataclass
class RawParsedXMLResult:
    metadata: ParsedXMLMetadata
    seller: ParsedXMLParty
    buyer: ParsedXMLParty
    items: List[ParsedXMLLineItem]
    summary: ParsedXMLSummary
    signature: ParsedXMLSignature
    schema_valid: bool = True
    schema_errors: List[str] = field(default_factory=list)
