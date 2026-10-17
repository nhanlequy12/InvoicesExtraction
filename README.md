# AI SMART INVOICE PLATFORM

## Intelligent Vietnamese E-Invoice Processing, Validation & Accounting Automation

Enterprise-grade Document AI & Automated Accounting Platform for Vietnamese E-Invoices (Nghị định 123/2020/NĐ-CP & Thông tư 78/2021/TT-BTC).

---

## 1. System Architecture Pipeline

The system is built strictly in accordance with the enterprise processing workflow:

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

## 2. Enterprise Directory Structure

```text
InvoiceExtraction/
├── configs/                                # Declarative Configuration & Rules
│   ├── app_config.yaml                     # Global platform configuration
│   ├── rules/
│   │   ├── validation_rules.yaml           # Deterministic business rules (Layer 1 - 4)
│   │   ├── tax_rates.yaml                  # Vietnamese VAT policies (0%, 5%, 8%, 10%)
│   │   └── thresholds.yaml                 # Confidence scoring & auto-approval thresholds
│   └── schemas/
│       └── einvoice_v1_schema.xsd          # Official XSD schema (ND123/TT78)
│
├── docker/                                 # Containerization & Deployment
│   ├── Dockerfile                          # Multi-stage production container
│   └── docker-compose.yml                  # API + Celery + Postgres + Redis + MinIO
│
├── src/                                    # Application Source Code
│   ├── main.py                             # FastAPI Application Entrypoint
│   │
│   ├── core/                               # Core Infrastructure
│   │   ├── config.py                       # Pydantic Settings & environment variables
│   │   ├── logging.py                      # Structured logging
│   │   ├── database.py                     # SQLAlchemy 2.0 Engine & Session pool
│   │   └── celery_app.py                   # Distributed background task runner
│   │
│   ├── storage/                            # Object Storage Abstraction
│   │   └── object_storage.py               # MinIO (S3) & Local Disk with SHA-256
│   │
│   ├── ingestion/                          # Input Channels Layer
│   │   ├── base.py                         # RawDocument model & BaseIngestionService
│   │   ├── email/service.py                # Email IMAP / Graph invoice poller
│   │   ├── portal/scraper.py               # Supplier lookup portal downloader
│   │   ├── erp/connector.py                # Inbound ERP queue listener
│   │   └── api/uploader.py                 # REST API multipart upload handler
│   │
│   ├── classifier/                         # Input Classifier Layer
│   │   ├── detector.py                     # Magic bytes & MIME format detector
│   │   ├── router.py                       # Routing engine ('Structured First, AI Second')
│   │   └── schemas.py                      # ClassificationResult & Pipeline types
│   │
│   ├── pipelines/                          # Processing Branches
│   │   ├── xml/                            # Branch 1: XML Processing
│   │   │   ├── parser.py                   # lxml Vietnamese e-invoice parser
│   │   │   ├── schema_validator.py         # XSD Schema compliance validator
│   │   │   ├── signature_verifier.py       # XMLDSig & X.509 digital certificate verifier
│   │   │   └── models.py                   # Raw XML intermediate representations
│   │   │
│   │   └── ai/                             # Branch 2: AI Document Processing
│   │       ├── preprocessing/              # Page rendering, deskew & DPI check
│   │       ├── ocr/                        # PaddleOCR / Tesseract engine
│   │       ├── layout/                     # LayoutLM / YOLO region detector
│   │       ├── table/                      # Table boundary & cell row extractor
│   │       └── extraction/                 # Key-value field extractor & VLM fallback
│   │
│   ├── normalization/                      # Normalization Layer
│   │   ├── schemas.py                      # Canonical NormalizedInvoice schema
│   │   └── normalizer.py                   # Mapping raw XML/AI into unified Decimal model
│   │
│   ├── validation/                         # Validation Engine Layer
│   │   ├── engine.py                       # Orchestrator aggregating 3 validation pillars
│   │   ├── rules/                          # Pillar 1: Deterministic Rules
│   │   │   ├── schema_rule.py              # Mandatory fields check
│   │   │   ├── format_rule.py              # Regex format checks (Tax ID 10/13, Series)
│   │   │   ├── arithmetic_rule.py          # Decimal math with tolerance
│   │   │   └── cross_field_rule.py         # Semantic consistency
│   │   ├── external/                       # Pillar 2: External Tax Authority Verification
│   │   │   └── taxpayer_verifier.py        # General Dept of Taxation (GDT) connector
│   │   └── anomaly/                        # Pillar 3: Anomaly & Duplicate Detection
│   │       ├── duplicate_detector.py       # Multi-tier duplicate check (SHA256, Business Key)
│   │       └── anomaly_detector.py         # Price spikes & tax anomalies ('Anomaly != Fraud')
│   │
│   ├── confidence/                         # Confidence Engine Layer
│   │   ├── scorer.py                       # Weighted field confidence aggregator
│   │   ├── engine.py                       # Routing decision (APPROVED vs REVIEW)
│   │   └── schemas.py                      # Routing models
│   │
│   ├── review/                             # Human-in-the-Loop Review & Audit
│   │   ├── workflow.py                     # Review state machine (PENDING -> REVIEWED)
│   │   ├── audit.py                        # Financial immutable audit trail
│   │   └── active_learning.py              # Sample collector for AI retraining
│   │
│   ├── database/                           # Persistence Layer
│   │   ├── models/                         # SQLAlchemy ORM Tables (documents, invoices, items, validations, reviews)
│   │   └── repositories/                   # Transactional repository pattern
│   │
│   ├── integration/                        # Downstream Integration Layer
│   │   ├── erp/                            # Accounting double-entry vouchers (Nợ 156, Nợ 133, Có 331)
│   │   └── export/                         # Excel (.xlsx), JSON, and CSV export generators
│   │
│   ├── orchestrator/                       # End-to-End Orchestrator
│   │   └── pipeline_runner.py              # Links all layers into single processing loop
│   │
│   └── api/                                # REST API Layer
│       ├── dependencies.py                 # Dependency injection
│       └── v1/                             # Endpoints: /ingest, /invoices, /reviews, /export
│
├── tests/                                  # Comprehensive Test Suite
│   ├── conftest.py                         # Pytest fixtures & sample electronic invoices
│   ├── unit/                               # Unit tests for all modules
│   └── integration/                        # End-to-end integration tests
│
├── pyproject.toml                          # Modern Python build config
├── requirements.txt                        # Dependency specifications
├── .env.example                            # Configuration environment template
└── README.md                               # Project documentation
```

