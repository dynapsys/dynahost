import os
from pathlib import Path

import pytest

from dynahost import compose as compose_mod
from dynahost.compose import parse_compose_services, ServicePort


def test_parse_compose_simple(tmp_path: Path):
    content = """
version: '3.8'
services:
  app:
    image: nginx:alpine
    ports:
      - "8080:80"
      - "127.0.0.1:9090:90/tcp"
      - "7000:7000/udp"  # ignored (udp)
  db:
    image: postgres:16
    ports:
      - {published: 5432, target: 5432, protocol: tcp}
"""
    f = tmp_path / "docker-compose.yml"
    f.write_text(content)

    if compose_mod.yaml is None:
        pytest.skip("PyYAML not installed; skipping compose parser test")

    services = parse_compose_services(f)
    assert "app" in services.ports_by_service
    assert "db" in services.ports_by_service

    app_ports = services.ports_by_service["app"]
    host_ports = sorted([p.host_port for p in app_ports])
    assert host_ports == [8080, 9090]

    db_ports = services.ports_by_service["db"]
    assert [p.host_port for p in db_ports] == [5432]
