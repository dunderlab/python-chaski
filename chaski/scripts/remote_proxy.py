import asyncio
import argparse
import logging

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

args = parser.parse_args()


# ----------------------------------------------------------------------
async def run():
    """"""
    server = ChaskiRemote(
        ip=args.ip,
        port=args.port,
        name=args.name,
        available=args.modules.split(","),
        run=False,
    )

    print(f"CA Address: {server.address}")
    await server.run()


# ----------------------------------------------------------------------
def main():
    """"""
    asyncio.run(run())


if __name__ == "__main__":
    main()
