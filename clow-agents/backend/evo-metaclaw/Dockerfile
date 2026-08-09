FROM rust:1.78-slim AS builder
WORKDIR /app
COPY . .
RUN cargo build --release -p evo-metaclaw

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y ca-certificates sqlite3 && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/target/release/evo-metaclaw /usr/local/bin/agent
ENV RUST_LOG=info
ENV DATABASE_URL=sqlite:///data/evo-metaclaw.db
EXPOSE 8080
CMD ["agent"]
