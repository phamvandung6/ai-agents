FROM python:3.12.3-slim as base

WORKDIR /app

ENV UV_PROJECT_ENVIRONMENT="/usr/local/"
ENV UV_COMPILE_BYTECODE=1
ENV PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    netcat-openbsd \
    gcc \
    python3-dev \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Development stage
FROM base as development
# Install development dependencies
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && \
    uv sync --frozen

# Add watchfiles for better reload performance
RUN pip install --no-cache-dir watchfiles

COPY alembic.ini .
COPY migrations/ ./migrations/
COPY src/ ./src/

# Add entrypoint script
COPY src/scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

# Production stage
FROM base as production
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && \
    uv sync --frozen --no-install-project --no-dev

COPY alembic.ini .
COPY migrations/ ./migrations/
COPY src/ ./src/

# Add entrypoint script
COPY src/scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
