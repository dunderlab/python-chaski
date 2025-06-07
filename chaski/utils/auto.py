"""
====================
Automation Utilities
====================

This module provides a set of automated utilities specifically designed for
creating and managing ChaskiNode instances. These utilities streamline the setup
of distributed node communication and coordination systems.
"""

from chaski.node import ChaskiNode
from typing import List, Union
import asyncio
from string import ascii_uppercase

# PORT = 65440
PORT = 0


async def _wait_for_connections():
    for i in range(10):
        await asyncio.sleep(0.3)


async def create_nodes(
    subscriptions: Union[int, List[str]],
    ip: str = "127.0.0.1",
    port: int = PORT,
) -> List[ChaskiNode]:
    """
    Create a list of ChaskiNode instances.

    This function generates a list of ChaskiNode instances with the given number of nodes
    or subscriptions. If an integer is provided for subscriptions, the first `n` letters
    of the alphabet will be used as default subscription topics. Each node will run on
    a sequentially incremented port starting from the given port number.

    Parameters
    ----------
    subscriptions : Union[int, List[str]]
        The number of nodes to create if an integer is provided. If a list of strings is
        provided, each string represents a subscription topic for a node.
    ip : str, optional
        The IP address where the nodes will bind to, by default '127.0.0.1'.
    port : int, optional
        The starting port number for the nodes, by default PORT.

    Returns
    -------
    List[ChaskiNode]
        A list of ChaskiNode instances.
    """
    if isinstance(subscriptions, int):
        subscriptions = list(ascii_uppercase)[:subscriptions]

    if PORT == 0:
        mult = 0
    else:
        mult = 1

    nodes = [
        ChaskiNode(
            ip=ip,
            port=mult * (port + i),
            name=f"Node{i}",
            subscriptions=sub,
            run=True,
            ttl=15,
            paired=(i == 0),
            reconnections=None,
            max_connections=10,
        )
        for i, sub in enumerate(subscriptions)
    ]

    await _wait_for_connections()
    return nodes


async def run_transmission(producer, consumer, parent=None):
    """"""
    await _wait_for_connections()
    # await producer.connect(consumer.address)
    await consumer.connect(producer.address)

    await _wait_for_connections()
    await producer.push(
        "topic1",
        {
            "data": "test0",
        },
    )

    count = 0
    async with consumer as message_queue:
        async for incoming_message in message_queue:

            if parent:
                assert f"test{count}" == incoming_message.data["data"]

            if count >= 5:
                await consumer.stop()
                await producer.stop()
                return

            count += 1
            await producer.push(
                "topic1",
                {
                    "data": f"test{count}",
                },
            )

    await consumer.stop()
    await producer.stop()
