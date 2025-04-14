FROM python:3.12-slim

# Install curl
RUN apt-get update && apt-get install -y curl postgresql-client

# Install uv python package
RUN curl -Ls https://astral.sh/uv/install.sh | sh
# Export to the PATH
ENV PATH="/root/.local/bin:${PATH}"
RUN uv --version

COPY . .

# Install the required packages
RUN uv pip install --system . 