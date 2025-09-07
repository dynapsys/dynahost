from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import yaml  # type: ignore
except Exception as e:  # pragma: no cover - optional dependency
    yaml = None  # type: ignore


@dataclass
class ServicePort:
    service: str
    host_port: int
    container_port: Optional[int] = None
    protocol: str = "tcp"


@dataclass
class ComposeServices:
    ports_by_service: Dict[str, List[ServicePort]]


def _parse_port_entry(svc: str, entry) -> Optional[ServicePort]:
    # string forms: "8080:80", "127.0.0.1:8080:80/tcp", "8080:80/udp"
    if isinstance(entry, str):
        proto = "tcp"
        if "/" in entry:
            entry, proto = entry.split("/", 1)
        parts = entry.split(":")
        if len(parts) == 2:
            host, cont = parts
            try:
                return ServicePort(svc, int(host), int(cont), proto)
            except ValueError:
                return None
        elif len(parts) == 3:
            # ip:host:container -> we care about host and container
            _, host, cont = parts
            try:
                return ServicePort(svc, int(host), int(cont), proto)
            except ValueError:
                return None
        else:
            return None
    # dict forms v3: { target: 80, published: 8080, protocol: tcp, mode: host }
    if isinstance(entry, dict):
        try:
            published = int(entry.get("published"))
        except Exception:
            return None
        proto = (entry.get("protocol") or "tcp").lower()
        target = entry.get("target")
        target_port = int(target) if target is not None else None
        return ServicePort(svc, published, target_port, proto)
    return None


def parse_compose_services(path: Path) -> ComposeServices:
    if yaml is None:
        raise RuntimeError(
            "PyYAML is not installed. Install optional extras: arpx[compose]"
        )
    data = yaml.safe_load(Path(path).read_text())
    services = data.get("services") or {}
    result: Dict[str, List[ServicePort]] = {}
    for svc_name, svc_def in services.items():
        ports = svc_def.get("ports") or []
        svc_ports: List[ServicePort] = []
        for entry in ports:
            sp = _parse_port_entry(svc_name, entry)
            if sp and sp.protocol.lower() == "tcp":
                svc_ports.append(sp)
        if svc_ports:
            result[svc_name] = svc_ports
    return ComposeServices(ports_by_service=result)
