# ─────────────────────────────────────────────────────────
# Taylrd — AI Resume Tailor
# Production Dockerfile with LaTeX support for PDF generation
# ─────────────────────────────────────────────────────────

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install LaTeX (needed for PDF generation via pdflatex)
# This is a large install (~1.5 GB) but necessary for your templates
RUN apt-get update && apt-get install -y --no-install-recommends \
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-fonts-extra \
    lmodern \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Verify pdflatex is available
RUN pdflatex --version

# Expose port (Railway/Render will override with $PORT)
ENV PORT=8000
EXPOSE 8000

# Run with gunicorn for production
# --workers 2: 2 worker processes (good for free tier)
# --timeout 120: PDF generation can take time
# --access-logfile -: log to stdout for platform logging
CMD gunicorn app:app \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -