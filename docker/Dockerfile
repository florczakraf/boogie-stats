FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app
COPY pyproject.toml uv.lock /app/
RUN uv sync --locked --no-install-project --no-dev

COPY . /app
RUN uv sync --locked --no-dev

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

ENTRYPOINT ["/app/docker/entrypoint.sh"]
