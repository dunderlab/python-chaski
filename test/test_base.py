from typing import Optional
from chaski.node import ChaskiNode


class TestBase:

    async def asyncTearDown(self):
        for node in self.nodes:
            print(f"Closing node {node.port}")
            await node.stop()

    def assertConnection(
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
        return self.assertTrue(conn, msg)

    def assertNoConnection(
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
        return self.assertFalse(conn, msg)
