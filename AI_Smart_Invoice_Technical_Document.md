# AI SMART INVOICE

## Intelligent Vietnamese E-Invoice Processing, Validation & Accounting Automation

---

## 1. Project Overview

**AI Smart Invoice** là hệ thống tự động tiếp nhận, phân tích, chuẩn hóa và kiểm tra hóa đơn đầu vào cho doanh nghiệp Việt Nam.

Khác với một hệ thống OCR hóa đơn thông thường, AI Smart Invoice được thiết kế dựa trên thực tế rằng doanh nghiệp có thể nhận hóa đơn thông qua nhiều nguồn:

* Email
* File XML/PDF đính kèm
* Cổng tra cứu hóa đơn
* Hệ thống/giải pháp hóa đơn điện tử
* Phần mềm kế toán/ERP
* Hệ thống tích hợp dữ liệu hóa đơn
* PDF quốc tế
* Hình ảnh scan/chụp hóa đơn

Hệ thống đặc biệt ưu tiên **file XML của hóa đơn điện tử** khi có sẵn, vì đây là nguồn dữ liệu có cấu trúc và có thể kiểm tra chữ ký điện tử/chữ ký số cùng các thông tin liên quan.

Trong trường hợp chỉ có PDF hoặc hình ảnh, hệ thống chuyển sang pipeline **Computer Vision + OCR + Document AI + Table Extraction + VLM/Transformer**.

Mục tiêu cuối cùng không phải chỉ là:

> "Đọc được chữ trên hóa đơn."

Mà là:

> **Biến hóa đơn không cấu trúc thành một đối tượng dữ liệu kế toán có cấu trúc, có thể kiểm tra, đối soát, lưu trữ và tích hợp vào ERP/accounting system.**

---

# 2. Regulatory Context

Hệ thống được thiết kế trong bối cảnh hóa đơn điện tử tại Việt Nam, đặc biệt liên quan đến:

* Nghị định 123/2020/NĐ-CP
* Thông tư 78/2021/TT-BTC
* Các quy định/hướng dẫn hiện hành liên quan đến hóa đơn điện tử và dữ liệu hóa đơn

Các quy định pháp lý có thể được sửa đổi, bổ sung theo thời gian.

Do đó:

> **Business rules trong hệ thống không nên hard-code cứng vào source code.**

Thay vào đó nên thiết kế:

```text
Regulation
    ↓
Configuration / Rule Engine
    ↓
Validation
```

để có thể cập nhật khi chính sách thay đổi.

---

# 3. Business Problem

Trong thực tế, bộ phận kế toán có thể nhận hàng trăm hoặc hàng nghìn hóa đơn mỗi tháng.

Ví dụ:

```text
Supplier A
    ↓
Email
    ↓
invoice.xml
invoice.pdf

Supplier B
    ↓
Email
    ↓
Link tra cứu
    ↓
Portal
    ↓
Download XML/PDF

Supplier C
    ↓
ERP integration
    ↓
Electronic invoice data

Supplier D
    ↓
PDF

Supplier E
    ↓
Photo / Scan
```

Nếu xử lý thủ công, kế toán phải:

1. Mở email.
2. Download file.
3. Mở XML/PDF.
4. Kiểm tra thông tin người bán.
5. Kiểm tra MST.
6. Kiểm tra số hóa đơn.
7. Kiểm tra ngày.
8. Kiểm tra hàng hóa.
9. Kiểm tra tiền hàng.
10. Kiểm tra VAT.
11. Kiểm tra tổng tiền.
12. Nhập dữ liệu vào phần mềm kế toán.
13. Lưu hóa đơn.
14. Đối chiếu lại khi cần.

Quy trình này:

* tốn thời gian;
* dễ nhập sai;
* khó kiểm soát số lượng lớn;
* khó phát hiện hóa đơn trùng;
* khó phát hiện sai lệch số tiền;
* khó chuẩn hóa dữ liệu từ nhiều nhà cung cấp.

AI Smart Invoice giải quyết phần lớn các bước này tự động.

---

# 4. Invoice Input Sources

Hệ thống hỗ trợ nhiều nguồn đầu vào.

## 4.1. Email Attachment

Đây là một trong những workflow phổ biến.

Ví dụ:

```text
Supplier
    ↓
Email
    ↓
┌────────────────────┐
│ invoice.xml        │
│ invoice.pdf        │
└────────────────────┘
```

Trong trường hợp có cả XML và PDF:

```text
XML
 ↓
Primary structured source

PDF
 ↓
Human-readable representation
 ↓
Visual verification
```

Hệ thống nên coi XML là nguồn dữ liệu ưu tiên khi XML hợp lệ.

