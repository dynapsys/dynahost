#!/usr/bin/env python3
"""API example for ARPx.

Creates a single alias IP and starts an HTTPS server on it using a self-signed
certificate, then waits until interrupted.

Run as root:

    sudo python3 examples/api/simple_api.py

"""
import logging
import signal
import sys
import time
from pathlib import Path

from arpx.network import NetworkVisibleManager
from arpx.server import LANWebServerManager
from arpx import certs as cert_utils


def main() -> int:
    logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(name)s: %(message)s')

    NetworkVisibleManager.check_root()
    iface = NetworkVisibleManager.auto_detect_interface()
    print(f"Using interface: {iface}")

    net = NetworkVisibleManager(iface)
    web = LANWebServerManager()

    ip, base, cidr, _ = net.get_network_details()
    if not ip:
        print("Network details not available")
        return 1

    # Find one free IP
    alias_ips = net.find_free_ips(base, cidr, num_ips=1, start_ip=100)
    if not alias_ips:
        print("No free IPs found")
        return 1
    alias_ip = alias_ips[0]

    # Self-signed cert
    out_dir = Path.cwd() / ".arpx" / "certs" / "api-example"
    cert_file, key_file = cert_utils.generate_self_signed_cert(out_dir, alias_ip, [alias_ip])
    ctx = cert_utils.build_ssl_context(cert_file, key_file)

    # signal handling
    def stop(_sig, _frm):
        print("\nStopping...")
        net.cleanup()
        web.stop_all()
        sys.exit(0)

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    # Add alias IP and start server
    if net.add_virtual_ip_with_visibility(alias_ip, "api", cidr):
        port = 9443
        net.configure_firewall_for_lan(alias_ip, port)
        web.start_lan_server(alias_ip, port, "API Example", ctx)
        print(f"Now open: https://{alias_ip}:{port}")

        try:
            while True:
                time.sleep(30)
        finally:
            net.cleanup()
            web.stop_all()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
