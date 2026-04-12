FROM rust:1.78-slim AS builder
WORKDIR /app

COPY Cargo.toml Cargo.lock* build.rs ./
COPY src/ src/
COPY ../proto/ /proto/

RUN apt-get update && apt-get install -y protobuf-compiler && rm -rf /var/lib/apt/lists/*
RUN cargo build --release --bin cleaner

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/target/release/cleaner /usr/local/bin/cleaner
EXPOSE 50051
ENTRYPOINT ["cleaner"]
