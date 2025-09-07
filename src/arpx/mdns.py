import logging
import socket
from typing import List, Tuple

try:
    from zeroconf import IPVersion, ServiceInfo, Zeroconf
except Exception:  # pragma: no cover - optional dependency
    Zeroconf = None  # type: ignore

logger = logging.getLogger("arpx.mdns")


class MDNSPublisher:
    def __init__(self):
        if Zeroconf is None:
            raise RuntimeError("zeroconf is not installed. Install with arpx[mdns]")
        self.zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
        self.services: List[ServiceInfo] = []

    def publish(self, name: str, ip: str, port: int, https: bool = False):
        service_type = "_https._tcp.local." if https else "_http._tcp.local."
        instance_name = f"{name}.{service_type}"
        server = f"{name}.local."
        info = ServiceInfo(
            type_=service_type,
            name=instance_name,
            addresses=[socket.inet_aton(ip)],
            port=port,
            properties={},
            server=server,
        )
        self.zeroconf.register_service(info)
        self.services.append(info)
        logger.info("mDNS published: %s on %s:%d", instance_name, ip, port)

    def stop(self):
        for info in self.services:
            try:
                self.zeroconf.unregister_service(info)
            except Exception:
                pass
        try:
            self.zeroconf.close()
        except Exception:
            pass
        self.services.clear()
