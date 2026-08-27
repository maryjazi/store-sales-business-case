# Store Sales Analytics & Forecasting — containerized ETL + test environment
FROM python:3.10-slim

WORKDIR /app

# Install dependencies first so this layer is cached across code changes
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Only the code needed to run the pipeline/tests — data is mounted at runtime
COPY etl/ etl/
COPY sql/ sql/
COPY tests/ tests/

# Raw and processed data are NOT baked into the image:
#  - Kaggle's competition rules restrict redistributing the raw CSVs
#  - keeps the image small and reproducible
# Mount your local ./data folder to run the real pipeline or the full test suite, e.g.:
#   docker run --rm -v "$(pwd)/data:/app/data" sales-forecast
#   docker run --rm -v "$(pwd)/data:/app/data" sales-forecast python etl/phase3_kpi_reporting.py
VOLUME ["/app/data"]

# Default: run the test suite (feature tests always run; data-quality tests
# skip cleanly if data/ isn't mounted, and pass against the real 3M-row
# dataset when it is)
CMD ["pytest", "tests/", "-v", "--tb=short"]
