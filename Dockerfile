FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLANET_X_MANIFEST=/app/data/manifests/spherex-dr1.json \
    PLANET_X_DATA_DIR=/data

WORKDIR /app
COPY pyproject.toml ./
COPY apps/ apps/
COPY pipeline/ pipeline/
RUN python -m pip install --no-cache-dir . \
    && mkdir /data \
    && chown 10001:10001 /data
COPY data/manifests/ data/manifests/

USER 10001:10001
EXPOSE 8765
CMD ["python", "-m", "uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8765"]