---

# 5. XML + PDF Relationship

Một hóa đơn điện tử có thể được cung cấp dưới dạng:

### XML

Chứa dữ liệu có cấu trúc của hóa đơn, cùng thông tin chữ ký điện tử/chữ ký số theo định dạng được sử dụng.

Ví dụ khái niệm:

```xml
<Invoice>
    <THDon>
        ...
    </THDon>

    <NBan>
        ...
    </NBan>

    <NMua>
        ...
    </NMua>

    <DSHHDVu>
        ...
    </DSHHDVu>

    <TToan>
        ...
    </TToan>

    <Signature>
        ...
    </Signature>
</Invoice>
```

### PDF

Là bản thể hiện trực quan để:

* con người đọc;
* kiểm tra;
* lưu trữ;
* đối chiếu với XML.

Vì vậy hệ thống không nên mặc định:

```text
PDF → OCR
```

nếu XML tương ứng đã tồn tại.

Pipeline tốt hơn là:

```text
XML available?
      │
   ┌──┴──┐
   │     │
  YES    NO
   │     │
   ▼     ▼
 XML    PDF/Image
Parser   AI Pipeline
```

---

# 6. Invoice Portal

Một số nhà cung cấp có thể gửi:

```text
Email
  ↓
Invoice lookup URL
  ↓
Lookup code / secret
  ↓
Supplier invoice portal
  ↓
XML / PDF
```

Hệ thống có thể hỗ trợ workflow:

```text
Invoice URL
    ↓
Connector / Integration
    ↓
Download
    ↓
XML/PDF
    ↓
Processing
```

Việc tự động truy cập portal cần tuân thủ:

* điều khoản sử dụng;
* cơ chế xác thực;
* giới hạn truy cập;
* quyền truy cập của doanh nghiệp;
* yêu cầu pháp lý và bảo mật.

Không nên thiết kế hệ thống dựa trên giả định rằng mọi portal đều cho phép crawler tự động.

---

# 7. Accounting / ERP Integration

Đối với doanh nghiệp lớn:

```text
Accounting Software
        │
        ▼
ERP
        │
        ▼
Invoice Integration
        │
        ▼
AI Smart Invoice
```

Hoặc:

```text
Tax / E-Invoice Data Source
            ↓
Integration Layer
            ↓
AI Smart Invoice
            ↓
Accounting DB
```

Nếu nguồn đã cung cấp dữ liệu có cấu trúc thì hệ thống ưu tiên xử lý structured data thay vì OCR.

---

# 8. International PDF Invoice

Một trường hợp khác là invoice từ các nhà cung cấp quốc tế.

Ví dụ:

```text
Cloud provider
Advertising platform
SaaS provider
International vendor
```

Có thể chỉ có:

```text
PDF
```

hoặc:

```text
PDF + email
```

Các invoice này có thể không tuân theo layout hóa đơn điện tử Việt Nam.

Do đó hệ thống cần có:

```text
Vietnamese E-Invoice Pipeline
+
International Invoice Pipeline
```

---

# 9. Input Classification

Bước đầu tiên của hệ thống:

```text
Input
 ↓
Document Classifier
```

Phân loại:

```text
Vietnamese E-Invoice XML
Vietnamese E-Invoice PDF
Scanned Invoice
Photographed Invoice
International Invoice
Receipt
Unknown
```

Ví dụ:

```json
{
    "document_type": "vietnamese_einvoice",
    "format": "xml",
    "confidence": 0.997
}
```

---

# 10. Core Principle: Structured First, AI Second

Đây là nguyên tắc quan trọng nhất của project.

## Nếu XML tồn tại

Không cần:

```text
OCR
```

Không cần:

```text
VLM đọc toàn bộ hóa đơn
```

Mà dùng:

```text
XML Parser
```

---

## Nếu chỉ có PDF/Image

Dùng:

```text
Computer Vision
+
OCR
+
Document AI
+
Table Recognition
+
VLM/Transformer
```

---

# 11. XML Processing Pipeline

Pipeline:

```text
XML
 ↓
XML Schema Validation
 ↓
Parse XML Tree
 ↓
Extract Invoice Metadata
 ↓
Extract Seller
 ↓
Extract Buyer
 ↓
Extract Line Items
 ↓
Extract Payment
 ↓
Extract Tax
 ↓
Digital Signature Verification
 ↓
Normalize
 ↓
Validation
 ↓
Database
```

---

# 12. XML Parser

Không nên lấy dữ liệu bằng cách tìm chuỗi đơn giản.

Ví dụ không nên chỉ:

```python
xml_text.find("MST")
```

Mà nên parse XML:

