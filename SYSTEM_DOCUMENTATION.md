# TÀI LIỆU HỆ THỐNG VÀ HƯỚNG DẪN SỬ DỤNG
# AI SMART INVOICE PROCESSING PLATFORM

> **Nền tảng Tự động hóa Tiếp nhận, Bóc tách, Kiểm tra và Hạch toán Hóa đơn Điện tử Doanh nghiệp Việt Nam**  
> *(Tuân thủ Nghị định 123/2020/NĐ-CP & Thông tư 78/2021/TT-BTC)*

---

## MỤC LỤC
1. [Tổng quan & Những việc đã triển khai](#1-tổng-quan--những-việc-đã-triển-khai)
2. [Chi tiết Kiến trúc & Các Module đã xây dựng](#2-chi-tiết-kiến-trúc--các-module-đã-xây-dựng)
3. [Yêu cầu hệ thống & Cài đặt môi trường](#3-yêu-cầu-hệ-thống--cài-đặt-môi-trường)
4. [Hướng dẫn sử dụng hệ thống](#4-hướng-dẫn-sử-dụng-hệ-thống)
   - [Cách 1: Khởi chạy và Sử dụng qua REST API (Swagger UI)](#cách-1-khởi-chạy-và-sử-dụng-qua-rest-api-swagger-ui)
   - [Cách 2: Gọi trực tiếp qua Python SDK / Orchestrator](#cách-2-gọi-trực-tiếp-qua-python-sdk--orchestrator)
   - [Cách 3: Triển khai trọn gói bằng Docker Compose](#cách-3-triển-khai-trọn-gói-bằng-docker-compose)
   - [Cách 4: Chạy kiểm thử tự động (Unit & Integration Tests)](#cách-4-chạy-kiểm-thử-tự-động-unit--integration-tests)
5. [Cấu hình & Tùy biến Luật nghiệp vụ](#5-cấu-hình--tùy-biến-luật-nghiệp-vụ)
6. [Đặc tả API Endpoints & Dữ liệu mẫu](#6-đặc-tả-api-endpoints--dữ-liệu-mẫu)

---

## 1. Tổng quan & Những việc đã triển khai

Dựa trên sơ đồ kiến trúc luồng xử lý chuẩn và tài liệu kỹ thuật chuyên sâu ([`AI_Smart_Invoice_Technical_Document.md`](AI_Smart_Invoice_Technical_Document.md)), toàn bộ hệ thống đã được thiết kế và hiện thực hóa từ đầu theo chuẩn **Enterprise Clean Architecture / Modular Monolith**, hoàn toàn bằng Python, FastAPI, SQLAlchemy 2.0, Pydantic v2 và Celery.

### Sơ đồ xử lý xuyên suốt của hệ thống:
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

### Danh mục công việc đã hoàn thành:
1. **Thiết lập nền tảng Enterprise & Dependency Management**:
   - `pyproject.toml` và `requirements.txt` với đầy đủ các thư viện sản xuất: `fastapi`, `pydantic>=2.6`, `sqlalchemy>=2.0`, `lxml`, `cryptography`, `openpyxl`, `celery`, `redis`, `minio`.
   - File cấu hình môi trường chuẩn `.env.example`, `.gitignore`, `alembic.ini`.
2. **Cấu hình khai báo tách biệt (Declarative Configs - No Hardcoding)**:
   - `configs/app_config.yaml`: Cấu hình toàn hệ thống, timezone, dung lượng tối đa.
   - `configs/rules/validation_rules.yaml`: Khai báo 4 tầng luật kiểm tra (Schema, Format, Arithmetic, Cross-field) độc lập với mã nguồn.
   - `configs/rules/tax_rates.yaml`: Danh mục chính sách thuế suất VAT tại Việt Nam (0%, 5%, 8%, 10%).
   - `configs/rules/thresholds.yaml`: Ngưỡng tự động duyệt (`>= 0.92`) và trọng số từng trường.
   - `configs/schemas/einvoice_v1_schema.xsd`: Lược đồ XSD kiểm tra định dạng hóa đơn điện tử NĐ 123.
3. **Containerization & hạ tầng**:
   - `docker/Dockerfile`: Multi-stage build hỗ trợ C-dependencies (`libxml2`, `libxmlsec1`, `OpenCV`).
   - `docker/docker-compose.yml`: Triển khai 5 dịch vụ đồng bộ: FastAPI, Celery Worker, PostgreSQL 16, Redis 7, MinIO.
4. **Hiện thực hóa 100% các tầng mã nguồn trong `src/`**:
   - Tầng Ingestion (`src/ingestion/`): Kênh Email, Portal, ERP, REST API.
   - Tầng Phân loại (`src/classifier/`): Bộ nhận diện MIME, Magic bytes và phân luồng "Structured First, AI Second".
   - Nhánh XML (`src/pipelines/xml/`): Parser cây XML theo NĐ 123, XSD Validator, Kiểm định chữ ký số X.509.
   - Nhánh AI (`src/pipelines/ai/`): Tiền xử lý (deskew, rasterize), OCR (PaddleOCR abstraction), Layout Detection, Table Extractor, Semantic Field Extractor.
   - Tầng Chuẩn hóa (`src/normalization/`): Mô hình `NormalizedInvoice` đồng nhất, ép kiểu số học `Decimal` an toàn tuyệt đối.
   - Tầng Kiểm tra (`src/validation/`): 3 trụ cột (Deterministic Rules, Tra cứu MST Tổng cục Thuế, Phát hiện trùng lặp & Bất thường giá).
   - Tầng Đánh giá tin cậy (`src/confidence/`): Tính điểm tin cậy tổng hợp có trọng số, quyết định `APPROVED` hoặc `REVIEW`.
   - Tầng Soát xét kế toán (`src/review/`): Quản lý hàng đợi soát xét, Lưu vết kiểm toán tài chính bất biến (`AuditTrailService`), Thu thập mẫu học tăng cường (`ActiveLearningCollector`).
   - Tầng Cơ sở dữ liệu (`src/database/`): 8 bảng ORM (Documents, Invoices, Items, Signatures, Validations, Anomalies, Reviews, Audit Logs) và Repository Pattern.
   - Tầng Tích hợp ERP & Xuất dữ liệu (`src/integration/`): Sinh định khoản kế toán Nợ 156/133, Có 331; Xuất bảng kê Excel (`.xlsx`), JSON, CSV.
   - Bộ điều phối tổng thể (`src/orchestrator/`): Ghép nối tất cả các module thành quy trình khép kín `InvoicePipelineOrchestrator`.
   - Giao diện REST API (`src/api/`): Bộ định tuyến v1 đầy đủ (`/ingest`, `/invoices`, `/reviews`, `/export`).
5. **Bộ kiểm thử tự động hoàn chỉnh (`tests/`)**:
   - 17 test cases bao phủ toàn diện unit test và integration test. **Vượt qua 100% (17 passed)**.

---

## 2. Chi tiết Kiến trúc & Các Module đã xây dựng

### 2.1. Tầng Ingestion (Thu nạp đầu vào)
- `src/ingestion/base.py`: Đối tượng `RawDocument` mang thông tin luồng, dung lượng, hash SHA-256.
- `src/ingestion/email/service.py`: Adapter kết nối hộp thư IMAP/Graph của nhà cung cấp.
- `src/ingestion/portal/scraper.py`: Adapter phân giải URL tra cứu hóa đơn của các nhà mạng (VNPT, Viettel, MISA, BKAV,...).
- `src/ingestion/erp/connector.py`: Adapter nhận chứng từ gửi từ ERP nguồn.
- `src/ingestion/api/uploader.py`: Adapter nhận file upload trực tiếp qua HTTP multipart.

### 2.2. Tầng Input Classifier (Phân loại & Định tuyến)
- `src/classifier/detector.py`: Đọc magic bytes nhận diện chính xác XML (`<?xml`), PDF (`%PDF`), Ảnh (`PNG`, `JPG`, `TIFF`).
- `src/classifier/router.py`: Áp dụng triết lý cốt lõi:
  - Nếu có XML: Điều hướng sang nhánh **XML Processing** (nhanh hơn, chính xác 100%, có chữ ký số).
  - Nếu chỉ có PDF hoặc Ảnh: Điều hướng sang nhánh **AI Document Processing**.
  - Nếu nhận cả cặp XML + PDF: Lấy XML làm dữ liệu chính thống, liên kết PDF làm tệp đối soát trực quan (Visual Verification).

### 2.3. Nhánh XML Processing
- `src/pipelines/xml/parser.py`: Dùng `lxml.etree` bóc tách cấu trúc TT78/NĐ123: `TTChung` (Metadata), `NBan` (Người bán), `NMua` (Người mua), `DSHHDVu` (Danh sách hàng hóa), `TToan` (Tổng tiền).
- `src/pipelines/xml/schema_validator.py`: Thẩm định cú pháp dựa trên file lược đồ `configs/schemas/einvoice_v1_schema.xsd`.
- `src/pipelines/xml/signature_verifier.py`: Trích xuất khối `<Signature>` / `<DSCKS>`, giải mã chứng thư số X.509, kiểm tra thời hạn hiệu lực, nhà cấp phát (Issuer) và tính toàn vẹn (Integrity).

### 2.4. Nhánh AI Document Processing
- `src/pipelines/ai/preprocessing/preprocessor.py`: Chuyển đổi PDF sang ảnh (300 DPI), xoay thẳng góc nghiêng (Deskew), khử nhiễu (Denoise).
- `src/pipelines/ai/ocr/engine.py`: Chạy engine OCR đa ngôn ngữ tiếng Việt (PaddleOCR / Tesseract fallback), trích xuất bounding box `[x1, y1, x2, y2]`.
- `src/pipelines/ai/layout/detector.py`: Nhận diện các vùng Header, Seller, Buyer, Item Table, Totals, Stamp/Signature.
- `src/pipelines/ai/table/extractor.py`: Trích xuất bảng dòng hàng, phân tách cột (STT, Tên hàng, ĐVT, Số lượng, Đơn giá, Thành tiền, Thuế suất), xử lý trường hợp tên hàng xuống nhiều dòng.
- `src/pipelines/ai/extraction/field_extractor.py`: Trích xuất ngữ nghĩa và tính toán điểm tin cậy cho từng trường.

### 2.5. Tầng Normalization (Chuẩn hóa)
- `src/normalization/schemas.py`: Định nghĩa `NormalizedInvoice` là biểu diễn tiêu chuẩn duy nhất của toàn bộ hệ thống.
- `src/normalization/normalizer.py`:
  - Chuẩn hóa ngày về `YYYY-MM-DD`.
  - Làm sạch mã số thuế (loại bỏ ký tự lạ).
  - Ép kiểu số liệu tài chính sang **`Decimal`** (tuyệt đối không dùng `float` để tránh sai số thập phân trôi dạt trong kế toán).

### 2.6. Tầng Validation Engine (3 Trụ cột kiểm tra)
- `src/validation/rules/`:
  - `schema_rule.py`: Kiểm tra sự hiện diện của các trường bắt buộc theo luật định.
  - `format_rule.py`: Kiểm tra định dạng Regex cho MST (10 số hoặc 13 số có gạch nối `XXXXXXXXXX-XXX`), ký hiệu mẫu số hóa đơn (ví dụ `1C24TKK`).
  - `arithmetic_rule.py`: Kiểm tra phép tính:
    $$\text{Thành tiền} = \text{Số lượng} \times \text{Đơn giá} - \text{Chiết khấu}$$
    $$\text{Tổng tiền chưa thuế} = \sum \text{Thành tiền từng dòng}$$
    $$\text{Tổng thanh toán} = \text{Tổng chưa thuế} + \text{Tiền thuế VAT}$$
    Hỗ trợ dung sai làm tròn `ARITHMETIC_TOLERANCE_VND` (mặc định 1.0 VNĐ).
  - `cross_field_rule.py`: Kiểm tra ngày phát hành không được ở tương lai, MST người bán không được trùng MST người mua.
- `src/validation/external/taxpayer_verifier.py`: Tra cứu MST người bán với cổng Tổng cục Thuế để xác định trạng thái doanh nghiệp (Đang hoạt động, Ngừng hoạt động, Tạm nghỉ).
- `src/validation/anomaly/duplicate_detector.py`: Phát hiện hóa đơn trùng lặp qua 3 tầng bảo vệ:
  1. Hash file tuyệt đối (SHA-256).
  2. Perceptual Hash (pHash) cho file scan.
  3. Business Key chuẩn: `seller_tax_id + invoice_series + invoice_number + issue_date + total_amount`.
- `src/validation/anomaly/anomaly_detector.py`: Cảnh báo bất thường đơn giá, đột biến tổng tiền hoặc thuế suất bất thường (*"Bất thường $\neq$ Gian lận" - chỉ gắn nhãn cần soát xét, không kết luận gian lận*).

### 2.7. Tầng Confidence Engine & Phân luồng
- `src/confidence/scorer.py`: Tính điểm tin cậy tổng hợp dựa trên trọng số các trường quan trọng (MST 20%, Tổng tiền 20%, Số HĐ 15%,...).
- `src/confidence/engine.py`: Điều phối:
  - **`APPROVED` (Tự động duyệt)**: Khi Điểm tin cậy $\ge$ 0.92, **0 lỗi kiểm tra**, chữ ký số XML hợp lệ, MST người bán đang hoạt động.
  - **`REVIEW` (Cần soát xét)**: Khi có lỗi số học, điểm tin cậy thấp hoặc có cảnh báo bất thường.

### 2.8. Tầng Review & Workflow (Human-in-the-loop)
- `src/review/workflow.py`: Quản lý trạng thái hóa đơn: `PENDING_REVIEW` $\rightarrow$ `UNDER_REVIEW` $\rightarrow$ `APPROVED` / `REJECTED`.
- `src/review/audit.py`: Ghi lại nhật ký kiểm toán bất biến: Ai sửa, trường nào, giá trị cũ, giá trị mới, lý do và thời điểm.
- `src/review/active_learning.py`: Ghi nhận dữ liệu kế toán chỉnh sửa để tạo tập dữ liệu huấn luyện lại mô hình AI (Active Learning).

### 2.9. Tầng Lưu trữ & ERP Export
- `src/database/models/`: Mô hình SQLAlchemy ORM cho 8 thực thể dữ liệu.
- `src/database/repositories/invoice_repo.py`: Lưu trữ giao dịch an toàn (ACID transaction).
- `src/integration/erp/exporter.py`: Tự động tạo định khoản kế toán kép:
  - Nợ TK 1561 / 152: Tiền hàng chưa thuế
  - Nợ TK 1331: Thuế GTGT đầu vào
  - Có TK 331: Phải trả người bán (Tổng tiền thanh toán)
- `src/integration/export/file_exporter.py`: Tạo bảng kê mua vào chuẩn Excel (`.xlsx`), JSON kế toán và CSV.

---

## 3. Yêu cầu hệ thống & Cài đặt môi trường

### Yêu cầu tiên quyết:
- **Hệ điều hành**: Windows 10/11, Linux (Ubuntu 20.04+) hoặc macOS.
- **Python**: Phiên bản `>= 3.10` (Hệ thống đã test thành công trên Python 3.13).
- **Cơ sở dữ liệu (Tùy chọn cho chế độ local)**: SQLite có sẵn, hoặc PostgreSQL 15+ cho production.

### Các bước cài đặt:

1. **Mở terminal tại thư mục dự án**:
   ```powershell
   cd d:\UIT\project\Personal_Projects\InvoiceExtraction
   ```

2. **Cài đặt các thư viện cần thiết**:
   ```powershell
   pip install -r requirements.txt
   ```

3. **Cấu hình file biến môi trường**:
   Sao chép file template mẫu:
   ```powershell
   copy .env.example .env
   ```
   *(Trong môi trường phát triển thử nghiệm, hệ thống tự động sử dụng SQLite fallback tại `data/smart_invoice_dev.db` và lưu file trên ổ đĩa nội bộ mà không bắt buộc phải bật Postgres hay MinIO).*

---

## 4. Hướng dẫn sử dụng hệ thống

### Cách 1: Khởi chạy và Sử dụng qua REST API (Swagger UI)

Đây là cách tương tác trực quan và phổ biến nhất đối với người dùng hoặc tích hợp frontend.

1. **Khởi chạy API Server**:
   ```powershell
   uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Truy cập tài liệu Swagger UI**:
   Mở trình duyệt web và truy cập:
   👉 **`http://localhost:8000/docs`**

3. **Các tính năng trên giao diện Web API**:
   - **Upload & Xử lý hóa đơn tức thì**:
     - Vào `POST /api/v1/ingest/upload`
     - Bấm **Try it out** $\rightarrow$ Chọn file XML, PDF hoặc Ảnh từ máy của bạn $\rightarrow$ Bấm **Execute**.
     - Hệ thống sẽ trả về JSON chứa toàn bộ dữ liệu đã bóc tách, kết quả thẩm định, điểm tin cậy và quyết định (`APPROVED` hoặc `REVIEW`).
   - **Xem danh sách hóa đơn đã xử lý**:
     - Vào `GET /api/v1/invoices` $\rightarrow$ Bấm **Execute**.
   - **Lấy hàng đợi hóa đơn cần kế toán duyệt**:
     - Vào `GET /api/v1/reviews/queue` $\rightarrow$ Bấm **Execute**.
   - **Kế toán duyệt và sửa thông tin hóa đơn**:
     - Vào `POST /api/v1/reviews/{invoice_id}/decision` $\rightarrow$ Nhập ID, quyết định (`APPROVED`/`REJECTED`) và các trường đã sửa.
   - **Tải Bảng kê hóa đơn Excel**:
     - Vào `GET /api/v1/export/excel` $\rightarrow$ Bấm **Execute** $\rightarrow$ Bấm **Download file** để nhận file `Bang_Ke_Hoa_Don.xlsx`.

---

### Cách 2: Gọi trực tiếp qua Python SDK / Orchestrator

Bạn có thể nhúng trực tiếp bộ xử lý vào script Python hoặc background job mà không cần bật web server:

```python
import uuid
from src.ingestion.base import IngestionSource, RawDocument
from src.orchestrator.pipeline_runner import InvoicePipelineOrchestrator
from src.core.database import SessionLocal

# 1. Khởi tạo Orchestrator và Session Database
orchestrator = InvoicePipelineOrchestrator()
db = SessionLocal()

# 2. Đọc file hóa đơn (XML, PDF hoặc Ảnh)
file_path = "duong_dan_toi_hoa_don.xml"
with open(file_path, "rb") as f:
    content = f.read()

raw_doc = RawDocument(
    document_id=str(uuid.uuid4()),
    source=IngestionSource.API,
    file_name="hoa_don_dau_vao.xml",
    file_bytes=content
)

# 3. Chạy qua toàn bộ pipeline tự động
result = orchestrator.process_document(raw_doc, db=db)

# 4. Đọc kết quả
print(f"File: {result.file_name}")
print(f"Nhánh xử lý: {result.pipeline_type}")
print(f"Quyết định duyệt: {result.routing_decision.value}")
print(f"Điểm tin cậy: {result.confidence_evaluation.composite_score:.2f}")
print(f"Số HĐ: {result.normalized_invoice.metadata.invoice_number}")
print(f"Tổng tiền: {result.normalized_invoice.summary.total_amount:,.0f} VND")

if result.erp_post_result:
    print(f"Chứng từ ERP: {result.erp_post_result['voucher_id']}")

db.close()
```

---

### Cách 3: Triển khai trọn gói bằng Docker Compose

Dành cho môi trường Server / Production với đầy đủ cơ sở dữ liệu PostgreSQL, MinIO Storage, Redis Queue và Celery Worker:

```bash
docker compose -f docker/docker-compose.yml up -d --build
```

Sau khi khởi chạy:
- **API Server**: `http://localhost:8000/docs`
- **PostgreSQL**: `localhost:5432` (User: `postgres`, Pass: `postgres`, DB: `smart_invoice_db`)
- **MinIO S3 Console**: `http://localhost:9001` (User: `minioadmin`, Pass: `minioadmin`)
- **Redis Cache & Celery**: `localhost:6379`

---

### Cách 4: Chạy kiểm thử tự động (Unit & Integration Tests)

Hệ thống đi kèm bộ test tự động kiểm tra từ đầu đến cuối luồng xử lý:

```powershell
python -m pytest tests/ -v
```

Kết quả hiển thị:
```text
tests/integration/test_pipeline_flow.py::test_end_to_end_xml_pipeline_flow PASSED
tests/integration/test_pipeline_flow.py::test_end_to_end_pdf_ai_pipeline_flow PASSED
tests/unit/test_classifier.py::test_format_detector_xml PASSED
tests/unit/test_classifier.py::test_format_detector_pdf PASSED
tests/unit/test_classifier.py::test_format_detector_image PASSED
tests/unit/test_classifier.py::test_input_classifier_routing_xml PASSED
tests/unit/test_classifier.py::test_input_classifier_routing_pdf PASSED
tests/unit/test_classifier.py::test_classifier_bundle_pairing PASSED
tests/unit/test_confidence_engine.py::test_confidence_engine_routes_valid_invoice PASSED
tests/unit/test_confidence_engine.py::test_confidence_engine_routes_errored_invoice_to_review PASSED
tests/unit/test_normalization.py::test_normalization_from_xml PASSED
tests/unit/test_validation_engine.py::test_validation_engine_on_valid_invoice PASSED
tests/unit/test_validation_engine.py::test_arithmetic_rule_detects_mismatch PASSED
tests/unit/test_validation_engine.py::test_duplicate_detector_records_and_flags PASSED
tests/unit/test_xml_parser.py::test_xml_parser_metadata_and_parties PASSED
tests/unit/test_xml_parser.py::test_xml_parser_line_items_and_totals PASSED
tests/unit/test_xml_parser.py::test_xml_signature_detection PASSED

======================= 17 passed in 0.29s =======================
```

---

## 5. Cấu hình & Tùy biến Luật nghiệp vụ

Mọi quy định nghiệp vụ được cấu hình bằng file YAML trong thư mục `configs/` giúp kế toán hoặc quản trị viên có thể thay đổi chính sách mà **không cần chỉnh sửa code hay khởi động lại hệ thống**:

### 1. Thay đổi ngưỡng tự động duyệt (`configs/rules/thresholds.yaml`):
```yaml
routing:
  auto_approval:
    min_composite_confidence: 0.92   # Đặt 0.90 nếu muốn nới lỏng duyệt tự động
    min_field_confidence: 0.85
    require_zero_validation_errors: true
    require_valid_digital_signature_for_xml: true
```

### 2. Tùy biến luật kiểm tra (`configs/rules/validation_rules.yaml`):
```yaml
arithmetic:
  enabled: true
  tolerance:
    VND: 1.00 # Cho phép sai số làm tròn tối đa 1 VNĐ
    USD: 0.01 # 1 Cent cho ngoại tệ
```

### 3. Cập nhật chính sách thuế VAT (`configs/rules/tax_rates.yaml`):
```yaml
standard_vat_rates:
  - code: "0"
    rate: 0.0
  - code: "5"
    rate: 0.05
  - code: "8"
    rate: 0.08  # Nghị quyết giảm thuế GTGT
  - code: "10"
    rate: 0.10
```

---

## 6. Đặc tả API Endpoints & Dữ liệu mẫu

### 1. `POST /api/v1/ingest/upload`
- **Mục đích**: Tải lên và xử lý tức thời file hóa đơn (XML, PDF, PNG, JPG).
- **Request**: `multipart/form-data` với key `file`.
- **Response mẫu (Hóa đơn XML hợp lệ - Tự động duyệt)**:
```json
{
  "status": "success",
  "document_id": "93f666f8-472d-4591-ba47-1644781b08b3",
  "file_name": "invoice_1234.xml",
  "pipeline_used": "xml_processing",
  "routing_decision": "APPROVED",
  "confidence_score": 1.0,
  "validation_status": "PASS",
  "invoice": {
    "metadata": {
      "form_number": "1",
      "invoice_series": "1C24TKK",
      "invoice_number": "00001234",
      "issue_date": "2026-09-28",
      "tax_authority_code": "TCT-123456789"
    },
    "seller": {
      "name": "CONG TY TNHH CONG NGHE ABC VIET NAM",
      "tax_id": "0100109106",
      "address": "So 123 Pho Hue, Hai Ba Trung, Ha Noi"
    },
    "buyer": {
      "name": "CONG TY CO PHAN PHAN MEM KHOA HOC",
      "tax_id": "0312345678"
    },
    "items": [
      {
        "line_number": 1,
        "description": "May tinh xach tay Dell Latitude",
        "unit": "Cai",
        "quantity": 2.0,
        "unit_price": 25000000.0,
        "amount_before_tax": 50000000.0,
        "vat_rate": "10%",
        "vat_amount": 5000000.0
      }
    ],
    "summary": {
      "subtotal": 50000000.0,
      "vat_amount": 5000000.0,
      "total_amount": 55000000.0,
      "currency": "VND"
    },
    "signature": {
      "present": true,
      "status": "VALID"
    }
  },
  "erp_result": {
    "erp_provider": "misa",
    "success": true,
    "voucher_id": "VOUCHER-3A7B9F10",
    "posting_lines_count": 2,
    "message": "Successfully posted to misa ERP ledger."
  }
}
```

### 2. `GET /api/v1/reviews/queue`
- **Mục đích**: Lấy danh sách các hóa đơn bị nghi vấn, lỗi số học hoặc điểm tin cậy thấp cần kế toán kiểm tra thủ công.

### 3. `POST /api/v1/reviews/{invoice_id}/decision`
- **Mục đích**: Gửi quyết định duyệt hoặc từ chối sau khi kế toán đã kiểm tra, đồng thời cập nhật nhật ký kiểm toán.
- **Request Body mẫu**:
```json
{
  "reviewer": "ketoan_truong",
  "decision": "APPROVED",
  "corrections": {
    "total_amount": 55000000
  },
  "notes": "Đã đối chiếu với bản in gốc của nhà cung cấp, thông tin chính xác."
}
```

### 4. `GET /api/v1/export/excel`
- **Mục đích**: Tải xuống file Excel bảng kê chứng từ mua vào phục vụ báo cáo thuế và đối chiếu kế toán.

---

*Tài liệu này được tạo tự động và đồng bộ trực tiếp với mã nguồn dự án AI Smart Invoice Platform.*
