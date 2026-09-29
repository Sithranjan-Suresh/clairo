FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Rebuild the ChromaDB policy index at image build time — it's not
# committed to the repo (regenerable binary artifact), so the image needs
# to generate it itself. Doesn't require GROQ_API_KEY (embeddings only).
RUN python run_ingest.py

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
