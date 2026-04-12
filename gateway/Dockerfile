FROM golang:1.22-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
ARG CMD=api
RUN go build -o /app/server ./cmd/${CMD}

FROM alpine:3.19
COPY --from=builder /app/server /app/server
ENTRYPOINT ["/app/server"]
