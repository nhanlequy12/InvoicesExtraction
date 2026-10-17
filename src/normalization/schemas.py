from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class DocumentInfo(BaseModel):
    document_id: str
    source: str = "api"
    format: str = "xml"
    document_type: str = "vietnamese_einvoice"
    file_name: str
    file_hash: Optional[str] = None
    storage_path: Optional[str] = None


class InvoiceMetadata(BaseModel):
    form_number: Optional[str] = Field(None, description="Mẫu số hóa đơn (ví dụ: 1 hoặc 2)")
    invoice_series: str = Field(..., description="Ký hiệu hóa đơn (ví dụ: 1C24TKK)")
    invoice_number: str = Field(..., description="Số hóa đơn (ví dụ: 00001234, giữ nguyên string)")
    issue_date: str = Field(..., description="Ngày lập hóa đơn YYYY-MM-DD")
    tax_authority_code: Optional[str] = Field(None, description="Mã của cơ quan thuế cấp")
    invoice_type: Optional[str] = Field("standard", description="Loại hóa đơn GTGT / bán hàng")


class InvoiceParty(BaseModel):
    name: str = Field(..., description="Tên đơn vị / cá nhân")
    tax_id: Optional[str] = Field(None, description="Mã số thuế 10 hoặc 13 số")
    address: Optional[str] = Field(None, description="Địa chỉ")
    phone: Optional[str] = Field(None, description="Số điện thoại")
    bank_account: Optional[str] = Field(None, description="Số tài khoản ngân hàng")
    bank_name: Optional[str] = Field(None, description="Tên ngân hàng")


class InvoiceLineItem(BaseModel):
    line_number: int = Field(..., description="STT dòng")
    product_code: Optional[str] = Field(None, description="Mã sản phẩm / dịch vụ")
    description: str = Field(..., description="Tên hàng hóa, dịch vụ")
    unit: Optional[str] = Field(None, description="Đơn vị tính")
    quantity: Optional[Decimal] = Field(None, description="Số lượng")
    unit_price: Optional[Decimal] = Field(None, description="Đơn giá")
    discount: Optional[Decimal] = Field(Decimal("0"), description="Tiền chiết khấu")
    amount_before_tax: Decimal = Field(..., description="Thành tiền trước thuế")
    vat_rate: Optional[str] = Field(None, description="Thuế suất (0%, 5%, 8%, 10%)")
    vat_amount: Optional[Decimal] = Field(Decimal("0"), description="Tiền thuế GTGT dòng")


class InvoiceSummary(BaseModel):
    subtotal: Decimal = Field(..., description="Tổng tiền chưa thuế")
    vat_amount: Decimal = Field(..., description="Tổng tiền thuế GTGT")
    total_amount: Decimal = Field(..., description="Tổng tiền thanh toán")
    currency: str = Field("VND", description="Đơn vị tiền tệ (VND, USD,...)")
    exchange_rate: Optional[Decimal] = Field(None, description="Tỷ giá hối đoái")
    amount_in_words: Optional[str] = Field(None, description="Số tiền viết bằng chữ")


class InvoiceSignatureInfo(BaseModel):
    present: bool = False
    digest_valid: bool = False
    certificate_valid: bool = False
    status: str = "MISSING" # VALID, EXPIRED_OR_UNTRUSTED, MISSING
    subject_name: Optional[str] = None
    serial_number: Optional[str] = None
    message: Optional[str] = None


class InvoiceConfidenceInfo(BaseModel):
    composite_confidence: float = 1.0
    field_confidences: Dict[str, float] = Field(default_factory=dict)


class NormalizedInvoice(BaseModel):
    """
    Canonical Normalized Invoice Data Model.
    Unified representation for downstream validation, accounting matching,
    database persistence, and ERP export.
    """
    document: DocumentInfo
    metadata: InvoiceMetadata
    seller: InvoiceParty
    buyer: InvoiceParty
    items: List[InvoiceLineItem]
    summary: InvoiceSummary
    signature: InvoiceSignatureInfo
    confidence: InvoiceConfidenceInfo = Field(default_factory=InvoiceConfidenceInfo)
