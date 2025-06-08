"""Root streamer node for the Chaski distributed communication network."""

import asyncio
import logging

from chaski.streamer import ChaskiStreamer

logging.basicConfig(level=logging.DEBUG)


async def run(ip: str, port: int, name: str) -> None:
    """Initialize and run a ChaskiStreamer in root mode.

    Args:
        ip: IP address to bind the server to
        port: Port number to listen on
        name: Identifier for this root node
    """
    root: ChaskiStreamer = ChaskiStreamer(
        ip=ip,
        port=port,
        name=name,
        root=True,
        run=False,
    )
    print(f"Root Address: {root.address}")
    await root.run()


def main(ip: str = "127.0.0.1", port: int = 65433, name: str = "ChaskiRoot") -> None:
    """Start a ChaskiStreamer root node with the given parameters."""
    asyncio.run(run(ip, port, name))


if __name__ == "__main__":
    main()
