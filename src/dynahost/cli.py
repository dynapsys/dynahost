import argparse
import logging
import os
import signal
import sys
import time
from pathlib import Path
from typing import List, Optional

from .network import NetworkVisibleManager
from .server import LANWebServerManager
from . import certs as cert_utils
from .dns import suggest_dns
from .bridge import ComposeBridge


def _setup_logging(log_level: str) -> None:
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="[%(levelname)s] %(name)s: %(message)s",
    )


def print_summary(created_ips: List[str], base_port: int, scheme: str = "http") -> None:
    print("\n" + "=" * 60)
    print("✅ SERVERS RUNNING AND VISIBLE IN THE LAN")
    print("=" * 60)
    print("\n📋 ENDPOINTS (reachable from any device in the LAN):\n")
    for i, ip in enumerate(created_ips):
        port = base_port + i
        print(f"   {i + 1}. {scheme}://{ip}:{port}")
        print(f"      └─ Content: Hello {i + 1}")

    print("\n" + "=" * 60)
    print("🧪 HOW TO TEST:")
    print("=" * 60)
    print("\n1. FROM THIS MACHINE:")
    proto = "https" if scheme == "https" else "http"
    print(f"   curl -k {proto}://{created_ips[0]}:{base_port}")
    print(f"   wget --no-check-certificate {proto}://{created_ips[0]}:{base_port}")
    print(f"   Browser: {proto}://{created_ips[0]}:{base_port}")

    print("\n2. FROM ANOTHER MACHINE IN THE LAN:")
    print("   Open a browser and enter any of the addresses above")

    print("\n3. FROM A PHONE/TABLET:")
    print("   Connect to the same WiFi network")
    print(f"   Navigate: {proto}://{created_ips[0]}:{base_port}")

    print("\n" + "=" * 60)
    print("⚠️  Press Ctrl+C to stop all servers")
    print("=" * 60 + "\n")


