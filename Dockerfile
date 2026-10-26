FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    JABFY_BUS_HOST=0.0.0.0 \
    JABFY_BUS_PORT=8080

WORKDIR /app

RUN groupadd --gid 10001 jabfy \
    && useradd --create-home --uid 10001 --gid jabfy jabfy

COPY pyproject.toml README.md ./
COPY jabfy_bus ./jabfy_bus

RUN pip install --no-cache-dir ".[api]"

USER jabfy

EXPOSE 8080

CMD ["jabfy-bus", "serve"]

