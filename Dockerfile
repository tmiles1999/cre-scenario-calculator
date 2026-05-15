# syntax=docker/dockerfile:1

FROM python:3.12-slim-bookworm AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# --- Runtime: CLI only (smaller image) ---
FROM base AS runtime

COPY pyproject.toml /app/
COPY src /app/src

RUN pip install --no-cache-dir .

ENTRYPOINT ["cre-scenarios"]
CMD ["--help"]

# --- Test: dev deps + pytest ---
FROM base AS test

COPY pyproject.toml /app/
COPY src /app/src
COPY tests /app/tests

RUN pip install --no-cache-dir ".[dev]"

CMD ["pytest", "-q"]

# --- Web GUI: Streamlit + PDF extras ---
FROM base AS gui

COPY pyproject.toml /app/
COPY src /app/src

RUN pip install --no-cache-dir ".[gui]"

ENV PYTHONPATH=/app/src

EXPOSE 8501

CMD ["streamlit", "run", "/app/src/cre_calcs/gui_app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
