FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Build the ChromaDB policy index into the image — it isn't committed to the
# repo (regenerable binary artifact). Embeddings only: no GROQ_API_KEY needed.
RUN python run_ingest.py

# Run unprivileged; uploads/ is the only path the app writes to at runtime.
RUN useradd --create-home --uid 1001 clairo \
    && mkdir -p /app/app/uploads \
    && chown -R clairo:clairo /app/app/uploads /app/chroma_db
USER clairo

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"

# --proxy-headers: trust X-Forwarded-For from the load balancer so rate limits
# and audit logs see real client IPs. Override CMD to run the worker instead:
#   python -m app.jobs.worker
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