def cmd_up(args: argparse.Namespace) -> int:
    _setup_logging(args.log_level)
    # Root required
    NetworkVisibleManager.check_root()

    # Interface
    interface = args.interface or NetworkVisibleManager.auto_detect_interface()
    print(f"🔍 Interface: {interface}")

    net_manager = NetworkVisibleManager(interface)
    web_manager = LANWebServerManager()

    # Network details
    current_ip, network_base, cidr, broadcast = net_manager.get_network_details()
    if not current_ip:
        print("❌ Unable to obtain network details")
        return 1

    # Free IPs or base IP
    if args.base_ip:
        base_parts = args.base_ip.split('.')
        created_ips: List[str] = []
        for i in range(args.num_ips):
            base_parts[-1] = str(int(args.base_ip.split('.')[-1]) + i)
            ip = '.'.join(base_parts)
            created_ips.append(ip)
    else:
        print(f"\n🔍 Searching for {args.num_ips} free IP addresses...")
        created_ips = net_manager.find_free_ips(network_base, cidr, args.num_ips, args.ip_start)
        if not created_ips:
            print("❌ No free IP addresses found")
            return 1

    # TLS setup
    scheme = "http"
    ssl_ctx = None
    cert_dir = Path(args.cert_dir or (Path.cwd() / ".dynahost" / "certs"))
    if args.https and args.https != "none":
        scheme = "https"
        if args.https == "self-signed":
            names = []
            if args.domains:
                names.extend([d.strip() for d in args.domains.split(",") if d.strip()])
            names.extend(created_ips)
            common_name = names[0] if names else created_ips[0]
            out_dir = cert_dir / "self-signed"
            cert_file, key_file = cert_utils.generate_self_signed_cert(out_dir, common_name, names)
            ssl_ctx = cert_utils.build_ssl_context(cert_file, key_file)
        elif args.https == "mkcert":
            names = []
            if args.domains:
                names.extend([d.strip() for d in args.domains.split(",") if d.strip()])
            names.extend(created_ips)
            out_dir = cert_dir / "mkcert"
            try:
                cert_file, key_file = cert_utils.generate_mkcert_cert(out_dir, names)
            except RuntimeError as e:
                print(f"❌ {e}")
                return 1
            ssl_ctx = cert_utils.build_ssl_context(cert_file, key_file)
        elif args.https == "letsencrypt":
            if not args.domain or not args.email:
                print("❌ For Let's Encrypt please provide --domain and --email")
                return 1
            try:
                cert_file, key_file = cert_utils.get_letsencrypt_cert(args.domain, args.email, args.staging)
            except Exception as e:
                print(f"❌ Let's Encrypt error: {e}")
                return 1
            ssl_ctx = cert_utils.build_ssl_context(cert_file, key_file)
        elif args.https == "custom":
            if not args.cert_file or not args.key_file:
                print("❌ For custom certs provide --cert-file and --key-file")
                return 1
            cert_file = Path(args.cert_file)
            key_file = Path(args.key_file)
            ssl_ctx = cert_utils.build_ssl_context(cert_file, key_file)
        else:
            print(f"⚠️ Unknown https mode: {args.https}")
            return 1

    # Signal handling
    def signal_handler(sig, frame):
        print("\n\n⚠️ Stopping...")
        net_manager.cleanup()
        web_manager.stop_all()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create IPs and servers
    print(f"\n🚀 Configuring {len(created_ips)} virtual IP(s)...\n")
    for i, ip in enumerate(created_ips):
        print(f"📦 Config {i + 1}/{len(created_ips)}:")
        if net_manager.add_virtual_ip_with_visibility(ip, i + 1, cidr):
            port = args.base_port + i
            net_manager.configure_firewall_for_lan(ip, port)
            content = f"Hello {i + 1}"
            server = web_manager.start_lan_server(ip, port, content, ssl_ctx)
            if server:
                time.sleep(0.5)
                web_manager.test_connectivity(ip, port, scheme)
        print()

    print_summary(created_ips, args.base_port, scheme)

    # Post-start ARP reannounce
    time.sleep(2)
    print("\n📢 Re-announcing IPs on the network...")
    for ip in created_ips:
        net_manager.announce_arp(ip)

    print("\n✅ Ready! Servers visible across the LAN.")
    print("   Open a browser on ANY device in the network and navigate to the URLs above.\n")

    # Main loop: refresh ARP periodically
    try:
        while True:
            time.sleep(30)
            for ip in created_ips:
                net_manager.update_arp_cache(ip)
    finally:
        net_manager.cleanup()
        web_manager.stop_all()


def cmd_cert(args: argparse.Namespace) -> int:
    _setup_logging(args.log_level)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    if args.mode == "self-signed":
        names = [n.strip() for n in (args.names or "").split(",") if n.strip()]
        cn = args.common_name or (names[0] if names else "dynahost.local")
        cert, key = cert_utils.generate_self_signed_cert(out, cn, names or ["localhost"]) 
        print(f"✅ Generated self-signed cert:\n  cert: {cert}\n  key:  {key}")
    elif args.mode == "mkcert":
        names = [n.strip() for n in (args.names or "").split(",") if n.strip()]
        cert, key = cert_utils.generate_mkcert_cert(out, names or ["localhost"])
        print(f"✅ Generated mkcert cert:\n  cert: {cert}\n  key:  {key}")
    elif args.mode == "letsencrypt":
        if not args.domain or not args.email:
            print("❌ Provide --domain and --email for Let's Encrypt")
            return 1
        cert, key = cert_utils.get_letsencrypt_cert(args.domain, args.email, args.staging)
        print(f"✅ Obtained Let's Encrypt cert:\n  cert: {cert}\n  key:  {key}")
    else:
        print("❌ Unknown cert mode")
        return 1
    return 0


