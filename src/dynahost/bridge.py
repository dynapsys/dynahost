import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .network import NetworkVisibleManager
from .proxy import TcpForwarderManager
from .compose import parse_compose_services, ComposeServices
from .terminator import TlsTerminatorManager

logger = logging.getLogger("arpx.bridge")


class ComposeBridge:
    """Bridge Docker/Podman Compose services into the LAN with dedicated IPs.

    For each service with published TCP ports, we:
      - allocate a free LAN IP alias and add it to the chosen interface,
      - start a TCP forwarder that listens on alias_ip:host_port and forwards to 127.0.0.1:host_port,
      - (optionally) add firewall rules to allow inbound traffic for those ports.

    This makes each service accessible from other devices in the network using the alias IPs.
    """

    def __init__(self, interface: str):
        self.net = NetworkVisibleManager(interface)
        self.fwds = TcpForwarderManager()
        self.terms = TlsTerminatorManager()
        self.created: List[Tuple[str, str, List[int]]] = []  # (ip, service, ports)

    def up(
        self,
        compose_file: Path,
        ip_start: int = 100,
        base_ip: Optional[str] = None,
        ssl_context=None,
        https_port: int = 443,
    ) -> List[Tuple[str, str, List[int]]]:
        """Start bridging for services described by compose_file.

        Returns a list of (alias_ip, service_name, ports)
        """
        NetworkVisibleManager.check_root()

        current_ip, network_base, cidr, _broadcast = self.net.get_network_details()
        if not current_ip:
            raise RuntimeError("Unable to obtain network details from interface")

        comp: ComposeServices = parse_compose_services(compose_file)
        services = list(comp.ports_by_service.items())  # [(name, [ServicePort,...])]
        if not services:
            logger.warning("No TCP published ports found in compose file: %s", compose_file)
            return []

        svc_count = len(services)
        if base_ip:
            base_parts = base_ip.split('.')
            alias_ips: List[str] = []
            for i in range(svc_count):
                base_parts[-1] = str(int(base_ip.split('.')[-1]) + i)
                ip = '.'.join(base_parts)
                alias_ips.append(ip)
        else:
            alias_ips = self.net.find_free_ips(network_base, cidr, svc_count, ip_start)
            if len(alias_ips) < svc_count:
                logger.warning("Found only %d free IP(s) for %d service(s)", len(alias_ips), svc_count)
                if not alias_ips:
                    return []

        for (svc_name, ports), alias_ip in zip(services, alias_ips):
            # add alias IP with visibility
            ok = self.net.add_virtual_ip_with_visibility(alias_ip, svc_name, cidr)
            if not ok:
                logger.error("Failed to add alias IP for service %s at %s", svc_name, alias_ip)
                continue

            published_ports = sorted({p.host_port for p in ports if p.protocol.lower() == 'tcp'})
            for hp in published_ports:
                # allow inbound
                self.net.configure_firewall_for_lan(alias_ip, hp)
                # forward alias_ip:hp -> 127.0.0.1:hp
                self.fwds.add(alias_ip, hp, "127.0.0.1", hp)

            # Optionally add a TLS terminator on https_port that forwards to the first published port
            if ssl_context is not None and published_ports:
                target_hp = published_ports[0]
                if https_port not in published_ports:  # avoid conflict if service already uses 443
                    try:
                        self.net.configure_firewall_for_lan(alias_ip, https_port)
                        self.terms.add(alias_ip, https_port, "127.0.0.1", target_hp, ssl_context)
                        logger.info(
                            "HTTPS terminator at https://%s:%d -> http://127.0.0.1:%d",
                            alias_ip, https_port, target_hp,
                        )
                    except Exception as e:
                        logger.warning("Failed to start TLS terminator for %s at %s:%d: %s", svc_name, alias_ip, https_port, e)

            self.created.append((alias_ip, svc_name, published_ports))
            logger.info("Bridged service %s at %s with ports %s", svc_name, alias_ip, ",".join(map(str, published_ports)))

        return self.created

    def cleanup(self):
        self.fwds.stop_all()
        self.terms.stop_all()
        # remove IPs
        for alias_ip, _svc, _ports in self.created:
            try:
                self.net.remove_virtual_ip(alias_ip)
            except Exception:
                pass
        self.created.clear()