```python
from lxml import etree

tree = etree.parse("invoice.xml")
root = tree.getroot()
```

Sau đó xác định namespace và schema tương ứng.

Ví dụ khái niệm:

```python
invoice_info = root.find(...)
seller = root.find(...)
buyer = root.find(...)
items = root.find(...)
payment = root.find(...)
```

---

# 13. XML Data Groups

Dữ liệu hóa đơn được chuẩn hóa thành các nhóm:

```text
Invoice Metadata
        +
Seller
        +
Buyer
        +
Line Items
        +
Tax
        +
Payment
        +
Signature
        ↓
Normalized Invoice
```

---

# 14. Invoice Metadata

Các trường quan trọng:

```text
invoice_form_number
invoice_series
invoice_number
issue_date
tax_authority_code
invoice_type
currency
exchange_rate
```

Ví dụ:

```json
{
    "form_number": "1",
    "invoice_series": "C24TKK",
    "invoice_number": "00001234",
    "issue_date": "2026-09-28",
    "currency": "VND"
}
```

---

# 15. Invoice Form Number

Mẫu số giúp xác định loại hóa đơn/biểu mẫu theo quy định và cấu hình phát hành tương ứng.

Ví dụ:

```text
1
2
...
```

Không nên xây business logic dựa trên một vài ví dụ cố định.

Thay vào đó:

```text
form_number
    ↓
Invoice Type Mapping
    ↓
Validation Rules
```

---

# 16. Invoice Series

Ký hiệu hóa đơn được lưu riêng:

```json
{
    "invoice_series": "C24TKK"
}
```

Không nên tách ký hiệu thành các thành phần theo cách suy diễn đơn giản nếu chưa đối chiếu quy tắc pháp lý/định dạng áp dụng.

Ví dụ:

```text
C24TKK
```

có thể được lưu nguyên vẹn để:

* tra cứu;
* đối chiếu;
* hiển thị;
* kiểm tra tính nhất quán.

---

# 17. Invoice Number

Lưu:

```text
00001234
```

theo dạng string thay vì integer.

Lý do:

```text
00001234
```

không nên biến thành:

```text
1234
```

vì sẽ mất biểu diễn gốc.

Schema:

```json
{
    "invoice_number": "00001234"
}
```

---

# 18. Issue Date

Chuẩn hóa về:

```text
YYYY-MM-DD
```

Ví dụ:

```text
28/09/2026
```

→

```text
2026-09-28
```

Đồng thời giữ:

```text
raw_issue_date
```

nếu cần audit.

---

# 19. Tax Authority Code

Đối với hóa đơn có mã của cơ quan thuế, hệ thống lưu:

```json
{
    "tax_authority_code": "..."
}
```

Cần phân biệt:

```text
Seller Tax ID
```

với:

```text
Tax Authority Code
```

Đây là hai loại dữ liệu khác nhau.

---

# 20. Digital Signature

Đối với XML có chữ ký điện tử/chữ ký số, hệ thống không chỉ kiểm tra:

```text
XML đọc được
```

mà nên có module:

```text
Signature Verification
```

Pipeline:

```text
XML
 ↓
Extract Signature
 ↓
Validate Signature Structure
 ↓
Validate Certificate
 ↓
Validate Certificate Chain / Trust
 ↓
Validate Time / Validity
 ↓
Verify Document Integrity
 ↓
Signature Result
```

Kết quả có thể:

```json
{
    "signature": {
        "present": true,
        "integrity_valid": true,
        "certificate_valid": true,
        "status": "VALID"
    }
}
```

Việc xác nhận giá trị pháp lý cuối cùng phải dựa trên quy định và cơ chế xác thực phù hợp; hệ thống AI không nên tự tuyên bố một tài liệu là “hợp pháp” chỉ dựa trên một vài kiểm tra kỹ thuật.

---

# 21. Seller Information

Schema:

```json
{
    "seller": {
        "name": "...",
        "tax_id": "...",
        "address": "...",
        "bank_account": "...",
        "bank_name": "..."
    }
}
```

Các trường:

```text
Seller Name
Seller Tax ID
Seller Address
Bank Account
Bank Name
```

---

# 22. Buyer Information

Schema:

```json
{
    "buyer": {
        "name": "...",
        "tax_id": "...",
        "address": "..."
    }
}
```

Đặc biệt:

```text
buyer_tax_id
```

là trường quan trọng trong các workflow kế toán/thuế của doanh nghiệp.

---

# 23. Line Items

Đây là phần phức tạp nhất của invoice automation.

Schema:

