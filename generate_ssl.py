"""
generate_ssl.py — Tự tạo SSL certificate self-signed cho HTTPS local.
Chạy 1 lần: python generate_ssl.py
Tạo ra: ssl/cert.pem và ssl/key.pem
"""

import os
import datetime
from pathlib import Path

SSL_DIR = Path(__file__).parent / "ssl"
CERT_FILE = SSL_DIR / "cert.pem"
KEY_FILE = SSL_DIR / "key.pem"


def generate_ssl():
    SSL_DIR.mkdir(exist_ok=True)

    if CERT_FILE.exists() and KEY_FILE.exists():
        print("[SSL] Certificate đã tồn tại — bỏ qua")
        return

    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        import ipaddress

        # Tạo private key
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

        # Lấy IP local
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            local_ip = "127.0.0.1"

        # Tạo certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, "Robot Bi"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Robot Bi Local"),
        ])

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.utcnow())
            .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=3650))
            .add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName("localhost"),
                    x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                    x509.IPAddress(ipaddress.IPv4Address(local_ip)),
                ]),
                critical=False,
            )
            .sign(key, hashes.SHA256())
        )

        # Lưu key
        KEY_FILE.write_bytes(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

        # Lưu cert
        CERT_FILE.write_bytes(cert.public_bytes(serialization.Encoding.PEM))

        print(f"[SSL] Certificate tạo thành công!")
        print(f"[SSL] IP local: {local_ip}")
        print(f"[SSL] Cert: {CERT_FILE}")
        print(f"[SSL] Key:  {KEY_FILE}")
        print(f"[SSL] Hạn: 10 năm")

    except ImportError:
        print("[SSL] Thiếu thư viện cryptography — chạy: pip install cryptography")
        raise


if __name__ == "__main__":
    generate_ssl()