def cmd_dns(args: argparse.Namespace) -> int:
    _setup_logging(args.log_level)
    advice = suggest_dns(args.domain, args.ip)
    print("\nSuggestions for local domain configuration:\n")
    print("Hosts entry:")
    print(f"  {advice.hosts_line}\n")
    print("dnsmasq options (router):")
    print(f"  {advice.dnsmasq_address}")
    print(f"  {advice.dnsmasq_a_record}\n")
    print(advice.notes)
    if args.output:
        out = Path(args.output)
        out.write_text(f"{advice.dnsmasq_address}\n{advice.dnsmasq_a_record}\n", encoding="utf-8")
        print(f"\n💾 Written dnsmasq snippet to: {out}")
    return 0


def cmd_compose(args: argparse.Namespace) -> int:
    _setup_logging(args.log_level)
    # root required; ComposeBridge will also check
    NetworkVisibleManager.check_root()

    interface = args.interface or NetworkVisibleManager.auto_detect_interface()
    print(f"🔍 Interface: {interface}")

    cb = ComposeBridge(interface)

    # Optional HTTPS terminator context
    ssl_ctx = None
    cert_dir = Path(args.cert_dir or (Path.cwd() / ".dynahost" / "certs" / "compose"))
    if args.https and args.https != "none":
        if args.https == "self-signed":
            names = []
            if args.domains:
                names.extend([d.strip() for d in args.domains.split(",") if d.strip()])
            common_name = names[0] if names else "dynahost.local"
            cert_file, key_file = cert_utils.generate_self_signed_cert(cert_dir, common_name, names)
            ssl_ctx = cert_utils.build_ssl_context(cert_file, key_file)
        elif args.https == "mkcert":
            names = []
            if args.domains:
                names.extend([d.strip() for d in args.domains.split(",") if d.strip()])
            try:
                cert_file, key_file = cert_utils.generate_mkcert_cert(cert_dir, names or ["localhost"])
            except RuntimeError as e:
                print(f"❌ {e}")
                return 1
            ssl_ctx = cert_utils.build_ssl_context(cert_file, key_file)
        elif args.https == "letsencrypt":
            if not args.domain or not args.email:
                print("❌ For Let's Encrypt please provide --domain and --email")
                return 1
            try:
                cert_file, key_file = cert_utils.get_letsencrypt_cert(args.domain, args.email, args.staging)
            except Exception as e:
                print(f"❌ Let's Encrypt error: {e}")
                return 1
            ssl_ctx = cert_utils.build_ssl_context(cert_file, key_file)
        elif args.https == "custom":
            if not args.cert_file or not args.key_file:
                print("❌ For custom certs provide --cert-file and --key-file")
                return 1
            cert_file = Path(args.cert_file)
            key_file = Path(args.key_file)
            ssl_ctx = cert_utils.build_ssl_context(cert_file, key_file)

    # signal handling
    def signal_handler(sig, frame):
        print("\n\n⚠️ Stopping compose bridge...")
        cb.cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    created = cb.up(
        Path(args.file), ip_start=args.ip_start, base_ip=args.base_ip, ssl_context=ssl_ctx, https_port=args.https_port
    )
    if not created:
        print("⚠️ Nothing bridged (no services with published TCP ports?)")
        return 1

    print("\n" + "=" * 60)
    print("✅ COMPOSE SERVICES BRIDGED TO LAN")
    print("=" * 60)
    for alias_ip, svc, ports in created:
        for port in ports:
            print(f"  - {svc}: http://{alias_ip}:{port}  (or https if your service serves TLS)")
    print("\nPress Ctrl+C to stop and remove alias IPs.")

    try:
        while True:
            time.sleep(30)
    finally:
        cb.cleanup()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="dynahost", description="DynaHost - multi-IP LAN HTTP/HTTPS servers with ARP visibility")
    p.add_argument("--log-level", default="INFO", help="Logging level (DEBUG, INFO, WARNING, ERROR)")
    sub = p.add_subparsers(dest="cmd", required=True)

    # up
    up = sub.add_parser("up", help="Create virtual IPs and start HTTP/HTTPS servers visible in the LAN")
    up.add_argument("-i", "--interface", help="Network interface (auto-detected if omitted)")
    up.add_argument("-n", "--num-ips", type=int, default=3, help="Number of virtual IPs")
    up.add_argument("-b", "--base-ip", help="Base IP to start from (otherwise auto-find free IPs)")
    up.add_argument("-p", "--base-port", type=int, default=8000, help="Base HTTP port")
    up.add_argument("--ip-start", type=int, default=100, help="Start searching from this last octet value")

    up.add_argument("--https", choices=["none", "self-signed", "mkcert", "letsencrypt", "custom"], default="none", help="Enable HTTPS with chosen method")
    up.add_argument("--domains", help="Comma-separated domain list for cert SANs (self-signed/mkcert)")
    up.add_argument("--domain", help="Single domain for Let's Encrypt")
    up.add_argument("--email", help="Email for Let's Encrypt")
    up.add_argument("--staging", action="store_true", help="Use Let's Encrypt staging environment")
    up.add_argument("--cert-file", help="Path to custom certificate (PEM)")
    up.add_argument("--key-file", help="Path to custom private key (PEM)")
    up.add_argument("--cert-dir", help="Directory to place or read certificates")
    up.set_defaults(func=cmd_up)

    # cert
    cert = sub.add_parser("cert", help="Certificate utilities")
    cert.add_argument("mode", choices=["self-signed", "mkcert", "letsencrypt"], help="Certificate mode")
    cert.add_argument("-o", "--output", default=str(Path.cwd() / ".dynahost" / "certs"), help="Output directory")
    cert.add_argument("--common-name", help="Common Name for self-signed")
    cert.add_argument("--names", help="Comma-separated SANs: domain(s) and/or IP(s)")
    cert.add_argument("--domain", help="Domain for Let's Encrypt")
    cert.add_argument("--email", help="Email for Let's Encrypt")
    cert.add_argument("--staging", action="store_true", help="Use Let's Encrypt staging")
    cert.set_defaults(func=cmd_cert)

    # dns
    dns = sub.add_parser("dns", help="Suggest local domain config for DHCP router (dnsmasq)")
    dns.add_argument("--domain", required=True, help="Desired local domain, e.g., myapp.lan")
    dns.add_argument("--ip", required=True, help="Target IP address")
    dns.add_argument("-o", "--output", help="Write dnsmasq snippet to file")
    dns.set_defaults(func=cmd_dns)

    # compose bridge
    comp = sub.add_parser("compose", help="Bridge Docker/Podman Compose services into the LAN with alias IPs")
    comp.add_argument("-f", "--file", default="docker-compose.yml", help="Path to compose file")
    comp.add_argument("-i", "--interface", help="Network interface (auto-detected if omitted)")
    comp.add_argument("--ip-start", type=int, default=100, help="Start searching from this last octet value")
    comp.add_argument("-b", "--base-ip", help="Base IP to start from (otherwise auto-find free IPs)")
    comp.add_argument("--https", choices=["none", "self-signed", "mkcert", "letsencrypt", "custom"], default="none", help="Enable HTTPS terminator for bridged services")
    comp.add_argument("--https-port", type=int, default=443, help="Port for HTTPS terminator on alias IPs (default: 443)")
    comp.add_argument("--domains", help="Comma-separated domain list for cert SANs (self-signed/mkcert)")
    comp.add_argument("--domain", help="Single domain for Let's Encrypt")
    comp.add_argument("--email", help="Email for Let's Encrypt")
    comp.add_argument("--staging", action="store_true", help="Use Let's Encrypt staging environment")
    comp.add_argument("--cert-file", help="Path to custom certificate (PEM)")
    comp.add_argument("--key-file", help="Path to custom private key (PEM)")
    comp.add_argument("--cert-dir", help="Directory to place or read certificates for compose HTTPS")
    comp.set_defaults(func=cmd_compose)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