---

## 3. Core Architectural Principles

1. **Structured Data First, AI Second**:
   - If an XML file is provided, it is parsed directly using `lxml` and validated against official XSD schemas. Digital signatures are checked cryptographically.
   - AI/OCR is only invoked for unstructured PDF and image inputs.
   - When XML and PDF are both received, XML is the authoritative financial data source, while PDF is kept for visual verification.

2. **Deterministic Rules Always Verify**:
   - AI outputs are never blindly trusted.
   - Strict `Decimal` precision is used for all financial arithmetic to avoid floating-point errors.
   - Rules are defined declaratively in `configs/rules/` rather than hardcoded in source code.

3. **External Tax Authority Verification (Isolated & Read-Only)**:
   - Validates seller Tax IDs against official tax records without granting unrestricted database access to AI models.

4. **Anomaly != Fraud**:
   - Irregular transactions or price deviations are flagged as `Potential Anomaly / Requires Review` for human judgment.

5. **Financial Audit Trail & Human-in-the-Loop**:
   - Invoices with high confidence and zero validation errors are automatically approved.
   - Invoices with uncertainties are routed to human review, where all field corrections are immutably logged and fed into active learning.

---

## 4. Quick Start & Execution

### Running the Test Suite
```bash
python -m pytest tests/ -v
```

### Starting the FastAPI Server Locally
```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```
Swagger UI documentation will be available at: `http://localhost:8000/docs`

### Running with Docker Compose
```bash
docker compose -f docker/docker-compose.yml up --build
```
This spins up:
- FastAPI Application (`port 8000`)
- Celery Asynchronous Worker
- PostgreSQL Database (`port 5432`)
- Redis Task Broker (`port 6379`)
- MinIO Object Storage (`port 9000`, Console `port 9001`)
