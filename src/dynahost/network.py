import os
import sys
import subprocess
import ipaddress
import time
from typing import List, Optional, Tuple


class NetworkVisibleManager:
    """Manage virtual IPs that are visible across the LAN.

    Mirrors functionality from `network-visible-script.py` but packaged for reuse.
    """

    def __init__(self, interface: str = "eth0"):
        self.interface = interface
        self.virtual_ips: List[Tuple[str, str]] = []  # (ip, label)
        self.arp_announced: List[str] = []

    # -----------------
    # Privileges
    # -----------------
    @staticmethod
    def check_root() -> None:
        if os.geteuid() != 0:
            print("❌ This command requires root privileges.")
            print("Run with: sudo ...")
            sys.exit(1)

    # -----------------
    # Introspection
    # -----------------
    @staticmethod
    def auto_detect_interface() -> str:
        try:
            cmd = "ip route | grep default | awk '{print $5}' | head -1"
            iface = subprocess.check_output(cmd, shell=True).decode().strip()
            return iface or "eth0"
        except Exception:
            return "eth0"

    def get_network_details(self) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """Return (ip, network_base, cidr, broadcast) for the interface."""
        try:
            cmd = f"ip addr show {self.interface}"
            result = subprocess.check_output(cmd, shell=True).decode()

            import re

            ip_pattern = r"inet (\d+\.\d+\.\d+\.\d+)/(\d+)"
            match = re.search(ip_pattern, result)

            if match:
                ip = match.group(1)
                cidr = match.group(2)
                network = ipaddress.IPv4Network(f"{ip}/{cidr}", strict=False)
                return str(ip), str(network.network_address), str(cidr), str(network.broadcast_address)
        except Exception:
            pass
        return None, None, None, None

    # -----------------
    # IP selection
    # -----------------
    def find_free_ips(self, base_network: str, cidr: str, num_ips: int = 3, start_ip: int = 100) -> List[str]:
        network = ipaddress.IPv4Network(f"{base_network}/{cidr}", strict=False)
        free_ips: List[str] = []
        checked = 0

        print("\n🔍 Searching for free IP addresses in the network...")
        for ip in network.hosts():
            if int(str(ip).split(".")[-1]) < start_ip:
                continue
            if checked >= 50:
                break

            ip_str = str(ip)
            # ICMP echo
            cmd = f"ping -c 1 -W 1 {ip_str}"
            result = subprocess.run(cmd, shell=True, capture_output=True)

            if result.returncode != 0:
                # ARP check
                arp_cmd = f"arping -c 1 -w 1 {ip_str} 2>/dev/null"
                arp_result = subprocess.run(arp_cmd, shell=True, capture_output=True)
                if arp_result.returncode != 0:
                    free_ips.append(ip_str)
                    print(f"   ✅ Free: {ip_str}")
                    if len(free_ips) >= num_ips:
                        break
            checked += 1

        if len(free_ips) < num_ips:
            print(f"⚠️ Found only {len(free_ips)} free IPs")
        return free_ips

    # -----------------
    # IP configure
    # -----------------
    def add_virtual_ip_with_visibility(self, ip_address: str, label_suffix, cidr: str = "24") -> bool:
        try:
            label = f"{self.interface}:{label_suffix}"
            # add alias
            cmd = f"ip addr add {ip_address}/{cidr} dev {self.interface} label {label}"
            subprocess.run(cmd, shell=True, check=True)

            # enable forwarding
            subprocess.run("echo 1 > /proc/sys/net/ipv4/ip_forward", shell=True)
            # enable proxy ARP
            subprocess.run(
                f"echo 1 > /proc/sys/net/ipv4/conf/{self.interface}/proxy_arp", shell=True
            )

            # Gratuitous ARP
            self.announce_arp(ip_address)
            # Add to ARP cache
            self.update_arp_cache(ip_address)

            print(f"✅ Added and announced IP: {ip_address} as {label}")
            self.virtual_ips.append((ip_address, label))
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to add IP {ip_address}: {e}")
            return False

    def announce_arp(self, ip_address: str) -> None:
        try:
            # via arping
            cmd = f"arping -U -I {self.interface} -c 3 {ip_address} 2>/dev/null"
            subprocess.run(cmd, shell=True)
            # via ip neigh
            mac = self.get_interface_mac()
            if mac:
                cmd2 = f"ip neigh add {ip_address} lladdr {mac} dev {self.interface} nud permanent 2>/dev/null"
                subprocess.run(cmd2, shell=True)
            self.arp_announced.append(ip_address)
            print(f"   📢 ARP announced for {ip_address}")
        except Exception as e:
            print(f"   ⚠️ Failed to announce ARP for {ip_address}: {e}")

    def get_interface_mac(self) -> Optional[str]:
        try:
            cmd = f"ip link show {self.interface} | grep ether | awk '{{print $2}}'"
            mac = subprocess.check_output(cmd, shell=True).decode().strip()
            return mac
        except Exception:
            return None

    def update_arp_cache(self, ip_address: str) -> None:
        try:
            mac = self.get_interface_mac()
            if mac:
                cmd = f"arp -s {ip_address} {mac} 2>/dev/null"
                subprocess.run(cmd, shell=True)
        except Exception:
            pass

    def configure_firewall_for_lan(self, ip_address: str, port: int) -> None:
        try:
            result = subprocess.run("which iptables", shell=True, capture_output=True)
            if result.returncode == 0:
                cmd = f"iptables -A INPUT -d {ip_address} -p tcp --dport {port} -j ACCEPT"
                subprocess.run(cmd, shell=True)
                cmd2 = f"iptables -A OUTPUT -s {ip_address} -p tcp --sport {port} -j ACCEPT"
                subprocess.run(cmd2, shell=True)
                print(f"   🔥 Firewall configured for {ip_address}:{port}")
        except Exception:
            pass

    def remove_virtual_ip(self, ip_address: str, cidr: str = "24") -> None:
        try:
            cmd = f"ip addr del {ip_address}/{cidr} dev {self.interface}"
            subprocess.run(cmd, shell=True, check=True)
            cmd2 = f"arp -d {ip_address} 2>/dev/null"
            subprocess.run(cmd2, shell=True)
            print(f"✅ Removed IP: {ip_address}")
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Failed to remove IP {ip_address}: {e}")

    def cleanup(self) -> None:
        print("\n🧹 Cleaning up...")
        for ip, _label in self.virtual_ips:
            self.remove_virtual_ip(ip)
