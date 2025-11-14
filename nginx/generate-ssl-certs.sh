#!/bin/bash
# Generate self-signed SSL certificates for development
# For production, use Let's Encrypt with certbot

set -e

CERT_DIR="./ssl"
DAYS_VALID=365

echo "🔐 Generating self-signed SSL certificates for development..."

# Create directory if it doesn't exist
mkdir -p "$CERT_DIR"

# Generate private key and certificate
openssl req -x509 -nodes -days $DAYS_VALID -newkey rsa:2048 \
    -keyout "$CERT_DIR/key.pem" \
    -out "$CERT_DIR/cert.pem" \
    -subj "/C=CA/ST=Quebec/L=Montreal/O=AI CFO Suite/CN=aicfo.local"

echo "✅ SSL certificates generated successfully!"
echo "📁 Location: $CERT_DIR"
echo "🔑 Private key: $CERT_DIR/key.pem"
echo "📜 Certificate: $CERT_DIR/cert.pem"
echo ""
echo "⚠️  These are SELF-SIGNED certificates for DEVELOPMENT only."
echo "⚠️  For production, use Let's Encrypt with certbot."
echo ""
echo "To trust these certificates locally:"
echo "  - macOS: Add cert.pem to Keychain Access"
echo "  - Linux: Copy to /usr/local/share/ca-certificates/ and run update-ca-certificates"
echo "  - Windows: Import cert.pem to Trusted Root Certification Authorities"
