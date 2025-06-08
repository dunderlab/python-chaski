"""
=================================================
Chaski Network Connection Testing Framework
=================================================

This module provides a comprehensive test suite for validating the connection
capabilities of ChaskiNode instances within a distributed peer-to-peer network.
The tests verify critical aspects of network operation including:

- Establishing and maintaining peer-to-peer connections
- Managing multiple simultaneous connections
- Graceful handling of disconnection events
- Detection and cleanup of orphaned connections
- Network reliability under various connection patterns
- Protocol-specific behavior (IPv4 and IPv6)
- UDP communication between nodes

These tests ensure that ChaskiNodes can reliably form resilient network topologies,
maintain connections appropriately, and recover from various network disruptions.
"""

from typing import List, Dict

import pytest
import pytest_asyncio

from chaski.node import ChaskiNode
from chaski.utils.auto import create_nodes
from .test_base import TestBase


@pytest.mark.asyncio
class _TestConnections(TestBase):
    """
    Base class for testing connection-related functionality between ChaskiNode instances.

    This abstract class provides test methods for validating that ChaskiNodes can
    properly establish, maintain, and terminate connections under various network
    conditions. The tests verify both normal operation and edge cases such as
    disconnections and orphaned connections.

    This class is not meant to be instantiated directly; instead, concrete subclasses
    should be created that specify the IP address format to test (IPv4 or IPv6).
    """

    # ip attribute will be defined in subclasses
    ip: str

    @pytest.mark.asyncio
    async def test_single_connections(self) -> None:
        """
        Validate basic one-to-one connections between ChaskiNodes.

        This test verifies that nodes can establish simple point-to-point
        connections and properly maintain their connection states.

        Test procedure:
        1. Create 4 ChaskiNode instances
        2. Connect Node 0 to Node 1 and Node 2 to Node 3
        3. Wait for connections to stabilize
        4. Verify each node has exactly one active connection

        Raises:
            AssertionError: If any node fails to establish exactly one connection
        """
        self.nodes = await create_nodes(4, self.ip)
        await self.nodes[0].connect(self.nodes[1])
        await self.nodes[2].connect(self.nodes[3])

        await self._wait_for_connections()

        for i, node in enumerate(self.nodes, start=1):
            assert len(node.edges) == 1, f"Node {i} connection failed"

    @pytest.mark.asyncio
    async def test_multiple_connections(self) -> None:
        """
        Validate a central node handling multiple simultaneous connections.

        This test verifies that a single ChaskiNode can successfully manage
        multiple concurrent connections with other nodes in the network.

        Test procedure:
        1. Create 5 ChaskiNode instances
        2. Connect Nodes 1-4 to Node 0 (creating a star topology)
        3. Wait for connections to stabilize
        4. Verify that Nodes 1-4 each have exactly one connection
        5. Verify that Node 0 has exactly four connections

        Raises:
            AssertionError: If any node fails to establish the expected number of connections
        """
        self.nodes = await create_nodes(5, self.ip)
        for node in self.nodes[1:]:
            await node.connect(self.nodes[0])

        await self._wait_for_connections()

        for i, node in enumerate(self.nodes[1:], start=1):
            assert len(node.edges) == 1, f"Node {i}'s connection to Node 0 failed"

        assert (
            len(self.nodes[0].edges) == 4
        ), f"Node 0 failed to establish all connections"

    @pytest.mark.asyncio
    async def test_disconnection(self) -> None:
        """
        Validate network behavior when a central node disconnects.

        This test verifies that when a node with multiple connections is stopped,
        all connected nodes properly detect the disconnection and update their
        connection states accordingly.

        Test procedure:
        1. Create 5 ChaskiNode instances
        2. Connect Nodes 1-4 to Node 0 (creating a star topology)
        3. Wait for connections to stabilize
        4. Stop Node 0
        5. Verify that all nodes have zero active connections

        Raises:
            AssertionError: If any node fails to properly detect the disconnection
        """
        self.nodes = await create_nodes(5, self.ip)
        for node in self.nodes[1:]:
            await node.connect(self.nodes[0])

        await self._wait_for_connections()

        await self.nodes[0].stop()

        await self._wait_for_connections()

        assert len(self.nodes[0].edges) == 0, "Node 0 not disconnected"
        for i, node in enumerate(self.nodes[1:], start=1):
            assert len(node.edges) == 0, f"Node {i} not disconnected"

    @pytest.mark.asyncio
    async def test_edges_disconnection(self) -> None:
        """
        Validate selective edge disconnection in a complex network topology.

        This test verifies that nodes can handle selective disconnection of
        specific edges while maintaining other connections. It creates a network
        where nodes are connected to two central nodes, then disconnects edges
        from one central node while verifying the other connections remain intact.

        Test procedure:
        1. Create 6 ChaskiNode instances
        2. Connect Nodes 1-5 to Node 0
        3. Connect Nodes 0-4 to Node 5 (creating a dual-centered topology)
        4. Sequentially disconnect Node 0's connections one by one
        5. Verify connection counts after each disconnection
        6. Verify that Nodes 1-4 remain connected to Node 5

        Raises:
            AssertionError: If connections are not properly maintained or terminated
        """
        self.nodes = await create_nodes(6, self.ip)

        for node in self.nodes:
            if node.port != self.nodes[0].port:
                await node.connect(self.nodes[0])

        await self._wait_for_connections()

        for node in self.nodes:
            if node.port != self.nodes[5].port:
                await node.connect(self.nodes[5])

        await self._wait_for_connections()

        edges = self.nodes[0].edges.copy()
        for i, edge in enumerate(edges):
            await self.nodes[0].close_connection(edge)
            await self._wait_for_connections()
            assert len(self.nodes[0].edges) == 4 - i, "Node 0 connections failed"

        await self._wait_for_connections()

        for i in range(1, 5):
            assert len(self.nodes[i].edges) == 1, f"Node {i} connections failed"

        assert len(self.nodes[5].edges) == 4, "Node 5 connections failed"

    @pytest.mark.asyncio
    async def test_edges_client_orphan(self) -> None:
        """
        Validate handling of orphaned client connections.

        This test verifies that when client nodes initiate disconnection,
        both the client and server sides properly update their connection states
        and handle the orphaned connection scenario correctly.

        Test procedure:
        1. Create 5 ChaskiNode instances
        2. Connect Nodes 1-4 to Node 0 (clients connecting to server)
        3. Verify initial connection states
        4. Have each client node close its connection to the server
        5. Verify all nodes detect the disconnections

        Raises:
            AssertionError: If any node fails to properly handle the disconnection
                           or if orphaned connections remain
        """
        self.nodes = await create_nodes(5, self.ip)

        for node in self.nodes[1:]:
            await node.connect(self.nodes[0])

        await self._wait_for_connections()

        assert len(self.nodes[0].edges) == 4, "Node 0 connections failed"

        for i, node in enumerate(self.nodes[1:], start=1):
            assert len(node.edges) == 1, f"Node {i} connections failed"

        for node in self.nodes[1:]:
            await node.close_connection(node.edges[0])

        await self._wait_for_connections()

        for i, node in enumerate(self.nodes):
            assert (
                len(node.edges) == 0
            ), f"Node {i} connections failed after orphan detection"

    @pytest.mark.asyncio
    async def test_edges_server_orphan(self) -> None:
        """
        Validate handling of orphaned server connections.

        This test verifies that when a server node initiates disconnection from
        its clients, both the server and all client nodes properly update their
        connection states and handle the orphaned connection scenario correctly.

        Test procedure:
        1. Create 5 ChaskiNode instances
        2. Connect Nodes 1-4 to Node 0 (clients connecting to server)
        3. Verify initial connection states
        4. Have the server node close all its connections to clients
        5. Verify all nodes detect the disconnections

        Raises:
            AssertionError: If any node fails to properly handle the disconnection
                           or if orphaned connections remain
        """
        self.nodes = await create_nodes(5, self.ip)
        for node in self.nodes[1:]:
            await node.connect(self.nodes[0])

        await self._wait_for_connections()

        assert len(self.nodes[0].edges) == 4, "Node 0 connections failed"
        for i, node in enumerate(self.nodes[1:], start=1):
            assert len(node.edges) == 1, f"Node {i} connections failed"

        edges = self.nodes[0].edges.copy()
        for edge in edges:
            await self.nodes[0].close_connection(edge)

        await self._wait_for_connections()

        for i, node in enumerate(self.nodes):
            assert (
                len(node.edges) == 0
            ), f"Node {i} connections failed after orphan detection"

    @pytest.mark.asyncio
    async def test_response_udp(self) -> None:
        """
        Validate UDP communication between connected ChaskiNodes.

        This test verifies that nodes can exchange UDP messages correctly,
        with the receiving node properly processing and responding to the
        request with identical data.

        Test procedure:
        1. Create 2 ChaskiNode instances
        2. Connect Node 1 to Node 0
        3. Send test data via UDP from Node 0 to Node 1
        4. Verify the response data exactly matches the sent data

        Raises:
            AssertionError: If the response data differs from the sent data,
                           indicating UDP communication problems
        """
        self.nodes = await create_nodes(2, self.ip)
        await self.nodes[1].connect(self.nodes[0])

        await self._wait_for_connections()

        dummy_data: Dict[str, str] = {
            self.nodes[0].uuid(): self.nodes[0].uuid(),
            self.nodes[0].uuid(): self.nodes[0].uuid(),
            self.nodes[0].uuid(): self.nodes[0].uuid(),
        }
        response_data = await self.nodes[0]._test_generic_request_udp(dummy_data)
        assert dummy_data == response_data, "Mismatch between sent and received data"


