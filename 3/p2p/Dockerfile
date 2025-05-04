FROM python:3.12-slim

WORKDIR /app

# Copy and install Python dependencies first (for layer caching)
COPY pyproject.toml .
COPY README.md .
RUN pip install --no-cache-dir .

# Copy the rest of the application
COPY . .