```json
{
    "items": [
        {
            "line_number": 1,
            "product_code": "...",
            "description": "Laptop Dell",
            "unit": "Cái",
            "quantity": 2,
            "unit_price": 25000000,
            "discount": 0,
            "amount_before_tax": 50000000,
            "vat_rate": 10,
            "vat_amount": 5000000
        }
    ]
}
```

---

# 24. Why Line Items Are Difficult

Một invoice có thể có:

```text
5 columns
```

invoice khác:

```text
8 columns
```

invoice khác:

```text
10+ columns
```

Ví dụ:

```text
STT | Tên | ĐVT | SL | Đơn giá | CK | Thuế | Thành tiền
```

Nhưng invoice khác:

```text
No | Product Code | Description | Qty | Unit Price | VAT | Amount
```

Ngoài ra:

* tên sản phẩm có thể xuống nhiều dòng;
* bảng có thể sang trang;
* header có thể lặp lại;
* một cell có thể chứa nhiều dòng;
* cột có thể không có đường kẻ;
* PDF có thể bị lệch;
* ảnh chụp có thể bị nghiêng.

---

# 25. Table AI Pipeline

Đối với PDF/Image:

```text
Invoice
 ↓
Layout Detection
 ↓
Table Detection
 ↓
Row Detection
 ↓
Column Detection
 ↓
Cell Detection
 ↓
OCR
 ↓
Token-to-Cell Assignment
 ↓
Row Reconstruction
 ↓
Line Item JSON
```

---

# 26. Layout Models

Có thể sử dụng:

```text
YOLO
DETR
Table Transformer
LayoutLMv3
DocFormer
PaddleOCR PP-Structure
```

Không nhất thiết phải sử dụng tất cả.

Một kiến trúc thực tế có thể là:

```text
YOLO
 ↓
Detect invoice regions
 ↓
PP-Structure / Table Transformer
 ↓
Extract table
 ↓
OCR
```

---

# 27. PDF/Image OCR Pipeline

Nếu không có XML:

```text
PDF/Image
    ↓
Document Quality Check
    ↓
Perspective Correction
    ↓
Deskew
    ↓
Denoising
    ↓
Contrast Enhancement
    ↓
OCR
    ↓
Bounding Boxes
```

OCR output phải giữ:

```text
text
bbox
confidence
page
```

---

# 28. OCR Output

Ví dụ:

```json
{
    "text": "0312345678",
    "bbox": [120, 250, 310, 280],
    "confidence": 0.98,
    "page": 1
}
```

Không nên chỉ lưu:

```text
"0312345678"
```

vì mất thông tin vị trí.

Bounding box rất quan trọng đối với Document AI.

---

# 29. AI Field Extraction

Từ:

```text
OCR tokens
+
Bounding boxes
+
Visual layout
```

model dự đoán:

```text
SELLER_NAME
SELLER_TAX_ID
BUYER_NAME
BUYER_TAX_ID
INVOICE_NUMBER
ISSUE_DATE
TOTAL
...
```

Có thể dùng:

```text
LayoutLMv3
```

hoặc:

```text
Vision-Language Model
```

---

# 30. VLM Extraction

VLM có thể nhận:

```text
Invoice image
```

và yêu cầu:

```text
Return structured JSON.
```

Ví dụ:

```json
{
    "invoice_number": "000123",
    "issue_date": "2026-09-28",
    "seller_tax_id": "0312345678",
    "total_amount": 55000000
}
```

Nhưng:

> **Không được xem output của VLM là ground truth.**

VLM chỉ là một extraction component.

---

# 31. Hybrid Extraction

Kiến trúc tốt hơn:

```text
OCR
 +
Layout Model
 +
Rules
 +
VLM/Transformer
```

Ví dụ:

```text
OCR phát hiện:
0312345678

Regex:
Tax ID pattern ✓

Layout:
Gần "Mã số thuế" của seller ✓

VLM:
seller_tax_id ✓

Final:
0312345678
```

---

# 32. Summary Information

Các trường chính:

```text
subtotal
total_vat
total_amount
amount_in_words
payment_method
currency
exchange_rate
```

Ví dụ:

```json
{
    "summary": {
        "subtotal": 50000000,
        "vat_amount": 5000000,
        "total_amount": 55000000,
        "amount_in_words": "...",
        "payment_method": "TM/CK",
        "currency": "VND",
        "exchange_rate": 1
    }
}
```

---

# 33. Currency

Nếu:

```text
VND
```

thì:

```text
currency = VND
exchange_rate = null
```

Nếu:

```text
USD
```

thì hệ thống cần lưu:

```text
currency = USD
exchange_rate = ...
```

Không tự động giả định:

```text
1 USD = ...
```

nếu invoice không cung cấp tỷ giá và workflow chưa có nguồn dữ liệu hợp lệ.

