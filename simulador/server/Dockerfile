# Build context: simulador/ (the server depends on ../engine), see docker-compose.yml.
#
# Targets:
#   local  docker compose (default there): Flask's built-in server.
#   aws    the image deployed to ECS: gunicorn, Amazon's CA bundle for DocumentDB's
#          TLS, and the players CSV so the seed can run inside the VPC. Built by
#          infra/aws/deploy.sh with the CSV's folder as the named context `data`:
#            docker build --target aws --build-context data=../pipeline-dados/artefatos ...
FROM python:3.14-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv

RUN pip install --no-cache-dir uv==0.11.18

WORKDIR /app/server

# The engine is an editable path dependency (../engine), installed from source by
# `uv sync`, so it goes in first. Then the dependencies, so code changes don't
# reinstall them.
COPY engine/pyproject.toml /app/engine/pyproject.toml
COPY engine/copa_engine /app/engine/copa_engine
COPY server/pyproject.toml server/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY server/main.py ./
COPY server/api ./api

ENV PATH="/opt/venv/bin:$PATH" \
    REPOSITORY=mongo \
    MONGO_URI=mongodb://mongo:27017 \
    MONGO_DB=copa \
    SIMULATOR=engine

RUN useradd --system --no-create-home app
EXPOSE 5000


FROM base AS aws

RUN uv sync --frozen --no-dev --group deploy --no-install-project
# Amazon's CA bundle: DocumentDB only accepts TLS connections.
ADD --chmod=644 https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem /app/global-bundle.pem
COPY --from=data jogadores_copa_america_2024_filtrado.csv /app/data/

ENV MONGO_TLS_CA_FILE=/app/global-bundle.pem \
    MONGO_RETRY_WRITES=false \
    MONGO_REPLICA_SET=rs0

USER app
# create_app() runs once per worker; state lives in DocumentDB, so workers share nothing.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", \
     "--timeout", "30", "--access-logfile", "-", "--no-control-socket", "main:app"]


FROM base AS local

USER app
CMD ["flask", "--app", "main", "run", "--host", "0.0.0.0", "--port", "5000"]
