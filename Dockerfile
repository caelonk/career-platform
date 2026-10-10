FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.20 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY app ./app
COPY scripts ./scripts
COPY migrations ./migrations
COPY alembic.ini ./
RUN uv sync --locked --no-dev

EXPOSE 8000

# Railway sets PORT and terminates TLS in front of the container; trusting its
# X-Forwarded-Proto keeps url_for() links https:// so CSS and fonts aren't blocked.
CMD ["sh", "-c", "exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port ${PORT:-8000} --workers 2 --proxy-headers --forwarded-allow-ips '*'"]