---

# 34. Normalized Invoice Schema

Tất cả input cuối cùng phải được chuyển thành một schema chung:

```json
{
    "document": {
        "source": "email",
        "format": "xml",
        "document_type": "vietnamese_einvoice"
    },

    "metadata": {
        "form_number": "1",
        "invoice_series": "C24TKK",
        "invoice_number": "00001234",
        "issue_date": "2026-09-28",
        "tax_authority_code": "..."
    },

    "seller": {
        "name": "...",
        "tax_id": "...",
        "address": "...",
        "bank_account": "..."
    },

    "buyer": {
        "name": "...",
        "tax_id": "...",
        "address": "..."
    },

    "items": [],

    "summary": {
        "subtotal": 50000000,
        "vat_amount": 5000000,
        "total_amount": 55000000,
        "currency": "VND",
        "exchange_rate": null
    },

    "signature": {
        "present": true,
        "status": "VALID"
    },

    "validation": {
        "status": "PASS",
        "errors": [],
        "warnings": []
    }
}
```

---

# 35. Raw Data vs Normalized Data

Đây là điểm rất quan trọng trong hệ thống production.

Không nên chỉ lưu:

```text
Normalized Invoice
```

mà lưu cả:

```text
Original XML/PDF/Image
+
Raw Parsed Data
+
Normalized Data
+
AI Output
+
Validation Result
+
Audit Log
```

Architecture:

```text
Original Document
       ↓
Raw Extraction
       ↓
Normalized Invoice
       ↓
Validated Invoice
```

Điều này giúp audit và debug.

---

# 36. Validation Engine

Validation gồm nhiều lớp.

```text
Layer 1
Schema Validation

Layer 2
Format Validation

Layer 3
Arithmetic Validation

Layer 4
Cross-field Validation

Layer 5
Duplicate Detection

Layer 6
External Verification

Layer 7
AI Anomaly Detection
```

---

# 37. Schema Validation

Ví dụ:

```text
invoice_number exists
issue_date exists
seller exists
items exists
summary exists
```

Nếu thiếu:

```json
{
    "severity": "ERROR",
    "field": "invoice_number",
    "message": "Invoice number is missing"
}
```

---

# 38. Format Validation

Ví dụ:

```text
Tax ID
Invoice Number
Date
Currency
VAT Rate
```

Mỗi field có validator riêng.

Ví dụ concept:

```python
validate_tax_id(tax_id)
validate_invoice_number(invoice_number)
validate_date(issue_date)
validate_currency(currency)
```

---

# 39. Arithmetic Validation

Hệ thống phải tính lại.

Ví dụ:

```text
Quantity = 2
Unit price = 25,000,000

2 × 25,000,000
=
50,000,000
```

Sau đó:

```text
Subtotal
+
VAT
=
Total
```

Ví dụ:

```text
50,000,000
+
5,000,000
=
55,000,000
```

---

# 40. Financial Precision

Không sử dụng:

```python
float
```

cho các phép tính tài chính quan trọng.

Nên sử dụng:

```python
Decimal
```

Ví dụ:

```python
from decimal import Decimal

quantity = Decimal("2")
unit_price = Decimal("25000000")

amount = quantity * unit_price
```

Điều này tránh các vấn đề sai số floating-point.

---

# 41. Rounding

Invoice có thể có quy tắc làm tròn.

Do đó validation nên hỗ trợ:

```text
exact match
```

và:

```text
allowed rounding tolerance
```

Không nên đánh dấu invoice lỗi chỉ vì chênh lệch do làm tròn hợp lệ.

---

# 42. Cross-field Validation

Ví dụ:

```text
VAT rate = 10%
Taxable amount = 50M
VAT amount = 5M
```

Check:

```text
50M × 10%
=
5M
```

Nếu:

```text
VAT amount = 7M
```

→ warning/error tùy rule.

---

# 43. External Taxpayer Verification

Một chức năng nâng cao là kiểm tra MST của người bán với nguồn thông tin thuế/doanh nghiệp phù hợp.

Pipeline:

```text
Seller Tax ID
      ↓
External Verification
      ↓
Taxpayer Information
      ↓
Compare
```

Kiểm tra các thông tin như:

```text
Tax ID exists
Name
Status
Registration information
```

Kết quả:

```json
{
    "tax_id": "0312345678",
    "matched": true,
    "status": "ACTIVE"
}
```

---

# 44. Important Security Principle

Không nên cho LLM tự do truy cập:

```text
Tax database
ERP
Accounting database
```

Nên có:

```text
AI
 ↓
Controlled Tool
 ↓
Read-only API
 ↓
External Source
```

