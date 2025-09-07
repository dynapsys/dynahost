import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from arpx.network import NetworkVisibleManager
from arpx.bridge import ComposeBridge


@pytest.mark.e2e
def test_compose_bridge_end_to_end(tmp_path: Path):
    # Preconditions: root, docker, arping
    if os.geteuid() != 0:
        pytest.skip("root required for e2e network operations")
    if shutil.which("docker") is None:
        pytest.skip("docker required for e2e test")
    if shutil.which("arping") is None:
        pytest.skip("iputils-arping required for e2e test")
    if os.environ.get("DYNAHOST_E2E", "0") != "1":
        pytest.skip("Set DYNAHOST_E2E=1 to run this heavy e2e test")

    compose_file = Path.cwd() / "examples" / "docker" / "docker-compose.yml"
    assert compose_file.exists()

    # Start stack
    subprocess.run(["docker", "compose", "-f", str(compose_file), "up", "-d"], check=True)

    iface = NetworkVisibleManager.auto_detect_interface()

    cb = ComposeBridge(iface)
    created = []
    try:
        created = cb.up(compose_file, ip_start=120)
        # Expect at least 2 services bridged
        assert len(created) >= 2

        # Give a moment for services to be ready
        time.sleep(2)

        # Try to fetch from the first bridged service
        alias_ip, svc, ports = created[0]
        port = ports[0]
        import urllib.request

        resp = urllib.request.urlopen(f"http://{alias_ip}:{port}", timeout=2)
        assert resp.status == 200
    finally:
        cb.cleanup()
        subprocess.run(["docker", "compose", "-f", str(compose_file), "down", "-v"], check=False)
