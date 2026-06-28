# Build stage
FROM golang:1.22-alpine AS builder

ARG SERVICE
ENV SERVICE=${SERVICE}

WORKDIR /build

# Copy go.mod and go.sum from root
COPY go.mod go.sum ./
RUN go mod download

# Copy the entire source and build the specified service
COPY go_workers/ ./go_workers/
COPY config/ ./config/

# Build the service binary
WORKDIR /build/go_workers/${SERVICE}
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o /build/service .

# Final small image
FROM alpine:latest

WORKDIR /app

COPY --from=builder /build/service /app/service
COPY --from=builder /build/config /app/config

EXPOSE ${EXTRACTOR_GRPC_PORT:-50051} ${BACKTESTER_GRPC_PORT:-50052}

ENTRYPOINT ["/app/service"]