"""
=================================================
Test Node Discovery Module for ChaskiNode Network
=================================================

This module contains pytest tests for the discovery process in the
ChaskiNode network communication and management system. It ensures that nodes
can discover peers, establish connections based on subscriptions, and handle
disconnections properly during the discovery process.

Classes
-------
    - TestDiscovery : Test case class for validating node discovery and
      connection establishment.
"""

import pytest
import pytest_asyncio
import asyncio
from chaski.utils.auto import create_nodes
from typing import Optional
from chaski.node import ChaskiNode


@pytest.mark.asyncio
class TestDiscovery:
    """
    Test case for network discovery functionality of ChaskiNodes.

    This test case defines various scenarios to validate node discovery,
    connection establishment, and disconnection during the discovery process.
    """

    nodes = []
    ip = "127.0.0.1"

    async def _wait_for_connections(self):
        for i in range(10):
            await asyncio.sleep(0.3)

    @pytest_asyncio.fixture(autouse=True)
    async def cleanup(self):
        """Cleanup fixture to stop all nodes after each test"""
        yield
        for node in self.nodes:
            await node.stop()
        await self._wait_for_connections()

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

    async def test_no_discovery(self):
        """
        Test that nodes do not discover new peers if discovery process is not invoked.

        This test initializes two ChaskiNode instances with different subscriptions,
        connects them manually, and verifies that they recognize each other post-connection
        without invoking the discovery process. The test checks if the nodes do not perform
        automatic peer discovery.

        Steps:
        1. Create two nodes with subscriptions 'A' and 'B'.
        2. Manually connect node 0 to node 1.
        3. Wait briefly to ensure the connection is established.
        4. Verify that each node reports the correct number of established connections.
        5. Assert the nodes are connected to each other.
        6. Close all nodes.

        Raises
        ------
        AssertionError
            If the nodes do not correctly establish the connection without discovery.
        """
        self.nodes = await create_nodes(list("AB"), self.ip)
        await self.nodes[0].connect(self.nodes[1])

        await asyncio.sleep(0.3)
        await self.nodes[1].discovery()

        for i, node in enumerate(self.nodes):
            assert len(node.edges) == 1, f"Node {i} discovery failed"
        self.assert_connection(*self.nodes, "The nodes are not connected to each other")

    async def test_single_server_connect_discovery(self):
        """
        Test the discovery process when a single server connects to multiple peers.

        This test initializes three ChaskiNodes with specific subscriptions,
        connects them to a primary node (node 0), and verifies that all nodes
        correctly discover each other after manual connections and discovery
        process.

        Steps:
        1. Create three nodes with subscriptions 'A', 'B', 'B'.
        2. Connect node 0 to both node 1 and node 2.
        3. Verify the initial connection state.
        4. Perform discovery on nodes 1 and 2.
        5. Verify the final connection state.
        6. Assert all nodes are correctly connected to each other.
        7. Close all nodes.

        Raises
        ------
        AssertionError
            If any node fails to establish the expected number of connections.
        """
        self.nodes = await create_nodes(list("ABB"), self.ip)
        await self.nodes[0].connect(self.nodes[1])
        await self.nodes[0].connect(self.nodes[2])

        await asyncio.sleep(0.3)
        assert len(self.nodes[0].edges) == 2, f"Node 0 discovery failed"
        assert len(self.nodes[1].edges) == 1, f"Node 1 discovery failed"
        assert len(self.nodes[2].edges) == 1, f"Node 2 discovery failed"

        self.nodes[1].paired_event["B"].set()
        await self.nodes[2].discovery(on_pair="none", timeout=1)

        await asyncio.sleep(0.3)
        assert len(self.nodes[0].edges) == 2, f"Node 0 discovery failed after discovery"
        assert len(self.nodes[1].edges) == 2, f"Node 1 discovery failed after discovery"
        assert len(self.nodes[2].edges) == 2, f"Node 2 discovery failed after discovery"

        self.assert_connection(
            self.nodes[0], self.nodes[1], "The node 0 is not connected to node 1"
        )
        self.assert_connection(
            self.nodes[0], self.nodes[2], "The node 0 is not connected to node 2"
        )
        self.assert_connection(
            self.nodes[1], self.nodes[2], "The node 1 is not connected to node 2"
        )

    async def test_single_discovery(self):
        """
        Test discovery process with nodes having similar subscriptions.

        This test initializes three ChaskiNode instances with specified subscriptions,
        connects them manually, and verifies that all nodes correctly discover
        each other after manual connections and running the discovery process.

        Steps:
        1. Create three nodes with subscriptions 'A', 'B', 'B'.
        2. Connect node 1 to node 0, and node 2 to node 0.
        3. Verify the initial connection state.
        4. Run the discovery process on nodes 1 and 2.
        5. Verify the final connection state.
        6. Assert all nodes are correctly connected to each other.
        7. Close all nodes.

        Raises
        ------
        AssertionError
            If any node fails to establish the expected number of connections.
        """
        self.nodes = await create_nodes(list("ABB"), self.ip)
        await self.nodes[1].connect(self.nodes[0])
        await self.nodes[2].connect(self.nodes[0])

        await asyncio.sleep(0.3)
        assert len(self.nodes[0].edges) == 2, f"Node 0 discovery failed"
        assert len(self.nodes[1].edges) == 1, f"Node 1 discovery failed"
        assert len(self.nodes[2].edges) == 1, f"Node 2 discovery failed"

        await self.nodes[1].discovery(on_pair="none", timeout=1)
        await self.nodes[2].discovery(on_pair="none", timeout=1)

        await asyncio.sleep(0.3)
        assert len(self.nodes[0].edges) == 2, f"Node 0 discovery failed after discovery"
        assert len(self.nodes[1].edges) == 2, f"Node 1 discovery failed after discovery"
        assert len(self.nodes[2].edges) == 2, f"Node 2 discovery failed after discovery"

        self.assert_connection(
            self.nodes[0], self.nodes[1], "The node 0 is not connected to node 1"
        )
        self.assert_connection(
            self.nodes[0], self.nodes[2], "The node 0 is not connected to node 2"
        )
        self.assert_connection(
            self.nodes[1], self.nodes[2], "The node 1 is not connected to node 2"
        )

    async def test_single_discovery_with_disconnection(self):
        """
        Test the discovery process with disconnections.

        This test initializes three ChaskiNodes with specified subscriptions, connects them manually,
        performs the discovery and tests the behavior when nodes are disconnected during the discovery process.

        Steps:
        1. Create three nodes with subscriptions 'A', 'B', 'B'.
        2. Connect node 1 to node 0, and node 2 to node 0.
        3. Ensure initial connections are established.
        4. Set node 1's paired_event to simulate it being paired.
        5. Run discovery on node 2 with disconnect on pair.
        6. Verify the final connection states.
        7. Close all nodes.

        Raises
        ------
        AssertionError
            If any node fails to establish or maintain the expected connections after discovery and disconnections.
        """
        self.nodes = await create_nodes(list("ABB"), self.ip)
        await self.nodes[1].connect(self.nodes[0])
        await self.nodes[2].connect(self.nodes[0])

        await asyncio.sleep(0.3)
        assert len(self.nodes[0].edges) == 2, f"Node 0 connection failed"
        assert len(self.nodes[1].edges) == 1, f"Node 1 connection failed"
        assert len(self.nodes[2].edges) == 1, f"Node 2 connection failed"

        self.nodes[1].paired_event["B"].set()
        await self.nodes[2].discovery(on_pair="disconnect", timeout=1)
        await asyncio.sleep(0.3)

        assert len(self.nodes[0].edges) == 1, f"Node 0 discovery failed after discovery"
        assert len(self.nodes[1].edges) == 2, f"Node 1 discovery failed after discovery"
        assert len(self.nodes[2].edges) == 1, f"Node 2 discovery failed after discovery"

        self.assert_connection(
            self.nodes[0], self.nodes[1], "The node 0 is not connected to node 1"
        )
        self.assert_connection(
            self.nodes[2], self.nodes[1], "The node 0 is not connected to node 2"
        )

    async def test_multiple_discovery(self):
        """
        Test the discovery process with multiple nodes having the same subscription.

        This test initializes multiple ChaskiNode instances with a single different subscription
        and multiple similar subscriptions, connects them manually, and verifies that all nodes
        correctly discover each other after running the discovery process.

        Steps:
        1. Create seven nodes with subscriptions 'A', 'B', 'B', 'B', 'B', 'B', 'B'.
        2. Connect node 1 to node 0, and nodes 2-6 to node 0.
        3. Verify the initial connection state.
        4. Run the discovery process on nodes 1-6.
        5. Verify the final connection state.
        6. Assert all nodes are correctly connected to each other.
        7. Close all nodes.

        Raises
        ------
        AssertionError
            If any node fails to establish the expected number of connections after discovery.
        """
        self.nodes = await create_nodes(list("ABBBBBB"), self.ip)
        await self.nodes[1].connect(self.nodes[0])
        await self.nodes[2].connect(self.nodes[0])
        await self.nodes[3].connect(self.nodes[0])
        await self.nodes[4].connect(self.nodes[0])
        await self.nodes[5].connect(self.nodes[0])
        await self.nodes[6].connect(self.nodes[0])

        await self._wait_for_connections()

        assert len(self.nodes[0].edges) == 6, f"Node 0 failed before discovery"
        assert len(self.nodes[1].edges) == 1, f"Node 1 failed before discovery"
        assert len(self.nodes[2].edges) == 1, f"Node 2 failed before discovery"
        assert len(self.nodes[3].edges) == 1, f"Node 3 failed before discovery"
        assert len(self.nodes[4].edges) == 1, f"Node 4 failed before discovery"
        assert len(self.nodes[5].edges) == 1, f"Node 5 failed before discovery"
        assert len(self.nodes[6].edges) == 1, f"Node 6 failed before discovery"

        await self.nodes[1].discovery(on_pair="none")
        await self.nodes[2].discovery(on_pair="none")
        await self.nodes[3].discovery(on_pair="none")
        await self.nodes[4].discovery(on_pair="none")
        await self.nodes[5].discovery(on_pair="none")
        await self.nodes[6].discovery(on_pair="none")

        await self._wait_for_connections()

        assert len(self.nodes[0].edges) == 6, f"Node 0 discovery failed after discovery"
        assert len(self.nodes[1].edges) == 6, f"Node 1 discovery failed after discovery"
        assert len(self.nodes[2].edges) == 2, f"Node 2 discovery failed after discovery"
        assert len(self.nodes[3].edges) == 2, f"Node 3 discovery failed after discovery"
        assert len(self.nodes[4].edges) == 2, f"Node 4 discovery failed after discovery"
        assert len(self.nodes[5].edges) == 2, f"Node 5 discovery failed after discovery"
        assert len(self.nodes[6].edges) == 2, f"Node 6 discovery failed after discovery"

        self.assert_connection(
            self.nodes[0], self.nodes[1], "The node 0 is not connected to node 1"
        )
        self.assert_connection(
            self.nodes[0], self.nodes[2], "The node 0 is not connected to node 2"
        )
        self.assert_connection(
            self.nodes[0], self.nodes[3], "The node 1 is not connected to node 3"
        )
        self.assert_connection(
            self.nodes[0], self.nodes[4], "The node 0 is not connected to node 4"
        )
        self.assert_connection(
            self.nodes[0], self.nodes[5], "The node 0 is not connected to node 5"
        )
        self.assert_connection(
            self.nodes[0], self.nodes[6], "The node 0 is not connected to node 6"
        )
        self.assert_connection(
            self.nodes[1], self.nodes[2], "The node 0 is not connected to node 2"
        )
        self.assert_connection(
            self.nodes[1], self.nodes[3], "The node 1 is not connected to node 3"
        )
        self.assert_connection(
            self.nodes[1], self.nodes[4], "The node 1 is not connected to node 4"
        )
        self.assert_connection(
            self.nodes[1], self.nodes[5], "The node 1 is not connected to node 5"
        )
        self.assert_connection(
            self.nodes[1], self.nodes[2], "The node 1 is not connected to node 6"
        )
