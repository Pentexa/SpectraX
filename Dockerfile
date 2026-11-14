FROM python:3.11-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLANET_X_MANIFEST=/app/data/manifests/spherex-dr1.json \
    PLANET_X_DATA_DIR=/data \
    PLANET_X_IMPORT_DIR=/imports

WORKDIR /app
COPY pyproject.toml ./
COPY apps/ apps/
COPY pipeline/ pipeline/
RUN python -m pip install --no-cache-dir . \
    && mkdir /data /imports \
    && chown 10001:10001 /data /imports
COPY data/manifests/ data/manifests/

USER 10001:10001
EXPOSE 8765
CMD ["python", "-m", "uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8765"]

FROM runtime AS test
USER root
RUN python -m pip install --no-cache-dir '.[test]'
USER 10001:10001

FROM runtime AS production