LLM chỉ nhận kết quả cần thiết.

---

# 45. Duplicate Invoice Detection

Một invoice có thể xuất hiện nhiều lần.

Các tầng detection:

### File hash

```text
SHA-256
```

### Perceptual hash

```text
pHash
```

### Business key

```text
seller_tax_id
+
invoice_series
+
invoice_number
+
issue_date
+
total_amount
```

Không nên chỉ dùng filename.

---

# 46. Anomaly Detection

AI Smart Invoice có thể phát hiện:

```text
Unusual amount
Unusual unit price
Unexpected VAT
Repeated invoice
Unusual supplier behavior
Unexpected layout
```

Ví dụ:

```text
Supplier ABC

Average laptop price:
25M

Current invoice:
85M

→ Potential anomaly
```

---

# 47. Anomaly ≠ Fraud

Hệ thống phải phân biệt:

```text
Anomaly detected
```

và:

```text
Fraud confirmed
```

AI chỉ nên đưa ra:

```text
Potential anomaly
Requires review
```

Không nên tự kết luận:

```text
This invoice is fraudulent.
```

---

# 48. Confidence Score

Mỗi field có thể có:

```text
OCR confidence
Extraction confidence
Validation confidence
```

Ví dụ:

```json
{
    "invoice_number": {
        "value": "00001234",
        "confidence": 0.98
    },

    "seller_tax_id": {
        "value": "0312345678",
        "confidence": 0.99
    },

    "total_amount": {
        "value": 55000000,
        "confidence": 0.97
    }
}
```

---

# 49. Human-in-the-loop

Nếu:

```text
confidence >= 0.95
```

có thể:

```text
Auto processing
```

Nếu thấp:

```text
Human review
```

Ví dụ:

```text
Tax ID
confidence = 0.61

→ REVIEW REQUIRED
```

Threshold phải được xác định bằng benchmark thực tế, không nên coi 0.95 là con số cố định cho mọi hệ thống.

---

# 50. Human Review Interface

UI:

```text
┌──────────────────────┬─────────────────────────┐
│                      │ Extracted Data          │
│                      │                         │
│      Invoice         │ Seller: ABC             │
│       Image          │ Tax ID: 0312345678      │
│                      │                         │
│    [Bounding Box]    │ Invoice: 00001234       │
│                      │                         │
│                      │ Total: 55,000,000       │
│                      │                         │
│                      │ ⚠ VAT mismatch          │
└──────────────────────┴─────────────────────────┘
```

Click vào:

```text
Tax ID
```

→ highlight vị trí tương ứng trên invoice.

---

# 51. Audit Trail

Mọi thay đổi của con người phải được lưu.

Ví dụ:

```json
{
    "field": "total_amount",
    "old_value": "55000000",
    "new_value": "56000000",
    "reason": "OCR correction",
    "reviewer": "accounting_user",
    "timestamp": "..."
}
```

Điều này rất quan trọng với hệ thống tài chính.

---

# 52. Database Architecture

Nên lưu tối thiểu:

```text
documents
invoices
invoice_items
invoice_signatures
validation_results
anomalies
reviews
audit_logs
```

---

# 53. Document Table

```sql
documents
---------
id
source
file_name
file_type
storage_path
file_hash
created_at
```

---

# 54. Invoice Table

```sql
invoices
--------
id
document_id
form_number
invoice_series
invoice_number
issue_date
seller_tax_id
buyer_tax_id
currency
exchange_rate
subtotal
vat_amount
total_amount
status
confidence
created_at
updated_at
```

---

# 55. Invoice Items

```sql
invoice_items
-------------
id
invoice_id
line_number
product_code
description
unit
quantity
unit_price
discount
amount_before_tax
vat_rate
vat_amount
```

---

# 56. Signature Table

```sql
invoice_signatures
------------------
id
invoice_id
signature_present
integrity_valid
certificate_valid
certificate_subject
certificate_serial
valid_from
valid_to
status
```

---

# 57. Validation Table

```sql
validation_results
------------------
id
invoice_id
rule_code
field
severity
expected_value
actual_value
message
passed
created_at
```

---

# 58. System Architecture

