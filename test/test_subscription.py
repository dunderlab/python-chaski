"""
=========================
Test Subscriptions Module
=========================

This module contains pytest tests designed to assert and validate
the connection functionalities of ChaskiNode instances based on their subscription topics.
The tests are structured to ensure that nodes with matching subscriptions establish
connections correctly and can communicate effectively.

Functions
---------
- assert_connection(node1, node2, msg) : Assert that two ChaskiNode instances are connected.
- assert_no_connection(node1, node2, msg) : Assert that two ChaskiNode instances are not connected.
- test_single_subscription_no_disconnect() : Test single subscription connections between ChaskiNodes without disconnecting other nodes.
- test_single_subscription_with_disconnect() : Test single subscription connections between ChaskiNodes with node disconnection during pairing.
"""

import pytest
import pytest_asyncio
import asyncio
from typing import Optional
from chaski.utils.auto import create_nodes
from chaski.node import ChaskiNode


@pytest.mark.asyncio
class TestSubscriptions:
    """
    Test case for testing a single subscription scenario in ChaskiNodes.

    This test case defines the infrastructure to create multiple ChaskiNode instances
    and validate the correct establishment of connections based on their subscription topics.
    """

    nodes = []
    host = "127.0.0.1"

    @pytest_asyncio.fixture(autouse=True)
    async def cleanup(self):
        """Cleanup fixture to stop all nodes after each test"""
        yield
        for node in self.nodes:
            print(f"Closing node {node.port}")
            await node.stop()
        await asyncio.sleep(1)

    def assert_connection(
        self, node1: ChaskiNode, node2: ChaskiNode, msg: Optional[str] = None
    ):
        """
        Assert that two ChaskiNodes are connected to each other.

        This method checks if `node1` is connected to `node2` and vice versa.
        It raises an assertion error if the connection is not established in
        both directions.

        Parameters
        ----------
        node1 : ChaskiNode
                The first ChaskiNode to check connection from.
        node2 : ChaskiNode
                The second ChaskiNode to check connection to.
        msg : str, optional
                An optional message to include in the assertion error if the
                nodes are not connected.

        Raises
        ------
        AssertionError
                If `node1` is not connected to `node2` or `node2` is not connected to `node1`.
        """
        conn = node1.is_connected_to(node2) and node2.is_connected_to(node1)
        if not conn and msg is not None:
            pytest.fail(msg)
        assert conn

    def assert_no_connection(
        self, node1: ChaskiNode, node2: ChaskiNode, msg: Optional[str] = None
    ):
        """
        Assert that two ChaskiNodes are not connected to each other.

        This method checks if `node1` is connected to `node2` and vice versa.
        It raises an assertion error if the connection is established in
        either direction.

        Parameters
        ----------
        node1 : ChaskiNode
                The first ChaskiNode to check connection from.
        node2 : ChaskiNode
                The second ChaskiNode to check connection to.
        msg : str, optional
                An optional message to include in the assertion error if the
                nodes are connected.

        Raises
        ------
        AssertionError
                If `node1` is connected to `node2` or `node2` is connected to `node1`.
        """
        conn = node1.is_connected_to(node2) and node2.is_connected_to(node1)
        if conn and msg is not None:
            pytest.fail(msg)
        assert not conn

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

    async def test_single_subscription_with_disconnect(self):
        """
        Test single subscription connections between ChaskiNodes with node disconnection during pairing.

        This test method performs the following steps to ensure nodes with matching subscriptions
        connect correctly and disconnect from the discovery node:

        1. Create nodes with designated subscriptions: ['A', 'B', 'C', ['A', 'C'], ['B', 'A'], 'C'].
        2. Initiate connections from each subsequent node to the first node.
        3. Trigger a discovery phase to find and pair peers based on subscriptions.
        4. Disconnect from the discovery node after nodes are paired.
        5. Validate if nodes are connected based on their subscription topics.
        6. Close all node instances upon completion.

        Assertions
        ----------
        AssertionError
            Raised if the nodes do not pair correctly according to their subscription topics.
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