@pytest.mark.asyncio
class Test_Connections_for_IPv4(_TestConnections):
    """
    Concrete test class for validating ChaskiNode connections over IPv4.

    This class extends the abstract _TestConnections class to provide specific
    tests for IPv4 networking. It runs all the connection tests defined in the
    parent class using the IPv4 loopback address (127.0.0.1).

    Attributes:
        ip: The IPv4 loopback address used for test connections
        nodes: List to store ChaskiNode instances created during tests
    """

    ip: str = "127.0.0.1"
    nodes: List[ChaskiNode] = []

    @pytest_asyncio.fixture(autouse=True)
    async def cleanup(self) -> None:
        """
        Fixture to automatically clean up node resources after each test.

        This fixture ensures all ChaskiNode instances created during a test are
        properly stopped and resources released before the next test runs.
        """
        yield
        for node in self.nodes:
            await node.stop()
        await self._wait_for_connections()


@pytest.mark.asyncio
class Test_Connections_for_IPv6(_TestConnections):
    """
    Concrete test class for validating ChaskiNode connections over IPv6.

    This class extends the abstract _TestConnections class to provide specific
    tests for IPv6 networking. It runs all the connection tests defined in the
    parent class using the IPv6 loopback address (::1).

    Attributes:
        ip: The IPv6 loopback address used for test connections
        nodes: List to store ChaskiNode instances created during tests
    """

    ip: str = "::1"
    nodes: List[ChaskiNode] = []

    @pytest_asyncio.fixture(autouse=True)
    async def cleanup(self) -> None:
        """
        Fixture to automatically clean up node resources after each test.

        This fixture ensures all ChaskiNode instances created during a test are
        properly stopped and resources released before the next test runs.
        """
        yield
        for node in self.nodes:
            await node.stop()
        await self._wait_for_connections()
