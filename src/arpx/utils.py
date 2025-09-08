import logging
import shutil
import sys
from typing import List

logger = logging.getLogger("arpx.utils")

INSTALL_HINTS = {
    "ip": "sudo apt-get install iproute2 or similar",
    "arping": "sudo apt-get install arping / iputils-arping or similar",
    "mkcert": "See https://github.com/FiloSottile/mkcert for installation instructions",
    "certbot": "sudo apt-get install certbot or similar",
    "docker": "See https://docs.docker.com/engine/install/",
    "podman-compose": "pip install podman-compose or similar",
}

def check_dependencies(tools: List[str]) -> bool:
    """Check if all required command-line tools are available."""
    missing = []
    for tool in tools:
        if not shutil.which(tool):
            missing.append(tool)

    if not missing:
        return True

    logger.error("❌ Missing required system dependencies:")
    for tool in missing:
        hint = INSTALL_HINTS.get(tool, "Please install it using your system's package manager.")
        logger.error(f"  - '{tool}' not found. ({hint})")
    
    print("\nPlease install the missing dependencies and try again.", file=sys.stderr)
    return False
