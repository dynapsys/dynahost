import os
import subprocess
import ssl
import logging
from pathlib import Path
from typing import Iterable, List, Optional, Tuple
from datetime import datetime, timedelta
import ipaddress

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


logger = logging.getLogger("dynahost.certs")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _to_san_entries(names: Iterable[str]) -> List[x509.GeneralName]:
    entries: List[x509.GeneralName] = []
    for n in names:
        n = n.strip()
        if not n:
            continue
        # crude detection: IPv4 contains digits and dots only
        if all(ch.isdigit() or ch == "." for ch in n):
            try:
                entries.append(x509.IPAddress(ipaddress.ip_address(n)))
            except Exception:
                # skip invalid
                pass
        else:
            entries.append(x509.DNSName(n))
    return entries


def generate_self_signed_cert(
    output_dir: Path,
    common_name: str,
    sans: Iterable[str],
    valid_days: int = 3650,
) -> Tuple[Path, Path]:
    """Generate a self-signed certificate and return (cert_path, key_path).

    The certificate will include all provided SANs (domains and/or IPs).
    """
    ensure_dir(output_dir)
    logger.info("Generating self-signed certificate in %s (CN=%s)", output_dir, common_name)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])

    san_entries = _to_san_entries(sans)
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=valid_days))
    )
    if san_entries:
        builder = builder.add_extension(
            x509.SubjectAlternativeName(san_entries), critical=False
        )

    cert = builder.sign(private_key=key, algorithm=hashes.SHA256())

    key_path = output_dir / "key.pem"
    cert_path = output_dir / "cert.pem"

    with key_path.open("wb") as f:
        f.write(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    with cert_path.open("wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    logger.debug("Wrote key to %s and cert to %s", key_path, cert_path)
    return cert_path, key_path


def generate_mkcert_cert(output_dir: Path, names: Iterable[str]) -> Tuple[Path, Path]:
    """Generate a locally-trusted certificate using mkcert if available.

    Returns (cert_path, key_path).
    """
    ensure_dir(output_dir)
    cert_file = output_dir / "cert.pem"
    key_file = output_dir / "key.pem"

    # Check mkcert availability
    logger.info("Generating mkcert certificate in %s", output_dir)
    result = subprocess.run(["bash", "-lc", "command -v mkcert"], capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(
            "mkcert is not installed. See https://github.com/FiloSottile/mkcert"
        )

    names_list = " ".join([n for n in names if n])
    cmd = f"mkcert -install >/dev/null 2>&1 || true && mkcert -cert-file {cert_file} -key-file {key_file} {names_list}"
    proc = subprocess.run(cmd, shell=True)
    if proc.returncode != 0:
        raise RuntimeError("mkcert failed to generate certificate")

    return cert_file, key_file


def get_letsencrypt_cert(
    domain: str,
    email: str,
    staging: bool = False,
) -> Tuple[Path, Path]:
    """Obtain a Let's Encrypt certificate via certbot standalone.

    Requires root privileges and free port 80. Returns (cert_path, key_path).
    """
    args = [
        "certbot",
        "certonly",
        "--standalone",
        "--non-interactive",
        "--agree-tos",
        "-d",
        domain,
        "-m",
        email,
    ]
    if staging:
        args.append("--staging")

    logger.info("Requesting Let's Encrypt certificate for %s (standalone)", domain)
    proc = subprocess.run(args)
    if proc.returncode != 0:
        raise RuntimeError("certbot failed to obtain certificate. Ensure port 80 is free and domain resolves to this host.")

    live_dir = Path(f"/etc/letsencrypt/live/{domain}")
    cert_path = live_dir / "fullchain.pem"
    key_path = live_dir / "privkey.pem"
    if not cert_path.exists() or not key_path.exists():
        raise FileNotFoundError("Expected cert/key not found under /etc/letsencrypt/live/")

    return cert_path, key_path


def build_ssl_context(cert_file: Path, key_file: Path) -> ssl.SSLContext:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(certfile=str(cert_file), keyfile=str(key_file))
    # reasonable defaults
    ctx.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
    ctx.set_ciphers("ECDHE+AESGCM:ECDHE+CHACHA20")
    return ctx
