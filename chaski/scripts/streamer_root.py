import asyncio
import logging
from chaski.streamer import ChaskiStreamer

logging.basicConfig(level=logging.DEBUG)


# ----------------------------------------------------------------------
async def run(ip, port, name):
    """"""
    root = ChaskiStreamer(
        ip=ip,
        port=port,
        name=name,
        root=True,
        run=False,
    )
    print(f"Root Address: {root.address}")
    await root.run()


# ----------------------------------------------------------------------
def main(ip='127.0.0.1', port=65433, name='ChaskiRoot'):
    """"""
    asyncio.run(run(ip, port, name))


if __name__ == '__main__':
    main()
