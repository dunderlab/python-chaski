"""
=========================
Test Subscriptions Module
=========================

This module contains the TestSubscriptions class designed to assert and validate
the connection functionalities of ChaskiNode instances based on their subscription topics.
The tests are structured to ensure that nodes with matching subscriptions establish
connections correctly and can communicate effectively.

Functions
---------
- _close_nodes(nodes) : Close all instances of ChaskiNode in the provided list.
- assertConnection(node1, node2, msg) : Assert that two ChaskiNode instances are connected.
- assertNoConnection(node1, node2, msg) : Assert that two ChaskiNode instances are not connected.
- test_single_subscription_no_disconnect() : Test single subscription connections between ChaskiNodes without disconnecting other nodes.
- test_single_subscription_with_disconnect() : Test single subscription connections between ChaskiNodes with node disconnection during pairing.
"""

import pytest
import unittest
import asyncio
from chaski.utils.auto import create_nodes
from .test_base import TestBase


class TestSubscriptions(unittest.IsolatedAsyncioTestCase, TestBase):
    """
    Test case for testing a single subscription scenario in ChaskiNodes.

    This test case defines the infrastructure to create multiple ChaskiNode instances
    and validate the correct establishment of connections based on their subscription topics.
    """

    nodes = []
    host = "127.0.0.1"

    @pytest.mark.asyncio
    async def test_single_subscription_no_disconnect(self):
        """
        Test single subscription connections between ChaskiNodes without disconnecting other nodes.

        This test method performs the following steps to ensure nodes with matching subscriptions
        connect correctly:

        1. Create nodes with designated subscriptions: ['A', 'B', 'C', 'A', 'B', 'C'].
        2. Initiate connections from each subsequent node to the first node.
        3. Trigger a discovery phase to find and pair peers based on subscriptions.
        4. Immediately disconnect nodes after they are paired.
        5. Validate if nodes are connected based on their subscription topics.
        6. Close all node instances upon completion.

        Assertions
        ----------
        AssertionError
            Raised if the nodes do not pair correctly according to their subscription topics.
        """
        self.nodes = await create_nodes(["A", "B", "C", "A", "B", "C"], port=65440)
        for node in self.nodes[1:]:
            await node._connect_to_peer(self.nodes[0])

        await asyncio.sleep(0.3)
        for node in self.nodes[1:]:
            await node.discovery(on_pair="none")

        await asyncio.sleep(0.3)
        self.assertConnection(
            self.nodes[0],
            self.nodes[3],
            "Node 0 should be connected to Node 3 because both nodes are subscribed to the topic 'A'.",
        )
        self.assertConnection(
            self.nodes[1],
            self.nodes[4],
            "Node 1 should be connected to Node 4 because both nodes are subscribed to the topic 'B'.",
        )
        self.assertConnection(
            self.nodes[2],
            self.nodes[5],
            "Node 2 should be connected to Node 5 because both nodes are subscribed to the topic 'C'.",
        )

    @pytest.mark.asyncio
    async def test_single_subscription_with_disconnect(self):
        """"""
        self.nodes = await create_nodes(
            ["A", "B", "C", ["A", "C"], ["B", "A"], "C"], port=65450
        )
        for node in self.nodes[1:]:
            await node._connect_to_peer(self.nodes[0])

        await asyncio.sleep(0.3)
        for node in self.nodes[1:]:
            await node.discovery(on_pair="disconnect")

        await asyncio.sleep(0.3)
        self.assertConnection(
            self.nodes[0],
            self.nodes[3],
            "Node 0 must connect to Node 3 since both are subscribed to 'A'.",
        )
        self.assertConnection(
            self.nodes[0],
            self.nodes[4],
            "Node 0 must connect to Node 4 since they both subscribe to 'A' and 'B'.",
        )
        self.assertConnection(
            self.nodes[1],
            self.nodes[4],
            "Node 1 must connect to Node 4 since both are subscribed to 'B'.",
        )
        self.assertConnection(
            self.nodes[2],
            self.nodes[5],
            "Node 2 must connect to Node 5 since both are subscribed to 'C'.",
        )
        self.assertNoConnection(
            self.nodes[0],
            self.nodes[5],
            "Node 0 must not connect to Node 5 since their subscriptions do not overlap.",
        )


if __name__ == "__main__":
    unittest.main()
