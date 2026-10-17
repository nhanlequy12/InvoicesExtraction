# HƯỚNG DẪN THIẾT LẬP VÀ VẬN HÀNH HỆ THỐNG
## AI SMART INVOICE PROCESSING PLATFORM

> Tài liệu này hướng dẫn chi tiết từng bước những gì bạn cần chuẩn bị, cấu hình, cài đặt dịch vụ (MinIO, PostgreSQL, Redis) và điền thông tin vào các file để mã nguồn có thể khởi chạy và xử lý hóa đơn điện tử thành công 100%.

---

## MỤC LỤC
1. [Tổng quan kiến trúc & Các dịch vụ phụ trợ](#1-tổng-quan-kiến-trúc--các-dịch-vụ-phụ-trợ)
2. [Chi tiết cấu hình MinIO S3 (Tạo Bucket, Access Key, Secret Key)](#2-chi-tiết-cấu-hình-minio-s3-tạo-bucket-access-key-secret-key)
3. [Chi tiết cấu hình Database (PostgreSQL)](#3-chi-tiết-cấu-hình-database-postgresql)
4. [Chi tiết cấu hình Redis & Celery (Tác vụ bất đồng bộ)](#4-chi-tiết-cấu-hình-redis--celery-tác-vụ-bất-đồng-bộ)
5. [Danh sách các file cần điền và cấu hình](#5-danh-sách-các-file-cần-điền-và-cấu-hình)
6. [Hai cách khởi chạy hệ thống](#6-hai-cách-khởi-chạy-hệ-thống)
   - [Cách 1: Chạy 1 click với Docker Compose (Khuyên dùng nhất)](#cách-1-chạy-1-click-với-docker-compose-khuyên-dùng-nhất)
   - [Cách 2: Chạy trực tiếp trên máy (Python Local Dev)](#cách-2-chạy-trực-tiếp-trên-máy-python-local-dev)
7. [Hướng dẫn Test thử nghiệm hóa đơn đầu tiên](#7-hướng-dẫn-test-thử-nghiệm-hóa-đơn-đầu-tiên)
8. [Các lỗi thường gặp và cách xử lý (Troubleshooting)](#8-các-lỗi-thường-gặp-và-cách-xử-lý-troubleshooting)

---

## 1. Tổng quan kiến trúc & Các dịch vụ phụ trợ

Hệ thống AI Smart Invoice được xây dựng theo chuẩn Modular Monolith với 4 thành phần hạ tầng cốt lõi:

| Thành phần | Vai trò trong hệ thống | Cổng mặc định (Port) |
| :--- | :--- | :--- |
| **FastAPI Backend** | Tiếp nhận upload, phân loại, bóc tách và trả kết quả | `8000` |
| **MinIO (S3 Object Storage)** | Lưu trữ file hóa đơn gốc (XML, PDF, PNG) bất biến | API: `9000`, Web UI: `9001` |
| **PostgreSQL 16** | Lưu dữ liệu hóa đơn đã chuẩn hóa, kết quả kiểm tra luật, audit log | `5432` |
| **Redis 7 & Celery** | Quản lý hàng đợi và tác vụ xử lý hóa đơn ngầm | `6379` |

---

## 2. Chi tiết cấu hình MinIO S3 (Tạo Bucket, Access Key, Secret Key)

Trong hệ thống này, khi bất kỳ hóa đơn nào được gửi vào (qua API, Email, hoặc Portal), file gốc sẽ được băm mã SHA-256 và lưu trữ an toàn vào Object Storage (MinIO hoặc AWS S3) trước khi xử lý bóc tách.

### Bước 2.1: Khởi động MinIO Server
Nếu chưa có sẵn MinIO, bạn có thể chạy nhanh qua Docker bằng 1 lệnh:
```bash
docker run -d --name smart_invoice_minio \
  -p 9000:9000 -p 9001:9001 \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin" \
  -v minio_data:/data \
  minio/minio server /data --console-address ":9001"
```
*(Hoặc tải file `minio.exe` từ trang chủ MinIO nếu không muốn dùng Docker).*

### Bước 2.2: Đăng nhập MinIO Web Console
1. Mở trình duyệt vào địa chỉ: [http://localhost:9001](http://localhost:9001)
2. Điền tài khoản mặc định:
   - **Username**: `minioadmin`
   - **Password**: `minioadmin`

### Bước 2.3: Tạo Bucket lưu hóa đơn
1. Trên menu bên trái của MinIO Console, click vào **Buckets** -> chọn **Create Bucket**.
2. Điền tên Bucket: `smart-invoices` (viết thường, dùng dấu gạch ngang).
3. Bấm **Create Bucket**.
> *Lưu ý*: Trong mã nguồn (`src/storage/object_storage.py`), hệ thống có cơ chế tự động tạo bucket nếu nó chưa tồn tại. Tuy nhiên việc tạo trước trên UI giúp bạn dễ dàng theo dõi trực quan các file được lưu vào thư mục `raw/`.

### Bước 2.4: Lấy Access Key và Secret Key
- Nếu dùng tài khoản quản trị (Root Account):
  - **Access Key**: `minioadmin`
  - **Secret Key**: `minioadmin`
- Nếu muốn tạo Access Key riêng cho ứng dụng:
  1. Vào menu **Access Keys** -> chọn **Create access key**.
  2. Hệ thống sẽ sinh ngẫu nhiên 1 cặp **Access Key** (tương tự UID) và **Secret Key**.
  3. Bấm **Create** và copy lại 2 khóa này.

---

## 3. Chi tiết cấu hình Database (PostgreSQL)

### Bước 3.1: Tạo Database
1. Khởi động PostgreSQL (port `5432`).
2. Dùng pgAdmin, DBeaver hoặc terminal `psql` tạo một database rỗng:
```sql
CREATE DATABASE smart_invoice_db;
```

### Bước 3.2: Cơ chế tự động sinh bảng (Không cần chạy SQL thủ công)
- Bạn **KHÔNG** cần phải gõ lệnh tạo từng bảng bằng tay!
- Trong file `src/main.py`, hệ thống có hàm `lifespan`:
  ```python
  Base.metadata.create_all(bind=engine)
  ```
  Ngay khi server khởi động, SQLAlchemy sẽ tự động phân tích các Model trong `src/database/models/` và tự sinh 6 bảng:
  - `invoices`: Thông tin hóa đơn chuẩn hóa
  - `invoice_items`: Chi tiết từng dòng hàng hóa dịch vụ
  - `invoice_signatures`: Chữ ký số và chứng thư số X.509
  - `documents`: Quản lý tài liệu gốc và mã hash SHA-256
  - `validation_results` & `anomaly_records`: Lịch sử kiểm tra thuế và cảnh báo rủi ro
  - `review_records` & `audit_logs`: Lịch sử duyệt hóa đơn

> **Fallback thông minh**: Nếu bạn chưa kịp cài PostgreSQL, hệ thống sẽ tự động chuyển sang dùng SQLite tại `data/smart_invoice_dev.db` để ứng dụng vẫn chạy được mà không bị crash.

---

## 4. Chi tiết cấu hình Redis & Celery (Tác vụ bất đồng bộ)

Celery được sử dụng để chạy các pipeline AI nặng (OCR, phân tích bố cục LayoutLMv3) dưới nền.
- Cần có Redis đang chạy tại cổng `6379`.
- Chạy nhanh bằng Docker:
  ```bash
  docker run -d --name smart_invoice_redis -p 6379:6379 redis:7-alpine
  ```

---

## 5. Danh sách các file cần điền và cấu hình

### File quan trọng nhất: `.env` (Tại thư mục gốc)
Tạo file `.env` (nếu chưa có, copy từ `.env.example`). Điền các thông số tương ứng với môi trường của bạn:

```env
# ==============================================================================
# CẤU HÌNH MÔI TRƯỜNG CHÍNH THỨC (.env)
# ==============================================================================

APP_ENV=development
APP_NAME="AI Smart Invoice Processing Platform"
DEBUG=true
API_V1_STR=/api/v1
SECRET_KEY=super-secret-key-replace-with-random-uuid-in-prod

# Server
HOST=0.0.0.0
PORT=8000
WORKERS=4

# ------------------------------------------------------------------------------
# 1. DATABASE (POSTGRESQL)
# ------------------------------------------------------------------------------
POSTGRES_SERVER=localhost       # Nếu chạy docker compose thì là: postgres
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=smart_invoice_db

# ------------------------------------------------------------------------------
# 2. REDIS & CELERY (TASK BROKER)
# ------------------------------------------------------------------------------
REDIS_HOST=localhost            # Nếu chạy docker compose thì là: redis
REDIS_PORT=6379
REDIS_DB=0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# ------------------------------------------------------------------------------
# 3. OBJECT STORAGE (MINIO / S3) - ĐÂY LÀ PHẦN BẠN CẦN LƯU Ý
# ------------------------------------------------------------------------------
STORAGE_TYPE=minio              # PHẢI LÀ 'minio' để lưu vào MinIO S3 (mặc định 'local' sẽ lưu ổ cứng)
MINIO_ENDPOINT=localhost:9000   # Nếu chạy docker compose thì là: minio:9000
MINIO_ACCESS_KEY=minioadmin     # Điền Username hoặc Access Key bạn tạo trên MinIO
MINIO_SECRET_KEY=minioadmin     # Điền Password hoặc Secret Key bạn tạo trên MinIO
MINIO_BUCKET_NAME=smart-invoices
MINIO_SECURE=false              # false nếu là http://, true nếu là https://

# ------------------------------------------------------------------------------
# 4. CÁC TÍCH HỢP MỞ RỘNG (ĐÃ CÓ MOCK SẴN, ĐIỀN NẾU TÍCH HỢP THẬT)
# ------------------------------------------------------------------------------
TAX_API_BASE_URL=https://api.gdt.gov.vn/v1
TAX_API_KEY=mock-tax-api-token

ERP_ADAPTER=misa
ERP_ENDPOINT=https://api.erp.company.internal/v1
ERP_AUTH_TOKEN=enterprise-erp-token

EMAIL_IMAP_SERVER=imap.example.com
EMAIL_IMAP_PORT=993
EMAIL_USERNAME=invoices@company.com
EMAIL_PASSWORD=secure-password-here
```

### File `docker/docker-compose.yml` (Đã được cập nhật sẵn)
Nếu bạn chạy bằng Docker, toàn bộ các biến môi trường cho `MinIO`, `PostgreSQL`, `Redis` và `API` đã được cấu hình ăn khớp hoàn toàn với nhau trong file này.

---

## 6. Hai cách khởi chạy hệ thống

### Cách 1: Chạy 1 click với Docker Compose (Khuyên dùng nhất)
Cách này không cần cài đặt Python, không cần cài PostgreSQL hay MinIO thủ công. Docker sẽ tự dựng 5 container cùng lúc.

1. Mở Terminal (PowerShell hoặc CMD) tại thư mục dự án `InvoiceExtraction`.
2. Chạy lệnh:
   ```bash
   docker compose -f docker/docker-compose.yml up --build -d
   ```
3. Sau khoảng 1-2 phút khi Docker tải xong và build ảnh:
   - API Backend: [http://localhost:8000/docs](http://localhost:8000/docs)
   - MinIO Console: [http://localhost:9001](http://localhost:9001) (User: `minioadmin` / Pass: `minioadmin`)
   - PostgreSQL: Port `5432`
   - Redis: Port `6379`

Để tắt các container khi dùng xong:
```bash
docker compose -f docker/docker-compose.yml down
```

---

### Cách 2: Chạy trực tiếp trên máy (Python Local Dev)

Dành cho khi bạn muốn phát triển code và debug trực tiếp bằng Python trên Windows.

#### Bước 1: Chuẩn bị môi trường Python
Yêu cầu: Python 3.10 đến 3.13.
Tạo và kích hoạt môi trường ảo:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

#### Bước 2: Cài đặt thư viện dependencies
```powershell
pip install -r requirements.txt
```
*(Tùy chọn: Nếu muốn chạy OCR giải mã hóa đơn ảnh/PDF thực tế nâng cao, cài thêm: `pip install pymupdf opencv-python-headless paddleocr`)*

#### Bước 3: Đảm bảo MinIO, PostgreSQL, Redis đang bật
- Đảm bảo MinIO đang lắng nghe tại `localhost:9000`
- Đảm bảo PostgreSQL đang chạy database `smart_invoice_db`
- Đảm bảo Redis đang chạy port `6379`

#### Bước 4: Khởi động API Server
```powershell
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```
Server sẽ chạy tại `http://localhost:8000`. Khi khởi động, bạn sẽ thấy log thông báo:
```text
INFO: Initializing database schemas...
INFO: AI Smart Invoice Processing Platform started successfully in development environment.
```

#### Bước 5: (Tùy chọn) Khởi động Celery Worker
Mở 1 cửa sổ Terminal mới để nhận các task xử lý nền:
```powershell
# Lưu ý: Trên Windows, Celery cần thêm tham số -P solo
celery -A src.core.celery_app worker --loglevel=info -P solo
```

---

## 7. Hướng dẫn Test thử nghiệm hóa đơn đầu tiên

### Bước 7.1: Kiểm tra trạng thái hệ thống (Health Check)
Mở trình duyệt hoặc dùng curl:
[http://localhost:8000/health](http://localhost:8000/health)

Kết quả trả về:
```json
{
  "status": "healthy",
  "app_name": "AI Smart Invoice Processing Platform",
  "env": "development",
  "version": "1.0.0"
}
```

### Bước 7.2: Upload hóa đơn mẫu thử nghiệm
Dự án đã chuẩn bị sẵn một file XML hóa đơn điện tử chuẩn tại: `data/sample_invoice.xml`.

1. Truy cập Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
2. Tìm đến mục **Ingestion** -> chọn `POST /api/v1/ingest/upload`.
3. Bấm nút **Try it out**.
4. Tại ô **file**, chọn file `data/sample_invoice.xml` trong thư mục dự án.
5. Bấm **Execute**.

### Bước 7.3: Quan sát kết quả xử lý
Hệ thống sẽ thực hiện toàn bộ luồng tự động:
1. **Lưu file**: Tải file lên MinIO tại `s3://smart-invoices/raw/<hash>.xml`.
2. **Phân loại**: Nhận diện định dạng XML -> chuyển tiếp sang `XML Parser`.
3. **Kiểm tra luật & Tính thuế**: Xác thực thuế suất 10%, tính toán số tiền `55,000,000 VND`, kiểm tra chữ ký số.
4. **Chấm điểm Confidence**: Đạt điểm tuyệt đối (`>= 0.95`).
5. **Duyệt & Hạch toán**: Tự động chuyển trạng thái `APPROVED`, lập bút toán kế toán Nợ 156 / Nợ 133 / Có 331 và lưu toàn bộ vào Database.

### Bước 7.4: Kiểm tra lại trên MinIO & Database
- Vào MinIO Console [http://localhost:9001](http://localhost:9001), vào bucket `smart-invoices/raw/` -> Bạn sẽ thấy file hóa đơn vừa upload đã nằm an toàn tại đây!
- Mở database kiểm tra bảng `invoices` -> Thấy bản ghi hóa đơn số `00001234` từ người bán `CONG TY TNHH CONG NGHE ABC VIET NAM`.

---

## 8. Các lỗi thường gặp và cách xử lý (Troubleshooting)

### 1. Lỗi: `Failed to initialize MinIO client (...) falling back to local storage`
- **Nguyên nhân**: Dịch vụ MinIO chưa được bật, hoặc sai endpoint (`MINIO_ENDPOINT=localhost:9000`), hoặc sai Access/Secret key.
- **Cách xử lý**:
  - Kiểm tra xem container MinIO hoặc tiến trình MinIO đã chạy chưa.
  - Kiểm tra xem biến `STORAGE_TYPE` trong `.env` đã đặt là `minio` chưa. Nếu MinIO không chạy được, hệ thống sẽ tự động fallback lưu vào thư mục `data/uploads/` trên ổ cứng mà không làm gián đoạn chương trình.

### 2. Lỗi: `could not connect to server: Connection refused (PostgreSQL)`
- **Nguyên nhân**: PostgreSQL service chưa chạy hoặc sai mật khẩu `POSTGRES_PASSWORD`.
- **Cách xử lý**:
  - Khởi động service PostgreSQL.
  - Nếu muốn test nhanh mà không cần Postgres, hệ thống sẽ tự động chuyển sang SQLite (`data/smart_invoice_dev.db`).

### 3. Lỗi Celery trên Windows: `ValueError: not enough values to unpack`
- **Nguyên nhân**: Celery mặc định sử dụng cơ chế `fork` của Linux, không tương thích với Windows đa luồng.
- **Cách xử lý**: Luôn truyền thêm cờ `-P solo` khi chạy worker trên Windows:
  ```powershell
  celery -A src.core.celery_app worker --loglevel=info -P solo
  ```

---
*Chúc bạn vận hành hệ thống thành công! Nếu cần tùy chỉnh thêm bất kỳ luật kiểm tra thuế hay bộ kết nối ERP nào, hãy tham khảo các file cấu hình tại thư mục `configs/`.*
