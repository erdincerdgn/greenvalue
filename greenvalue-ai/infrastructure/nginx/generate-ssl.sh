#!/bin/bash
# ============================================================
# GreenValue AI - Self-Signed SSL Certificate Generator
# For development only. Use Let's Encrypt for production.
# ============================================================

SSL_DIR="$(dirname "$0")/ssl"
mkdir -p "$SSL_DIR"

echo "Generating self-signed SSL certificate for GreenValue AI..."

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout "$SSL_DIR/server.key" \
  -out "$SSL_DIR/server.crt" \
  -subj "/C=TR/ST=Istanbul/L=Istanbul/O=GreenValue AI/OU=Development/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,DNS:*.greenvalue.local,IP:127.0.0.1"

echo "SSL certificates generated:"
echo "  Certificate: $SSL_DIR/server.crt"
echo "  Private Key: $SSL_DIR/server.key"
echo ""
echo "For production, replace these with Let's Encrypt certificates."
