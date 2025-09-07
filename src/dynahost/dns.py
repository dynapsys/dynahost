from dataclasses import dataclass
from typing import Optional


@dataclass
class DnsAdvice:
    domain: str
    ip: str
    hosts_line: str
    dnsmasq_address: str
    dnsmasq_a_record: str
    notes: str


def suggest_dns(domain: str, ip: str) -> DnsAdvice:
    hosts_line = f"{ip} {domain}"
    # dnsmasq shortcut
    dnsmasq_address = f"address=/{domain}/{ip}"
    # explicit A record style
    dnsmasq_a_record = f"host-record={domain},{ip}"

    notes = (
        "Add the hosts line on your client machines for quick testing, or add the dnsmasq lines\n"
        "on your router (OpenWrt, EdgeOS, etc.) to create a network-wide local domain.\n"
        "After changing router DNS, restart dnsmasq on the router or reboot it."
    )

    return DnsAdvice(
        domain=domain,
        ip=ip,
        hosts_line=hosts_line,
        dnsmasq_address=dnsmasq_address,
        dnsmasq_a_record=dnsmasq_a_record,
        notes=notes,
    )
