"""
===============================================
Chaski Node Discovery Mechanism Test Suite
===============================================

This module contains comprehensive pytest test cases for validating the peer discovery
and connection management functionality in the Chaski network communication system.

The test suite verifies critical aspects of the discovery process including:

- Basic node connection establishment without discovery
- Peer detection and connection based on shared subscription topics
- Handling of connection events during the discovery process
- Proper disconnection behavior during topology changes
- Scalability with multiple nodes sharing common subscriptions
- Network reorganization after discovery events

All tests use asynchronous patterns to simulate realistic network conditions
and verify that nodes properly establish, maintain, and terminate connections
as expected in various scenarios.
"""

import asyncio
from typing import List

import pytest

from chaski.node import ChaskiNode
from chaski.utils.auto import create_nodes
from .test_base import TestBase


@pytest.mark.asyncio
class TestDiscovery(TestBase):
    """
    Test suite for validating the peer discovery mechanism in Chaski networks.

    This class contains test cases that verify the node discovery process
    under various conditions, including manual connections, automatic peer
    finding, connection establishment based on matching subscriptions, and
    proper disconnection handling during network reorganization.
    """

    nodes: List[ChaskiNode] = []
    ip: str = "127.0.0.1"

    @pytest.mark.asyncio
    async def test_no_discovery(self) -> None:
        """
        Verify that nodes connect manually without triggering discovery.

        This test ensures that nodes establish direct connections when explicitly
        instructed to connect, without initiating the automatic discovery process
        to find additional peers.

        Test procedure:
        1. Create two nodes with subscriptions 'A' and 'B'
        2. Manually connect node 0 to node 1
        3. Wait for connection establishment
        4. Call discovery on node 1 but no new connections should form
        5. Verify each node has exactly one connection
        6. Confirm both nodes are properly connected to each other

        Raises:
            AssertionError: If nodes fail to establish direct connections or
                           if unexpected automatic discovery occurs
        """
        self.nodes = await create_nodes(list("AB"), self.ip)
        await self.nodes[0].connect(self.nodes[1])

        await asyncio.sleep(0.3)
        await self.nodes[1].discovery()

        for i, node in enumerate(self.nodes):
            assert len(node.edges) == 1, f"Node {i} discovery failed"
        self.assert_connection(*self.nodes, "The nodes are not connected to each other")

    @pytest.mark.asyncio
    async def test_single_server_connect_discovery(self) -> None:
        """
        Validate discovery when one node connects to multiple peers.

        This test verifies that when a central node connects to multiple peers,
        those peers can discover each other through the discovery process
        if they have matching subscription topics.

        Test procedure:
        1. Create three nodes with subscriptions 'A', 'B', 'B'
        2. Connect node 0 to both node 1 and node 2
        3. Verify initial connection counts
        4. Set node 1's paired event to indicate it's ready for pairing
        5. Trigger discovery on node 2
        6. Verify that nodes 1 and 2 discover and connect to each other
        7. Confirm all expected connections between the three nodes

        Raises:
            AssertionError: If nodes fail to establish expected connections
                           or if connection counts are incorrect
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

    @pytest.mark.asyncio
    async def test_single_discovery(self) -> None:
        """
        Test bidirectional discovery between nodes with matching subscriptions.

        This test verifies that when nodes connect to a common peer and then
        perform discovery, they can find and connect to each other if they
        share subscription topics.

        Test procedure:
        1. Create three nodes with subscriptions 'A', 'B', 'B'
        2. Connect nodes 1 and 2 to node 0
        3. Verify initial connection state
        4. Trigger discovery on both nodes 1 and 2
        5. Verify that node 1 and 2 discover and connect to each other
        6. Confirm the final connection topology matches expectations

        Raises:
            AssertionError: If discovery fails to establish expected connections
                           or if connection counts are incorrect
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

    @pytest.mark.asyncio
    async def test_single_discovery_with_disconnection(self) -> None:
        """
        Validate discovery with disconnection from original peers.

        This test verifies that when nodes perform discovery with the "disconnect"
        option, they properly disconnect from discovery facilitators after
        establishing direct connections to relevant peers.

        Test procedure:
        1. Create three nodes with subscriptions 'A', 'B', 'B'
        2. Connect nodes 1 and 2 to node 0
        3. Verify initial connection counts
        4. Set node 1's paired event to indicate it's ready for pairing
        5. Trigger discovery on node 2 with disconnect option
        6. Verify node 2 disconnects from node 0 after connecting to node 1
        7. Confirm the final network topology matches expectations

        Raises:
            AssertionError: If disconnection behavior is incorrect or
                           if final connection state doesn't match expectations
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
            self.nodes[2], self.nodes[1], "The node 2 is not connected to node 1"
        )

    @pytest.mark.asyncio
    async def test_multiple_discovery(self) -> None:
        """
        Test discovery in a larger network with multiple shared subscriptions.

        This test validates the discovery process in a network with seven nodes,
        where six nodes share a common subscription and can discover each other
        through a central node.

        Test procedure:
        1. Create seven nodes with subscriptions 'A', 'B', 'B', 'B', 'B', 'B', 'B'
        2. Connect nodes 1-6 to node 0
        3. Verify initial connection state
        4. Trigger discovery on all nodes
        5. Wait for connections to stabilize
        6. Verify each node has established appropriate connections
        7. Confirm all expected node connections exist

        Raises:
            AssertionError: If discovery fails to establish expected connections
                           or if connection counts are incorrect after discovery
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
            self.nodes[0], self.nodes[3], "The node 0 is not connected to node 3"
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
            self.nodes[1], self.nodes[2], "The node 1 is not connected to node 2"
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
            self.nodes[1], self.nodes[6], "The node 1 is not connected to node 6"
        )
