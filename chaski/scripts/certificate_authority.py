import asyncio
import os
import logging

from chaski.ca import ChaskiCA

logging.basicConfig(level=logging.DEBUG)


async def run(ip, port, name):
    """"""
    ca = ChaskiCA(
        ip=ip,
        port=port,
        name=name,
        run=False,
        ssl_certificate_attributes={
            "Country Name": "CO",
            "Locality Name": "Manizales",
            "Organization Name": "DunderLab",
            "State or Province Name": "Caldas",
            "Common Name": "Chaski-Confluent",
        },
    )
    print(f"CA Address: {ca.address}")
    await ca.run()


def main(ip="127.0.0.1", port=65432, name="ChaskiCA"):
    """"""
    asyncio.run(run(ip, port, name))


if __name__ == "__main__":
    main()
