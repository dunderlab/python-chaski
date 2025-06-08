"""Certificate Authority server for the Chaski communication system."""

import asyncio
import logging
from typing import Dict

from chaski.ca import ChaskiCA

logging.basicConfig(level=logging.DEBUG)


async def run(ip: str, port: int, name: str) -> None:
    """Initialize and run a Certificate Authority server."""
    ssl_attributes: Dict[str, str] = {
        "Country Name": "CO",
        "Locality Name": "Manizales",
        "Organization Name": "DunderLab",
        "State or Province Name": "Caldas",
        "Common Name": "Chaski-Confluent",
    }

    ca: ChaskiCA = ChaskiCA(
        ip=ip,
        port=port,
        name=name,
        run=False,
        ssl_certificate_attributes=ssl_attributes,
    )
    print(f"CA Address: {ca.address}")
    await ca.run()


def main(ip: str = "127.0.0.1", port: int = 65432, name: str = "ChaskiCA") -> None:
    """Start the Certificate Authority server with the given parameters."""
    asyncio.run(run(ip, port, name))


if __name__ == "__main__":
    main()
