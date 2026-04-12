FROM rust:slim AS builder
WORKDIR /app

COPY Cargo.toml Cargo.lock* ./
COPY cleaner/ cleaner/
COPY ann/ ann/
COPY proto/ proto/

RUN apt-get update && apt-get install -y protobuf-compiler && rm -rf /var/lib/apt/lists/*
RUN cargo build --release --package voile-ann --bin ann

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/target/release/ann /usr/local/bin/ann
EXPOSE 50052
ENTRYPOINT ["ann"]