```text
                        EMAIL
                          │
                        PORTAL
                          │
                    ERP / API
                          │
                    XML / PDF / IMG
                          │
                          ▼
                ┌──────────────────┐
                │ Input Classifier │
                └────────┬─────────┘
                         │
            ┌────────────┴────────────┐
            │                         │
            ▼                         ▼
      XML Processing            AI Document Processing
            │                         │
      XML Parser                  Preprocessing
            │                         │
      Signature                    OCR
      Verification                 │
            │                   Layout Detection
            │                         │
            │                   Table Detection
            │                         │
            │                   Field Extraction
            │                         │
            └────────────┬────────────┘
                         ▼
                  Normalization
                         │
                         ▼
                Validation Engine
                         │
             ┌───────────┼───────────┐
             ▼           ▼           ▼
          Rules       External     Anomaly
                      Verify       Detection
             │           │           │
             └───────────┼───────────┘
                         ▼
                  Confidence Engine
                         │
                ┌────────┴────────┐
                ▼                 ▼
             Approved          Review
                │                 │
                └────────┬────────┘
                         ▼
                  Invoice Database
                         │
                ┌────────┴─────────┐
                ▼                  ▼
               ERP              Export
```

---

# 59. Technology Stack

## Input

```text
Email integration
REST API
File upload
ERP connector
```

## XML

```text
lxml
XML Schema validation
Digital signature verification
```

## Computer Vision

```text
OpenCV
YOLO
DETR
```

## OCR

```text
PaddleOCR
```

## Document AI

```text
LayoutLMv3
Table Transformer
VLM
```

## Backend

```text
FastAPI
Pydantic
SQLAlchemy
Celery
Redis
```

## Database

```text
PostgreSQL
pgvector
```

## Storage

```text
MinIO / S3
```

## MLOps

```text
MLflow
Prometheus
Grafana
Docker
```

---

# 60. Recommended AI Strategy

Không nên bắt đầu project bằng:

```text
VLM → JSON
```

Nên xây baseline:

```text
XML Parser
```

cho structured invoice.

Sau đó:

```text
OCR + Regex
```

cho PDF/Image.

Sau đó nâng cấp:

```text
OCR
+
Layout
+
Transformer/VLM
```

Cuối cùng:

```text
AI
+
Deterministic Validation
+
External Verification
```

---

# 61. Model Comparison

Có thể benchmark:

| Approach     | Ưu điểm                      | Nhược điểm               |
| ------------ | ---------------------------- | ------------------------ |
| XML Parser   | Chính xác, nhanh, structured | Chỉ dùng được khi có XML |
| OCR + Regex  | Đơn giản, dễ debug           | Kém với layout phức tạp  |
| OCR + Layout | Hiểu vị trí                  | Cần training             |
| LayoutLM     | Hiểu text + layout           | Cần annotation           |
| VLM          | Linh hoạt                    | Có thể hallucinate       |
| Hybrid       | Mạnh và dễ kiểm soát hơn     | Kiến trúc phức tạp       |

---

# 62. Recommended Production Principle

Hệ thống nên tuân theo:

> **Structured data first. AI second. Rules always verify. Humans resolve uncertainty.**

Cụ thể:

```text
XML
 ↓
Parser
 ↓
Validation
```

Nếu không có XML:

```text
PDF/Image
 ↓
AI
 ↓
Validation
```

Nếu AI không chắc:

```text
Human
```

---

# 63. End-to-End Example — XML

Input:

```text
invoice.xml
+
invoice.pdf
```

System:

```text
Detect XML
 ↓
Parse XML
 ↓
Extract invoice
 ↓
Verify signature
 ↓
Normalize
 ↓
Calculate totals
 ↓
Validate
 ↓
Check supplier
 ↓
Store
```

Không cần OCR.

PDF chỉ dùng để:

```text
visual verification
```

hoặc khi cần đối chiếu.

---

# 64. End-to-End Example — PDF

Input:

```text
invoice.pdf
```

Pipeline:

```text
PDF
 ↓
Render page
 ↓
Quality Check
 ↓
Deskew
 ↓
OCR
 ↓
Layout
 ↓
Table Detection
 ↓
Field Extraction
 ↓
Normalization
 ↓
Validation
 ↓
Confidence
 ↓
Human Review
```

---

# 65. End-to-End Example — Image

Input:

```text
invoice.jpg
```

Pipeline:

```text
Image
 ↓
Invoice Boundary Detection
 ↓
Perspective Correction
 ↓
Denoising
 ↓
OCR
 ↓
Layout
 ↓
Table
 ↓
Extraction
 ↓
Validation
```

---

# 66. End-to-End Example — Failed Extraction

Suppose OCR returns:

```text
03123A5678
```

instead of:

```text
0312345678
```

The system sees:

```text
Tax ID pattern mismatch
OCR confidence low
```

Instead of silently changing the value:

```text
03123A5678
      ↓
0312345678
```

the system should produce:

```json
{
    "field": "seller_tax_id",
    "status": "REVIEW_REQUIRED",
    "confidence": 0.61
}
```

This is safer for accounting.

---

# 67. Three-Way Matching

Một extension rất mạnh cho enterprise accounting:

