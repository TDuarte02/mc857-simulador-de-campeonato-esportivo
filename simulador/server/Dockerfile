# Build context: simulador/ (the server depends on ../engine), see docker-compose.yml.
FROM python:3.14-slim

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
USER app

EXPOSE 5000
CMD ["flask", "--app", "main", "run", "--host", "0.0.0.0", "--port", "5000"]
