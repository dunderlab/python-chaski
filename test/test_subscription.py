"""
======================================
Test Subscriptions Between ChaskiNodes
======================================

This file contains asynchronous pytest test cases for validating subscription-based
connection logic among ChaskiNode instances. The test suite checks that nodes with
overlapping subscription topics establish connections correctly and that
disconnections occur as expected when specified by the test logic.
"""

import asyncio
from typing import List

import pytest

from chaski.utils.auto import create_nodes
from chaski.node import ChaskiNode
from .test_base import TestBase


@pytest.mark.asyncio
class TestSubscriptions(TestBase):
    """
    Test case container for validating subscription-driven connection logic in ChaskiNodes.

    This class includes tests for both persistent and disconnect-on-pair behaviors when
    matching nodes are discovered based on their subscription topics.
    """

    nodes: List[ChaskiNode] = []
    host: str = "127.0.0.1"

    async def test_single_subscription_no_disconnect(self) -> None:
        """
        Validate connections between ChaskiNodes for single-topic subscriptions without disconnects.

        The test procedure is as follows:
            1. Create nodes with subscriptions ['A', 'B', 'C', 'A', 'B', 'C'].
            2. Connect each non-initial node to the first node.
            3. Invoke peer discovery without disconnecting after pairing.
            4. Assert correct node-to-node connections for each shared topic.

        Raises:
            AssertionError: If expected connections are not established based on topic matches.
        """
        self.nodes = await create_nodes(["A", "B", "C", "A", "B", "C"], port=65440)
        for node in self.nodes[1:]:
            await node._connect_to_peer(self.nodes[0])

        await asyncio.sleep(0.3)
        for node in self.nodes[1:]:
            await node.discovery(on_pair="none")

        await asyncio.sleep(0.3)
        self.assert_connection(
            self.nodes[0],
            self.nodes[3],
            "Node 0 should be connected to Node 3 because both nodes are subscribed to the topic 'A'.",
        )
        self.assert_connection(
            self.nodes[1],
            self.nodes[4],
            "Node 1 should be connected to Node 4 because both nodes are subscribed to the topic 'B'.",
        )
        self.assert_connection(
            self.nodes[2],
            self.nodes[5],
            "Node 2 should be connected to Node 5 because both nodes are subscribed to the topic 'C'.",
        )

    async def test_single_subscription_with_disconnect(self) -> None:
        """
        Validate connections and required disconnections for multi-topic subscriptions.

        The test procedure is as follows:
            1. Create nodes with subscriptions ['A', 'B', 'C', ['A', 'C'], ['B', 'A'], 'C'].
            2. Connect each non-initial node to the first node.
            3. Perform discovery with disconnects on peer pairing.
            4. Assert connection establishment and lack thereof for various node pairs.

        Raises:
            AssertionError: If actual connections differ from those specified by topic criteria.
        """
        self.nodes = await create_nodes(
            ["A", "B", "C", ["A", "C"], ["B", "A"], "C"], port=65450
        )
        for node in self.nodes[1:]:
            await node.connect(self.nodes[0])

        await asyncio.sleep(0.3)
        for node in self.nodes[1:]:
            await node.discovery(on_pair="disconnect")

        await asyncio.sleep(0.3)
        self.assert_connection(
            self.nodes[0],
            self.nodes[3],
            "Node 0 must connect to Node 3 since both are subscribed to 'A'.",
        )
        self.assert_connection(
            self.nodes[0],
            self.nodes[4],
            "Node 0 must connect to Node 4 since they both subscribe to 'A' and 'B'.",
        )
        self.assert_connection(
            self.nodes[1],
            self.nodes[4],
            "Node 1 must connect to Node 4 since both are subscribed to 'B'.",
        )
        self.assert_connection(
            self.nodes[2],
            self.nodes[5],
            "Node 2 must connect to Node 5 since both are subscribed to 'C'.",
        )
        self.assert_no_connection(
            self.nodes[0],
            self.nodes[5],
            "Node 0 must not connect to Node 5 since their subscriptions do not overlap.",
        )