```text
Purchase Order
       +
Goods Receipt
       +
Invoice
```

Ví dụ:

```text
PO:
Laptop × 10
25M/unit

GR:
Laptop × 10

Invoice:
Laptop × 12
25M/unit
```

System:

```text
⚠ Quantity mismatch

Expected: 10
Invoice: 12
Difference: +2
```

---

# 68. Natural Language Invoice Search

Sau khi invoice đã được chuẩn hóa, có thể thêm AI Assistant.

User:

```text
"Tìm tất cả hóa đơn của ABC trên 50 triệu trong tháng này."
```

AI chuyển thành:

```text
seller = ABC
total_amount > 50,000,000
date = current month
```

Sau đó backend thực thi query an toàn.

LLM không được phép tự do thực thi SQL.

---

# 69. Active Learning

Human review tạo ra dữ liệu training mới:

```text
AI extraction
      ↓
Human correction
      ↓
Correction dataset
      ↓
Retraining
      ↓
New model
```

Ví dụ:

```text
100 invoices reviewed
↓
37 table corrections
↓
37 new training samples
```

Theo thời gian:

```text
Model improves
Human review decreases
```

---

# 70. Key Project Differentiator

Project này không nên được giới thiệu là:

> **Invoice OCR System**

mà là:

> **Vietnamese E-Invoice Intelligent Processing and Validation Platform**

vì hệ thống bao gồm:

```text
E-Invoice ingestion
        +
XML parsing
        +
Digital signature verification
        +
OCR
        +
Document AI
        +
Table extraction
        +
Financial validation
        +
Taxpayer verification
        +
Anomaly detection
        +
Human review
        +
Accounting integration
```

---

# 71. Final Architecture

```text
                    ┌─────────────────────┐
                    │  EMAIL / ERP / API  │
                    │  PORTAL / UPLOAD     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  INPUT CLASSIFIER    │
                    └──────────┬──────────┘
                               │
               ┌───────────────┴───────────────┐
               │                               │
               ▼                               ▼
       ┌─────────────────┐             ┌─────────────────┐
       │   XML PIPELINE  │             │  AI PIPELINE    │
       │                 │             │                 │
       │ XML Parser      │             │ OpenCV          │
       │ Schema Check    │             │ OCR             │
       │ Signature Check │             │ Layout Model    │
       │                 │             │ Table Model     │
       └────────┬────────┘             │ VLM/Transformer │
                │                      └────────┬────────┘
                │                               │
                └───────────────┬───────────────┘
                                ▼
                     ┌─────────────────────┐
                     │ NORMALIZED INVOICE  │
                     └──────────┬──────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │ VALIDATION ENGINE   │
                     │                     │
                     │ Schema              │
                     │ Format              │
                     │ Arithmetic          │
                     │ Cross-field         │
                     │ Signature           │
                     │ External Verify     │
                     └──────────┬──────────┘
                                │
                     ┌──────────┴──────────┐
                     ▼                     ▼
              ┌──────────────┐      ┌──────────────┐
              │   APPROVED   │      │    REVIEW    │
              └──────┬───────┘      └──────┬───────┘
                     │                     │
                     └──────────┬──────────┘
                                ▼
                     ┌─────────────────────┐
                     │ PostgreSQL + MinIO  │
                     └──────────┬──────────┘
                                │
                     ┌──────────┴──────────┐
                     ▼                     ▼
                   ERP                  Export
```

---

# 72. Final Definition

**AI Smart Invoice** là một hệ thống Document AI hướng đến tự động hóa quy trình xử lý hóa đơn đầu vào tại doanh nghiệp Việt Nam.

Hệ thống không phụ thuộc duy nhất vào OCR. Thay vào đó, nó sử dụng kiến trúc multi-path:

```text
Structured Invoice
       ↓
XML Parser
```

và:

```text
Unstructured Invoice
       ↓
Computer Vision
       ↓
OCR
       ↓
Document AI
       ↓
Table Extraction
```

Hai pipeline hội tụ tại:

```text
Normalized Invoice
       ↓
Validation
       ↓
Verification
       ↓
Anomaly Detection
       ↓
Confidence
       ↓
Human Review
       ↓
Accounting / ERP
```

Triết lý thiết kế:

> **Không dùng AI khi dữ liệu có cấu trúc đã tồn tại. Không tin AI một cách mù quáng khi dữ liệu không cấu trúc. Luôn kiểm tra chéo các dữ liệu tài chính bằng deterministic rules và chuyển các trường hợp không chắc chắn cho con người.**

Đây là điểm biến project từ một **OCR demo** thành một **enterprise-oriented Document AI system**.
