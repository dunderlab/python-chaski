import pytest
import pytest_asyncio
import asyncio
from chaski.node import ChaskiNode
from typing import Optional, List


class TestBase:
    """
    Base class for Chaski network testing.

    This class provides common utility methods and fixtures for testing ChaskiNode
    functionality, including connection assertion helpers and cleanup procedures.
    Test classes should inherit from this base class to leverage its utilities.

    Attributes:
        nodes: List of ChaskiNode instances created during tests
    """

    nodes: List[ChaskiNode] = []

    async def _wait_for_connections(self) -> None:
        """
        Helper method to wait for connections to stabilize.

        This method introduces multiple short delays to ensure that all
        connection operations have completed before continuing with test
        assertions. It's particularly important for tests involving
        multiple nodes where connection establishment might take longer.

        Returns:
            None
        """
        for i in range(10):
            await asyncio.sleep(0.3)

    @pytest_asyncio.fixture(autouse=True)
    async def cleanup(self) -> None:
        """
        Pytest fixture to automatically stop all ChaskiNode instances after each test.

        This fixture is executed after each test coroutine and ensures all
        created ChaskiNode instances are properly shut down and resources released.
        """
        yield
        for node in self.nodes:
            print(f"Closing node {node.port}")
            await node.stop()
        await asyncio.sleep(1)

    def assert_connection(
        self, node1: ChaskiNode, node2: ChaskiNode, msg: Optional[str] = None
    ) -> None:
        """
        Assert that two ChaskiNode instances are connected in both directions.

        Checks that both node1 is connected to node2 and vice versa. Raises an
        AssertionError with an optional message if the nodes are not bidirectionally
        connected.

        Args:
            node1 (ChaskiNode): First node to check.
            node2 (ChaskiNode): Second node to check.
            msg (Optional[str]): Assertion failure message.

        Raises:
            AssertionError: If the two nodes are not mutually connected.
        """
        conn: bool = node1.is_connected_to(node2) and node2.is_connected_to(node1)
        if not conn and msg is not None:
            pytest.fail(msg)
        assert conn

    def assert_no_connection(
        self, node1: ChaskiNode, node2: ChaskiNode, msg: Optional[str] = None
    ) -> None:
        """
        Assert that two ChaskiNode instances are not connected in either direction.

        Verifies that node1 and node2 do not have a mutual connection. If they
        are found to be connected, raises an AssertionError with an optional
        descriptive message.

        Args:
            node1 (ChaskiNode): First node to check.
            node2 (ChaskiNode): Second node to check.
            msg (Optional[str]): Assertion failure message.

        Raises:
            AssertionError: If the nodes are connected.
        """
        conn: bool = node1.is_connected_to(node2) and node2.is_connected_to(node1)
        if conn and msg is not None:
            pytest.fail(msg)
        assert not conn
