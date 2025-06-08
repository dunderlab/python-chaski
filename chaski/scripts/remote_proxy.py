"""Remote proxy server for executing Python modules in a Chaski network environment."""

import asyncio
import argparse
import logging
from typing import List

from chaski.remote import ChaskiRemote

logging.basicConfig(level=logging.DEBUG)

parser = argparse.ArgumentParser(description="Chaski Remote Server")
parser.add_argument(
    "-i",
    "--ip",
    type=str,
    default="127.0.0.1",
    help="IP address to run the server on",
)
parser.add_argument(
    "-p",
    "--port",
    type=str,
    default="65434",
    help="Port number to run the server on",
)
parser.add_argument(
    "-n",
    "--name",
    type=str,
    default="ChaskiRemote",
    help="Name of the server",
)
parser.add_argument(
    "modules", type=str, help="Comma-separated list of available modules"
)

args: argparse.Namespace = parser.parse_args()


async def run() -> None:
    """Initialize and run the ChaskiRemote server with command-line arguments."""
    available_modules: List[str] = args.modules.split(",")

    server: ChaskiRemote = ChaskiRemote(
        ip=args.ip,
        port=int(args.port),  # Convert port to int since it's defined as str in args
        name=args.name,
        available=available_modules,
        run=False,
    )

    print(f"Remote Server Address: {server.address}")
    await server.run()


def main() -> None:
    """Entry point to start the ChaskiRemote server."""
    asyncio.run(run())


if __name__ == "__main__":
    main()
