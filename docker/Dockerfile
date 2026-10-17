FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install system dependencies for OpenCV, lxml, and PDF rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libxml2-dev \
    libxslt1-dev \
    libxmlsec1-dev \
    libxmlsec1-openssl \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
