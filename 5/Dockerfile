# Use official Go image as base
FROM golang:1.22

# Set protoc version
ENV PROTOC_VERSION=24.4

# Create a non-root user and set working directory
RUN useradd -m appuser
WORKDIR /home/appuser/app

# Install necessary tools: curl, unzip
RUN apt-get update && apt-get install -y curl unzip && rm -rf /var/lib/apt/lists/*

# Download and install protoc
RUN curl -LO https://github.com/protocolbuffers/protobuf/releases/download/v${PROTOC_VERSION}/protoc-${PROTOC_VERSION}-linux-x86_64.zip \
 && unzip protoc-${PROTOC_VERSION}-linux-x86_64.zip -d protoc3 \
 && mv protoc3/bin/protoc /usr/local/bin/ \
 && mv protoc3/include/* /usr/local/include/ \
 && rm -rf protoc-${PROTOC_VERSION}-linux-x86_64.zip protoc3

# Set up Go environment
RUN go install google.golang.org/protobuf/cmd/protoc-gen-go@latest && \
    go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest

# Switch to non-root user
USER appuser

# Default command to print versions (just to test)
CMD ["bash", "-c", "go version && protoc --version"]
