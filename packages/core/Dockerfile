FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Copy minimal package structure for dependency installation
COPY pyproject.toml ./
COPY core/__init__.py ./core/__init__.py
RUN pip install --no-cache-dir -e .

# Copy full source
COPY . .

EXPOSE 8000

CMD ["uvicorn", "core.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
