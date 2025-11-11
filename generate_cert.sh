#!/bin/bash
# Generate self-signed SSL certificate

openssl req -x509 -newkey rsa:4096 -nodes \
    -out ssl/cert.pem \
    -keyout ssl/key.pem \
    -days 365 \
    -subj "/C=CZ/ST=State/L=City/O=GymTurniket/CN=192.168.0.108" \
    -addext "subjectAltName=IP:192.168.0.108,DNS:localhost"

echo "SSL certificates generated in ssl/ directory"

