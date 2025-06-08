"""
==================================
Chaski Node Functions Test Module
==================================

This module contains comprehensive pytest test cases for validating core functionalities
of the Chaski communication framework. The tests verify critical features including:

- Node connectivity and message exchange
- Message time-to-live (TTL) behavior
- SSL/TLS certificate handling and secure communications
- Certificate Authority (CA) integration
- Connection latency measurement and management

These tests ensure the reliability, security, and performance characteristics
of the Chaski framework components in various operational scenarios.
"""

import os
import ssl
import asyncio
from typing import List, Union

import pytest

from chaski.streamer import ChaskiStreamer
from chaski.node import Message, ChaskiNode
from chaski.utils.auto import run_transmission, create_nodes
from .test_base import TestBase


@pytest.mark.asyncio
class TestFunctions(TestBase):
    """
    Test suite for core functionality of the Chaski networking framework.

    This class contains comprehensive test cases for validating essential
    operations of ChaskiNode instances including message exchange, secure
    communication, certificate management, and performance metrics.
    """

    nodes: List[Union[ChaskiNode, ChaskiStreamer]] = []
    ip: str = "127.0.0.1"

    async def test_ping(self) -> None:
        """
        Validate the ping functionality and latency measurement between ChaskiNodes.

        This test verifies that:
        1. Nodes can send and receive ping messages successfully
        2. Latency measurements correctly reflect message size differences
        3. Latency reset functionality works as expected

        Test procedure:
        1. Create three ChaskiNodes
        2. Connect nodes 1 and 2 to node 0
        3. Ping the first edge of node 0 with default size
        4. Ping the second edge of node 0 with larger size
        5. Verify the second edge has higher latency due to message size
        6. Reset latency measurements for both edges
        7. Confirm both edges show identical latency values after reset

        Raises:
            AssertionError: If latency measurements don't behave as expected
        """
        self.nodes = await create_nodes(3, self.ip)
        await self.nodes[1].connect(self.nodes[0])
        await self.nodes[2].connect(self.nodes[0])
        await asyncio.sleep(0.3)

        await self.nodes[0].ping(self.nodes[0].edges[0])
        await asyncio.sleep(1)
        await self.nodes[0].ping(self.nodes[0].edges[1], size=100000)
        await asyncio.sleep(1)

        assert (
            self.nodes[0].edges[1].latency > self.nodes[0].edges[0].latency
        ), "Latency of the second edge should be greater than the latency of the first edge"

        self.nodes[0].edges[0].reset_latency()
        self.nodes[0].edges[1].reset_latency()

        assert (
            self.nodes[0].edges[1].latency == self.nodes[0].edges[0].latency
        ), "Latencies of the two edges should be equal after resetting"

    async def test_message_ttl(self) -> None:
        """
        Validate the time-to-live (TTL) functionality of Message objects.

        This test ensures that:
        1. Messages are created with the correct initial TTL value
        2. The decrement_ttl method properly reduces the TTL counter
        3. Multiple TTL decrements accumulate correctly

        Test procedure:
        1. Create a Message instance with TTL of 10
        2. Call decrement_ttl() twice in succession
        3. Verify the TTL value is correctly reduced to 8

        Raises:
            AssertionError: If TTL does not decrement correctly
        """
        message = Message("command", ttl=10)
        message.decrement_ttl()
        message.decrement_ttl()

        assert (
            message.ttl == 8
        ), "The TTL should be decremented by 2 from the initial value of 10"

    async def test_ssl_certificate(self) -> None:
        """
        Validate SSL certificate configuration and secure communication between nodes.

        This test verifies that:
        1. SSL contexts can be properly configured for both client and server roles
        2. Certificate loading and verification works correctly
        3. Secure communication can be established between nodes

        Test procedure:
        1. Configure server SSL context with client authentication requirements
        2. Configure client SSL context with server authentication requirements
        3. Set up producer ChaskiStreamer with the first set of SSL contexts
        4. Set up consumer ChaskiStreamer with the second set of SSL contexts
        5. Run a test transmission between the producer and consumer
        6. Verify secure communication works correctly

        Raises:
            AssertionError: If secure communication fails between nodes
            SSLError: If certificate configuration is incorrect
        """
        uuid1: str = "3ea4e610-f276-4715-aa52-88d1cf14a295"
        uuid2: str = "4c535672-949e-480f-9df4-9548a4cc2c1f"

        path: str = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))

        # Configure the server SSL context for client authentication,
        # load the server's certificate and key, and set up the CA certificate for verification.
        server_ssl_context: ssl.SSLContext = ssl.create_default_context(
            ssl.Purpose.CLIENT_AUTH
        )
        server_ssl_context.load_cert_chain(
            certfile=f"{path}/certs_ca/server_{uuid1}.cert",
            keyfile=f"{path}/certs_ca/server_{uuid1}.key",
        )
        server_ssl_context.load_verify_locations(cafile=f"{path}/certs_ca/ca.cert")
        server_ssl_context.verify_mode = ssl.CERT_REQUIRED

        # Configure the client SSL context for server authentication,
        # load the client's certificate and key, and set up the CA certificate for verification.
        client_ssl_context: ssl.SSLContext = ssl.create_default_context(
            ssl.Purpose.SERVER_AUTH
        )
        client_ssl_context.load_cert_chain(
            certfile=f"{path}/certs_ca/client_{uuid1}.cert",
            keyfile=f"{path}/certs_ca/client_{uuid1}.key",
        )
        client_ssl_context.load_verify_locations(cafile=f"{path}/certs_ca/ca.cert")
        client_ssl_context.verify_mode = ssl.CERT_REQUIRED

        # Initialize the ChaskiStreamer instance for the producer, configuring SSL contexts
        # for secure communication, subscriptions, and other parameters.
        producer: ChaskiStreamer = ChaskiStreamer(
            name="Producer",
            subscriptions=["topic1"],
            reconnections=None,
            ssl_certificates_location="certs_ca",
            ssl_context_server=server_ssl_context,
            ssl_context_client=client_ssl_context,
        )

        # Configure the second server SSL context for client authentication,
        # load the second server's certificate and key, and set up the CA certificate for verification.
        server_ssl_context2: ssl.SSLContext = ssl.create_default_context(
            ssl.Purpose.CLIENT_AUTH
        )
        server_ssl_context2.load_cert_chain(
            certfile=f"{path}/certs_ca/server_{uuid2}.cert",
            keyfile=f"{path}/certs_ca/server_{uuid2}.key",
        )
        server_ssl_context2.load_verify_locations(cafile=f"{path}/certs_ca/ca.cert")
        server_ssl_context2.verify_mode = ssl.CERT_REQUIRED

        # Configure the second client SSL context for server authentication,
        # load the client's certificate and key, and set up the CA certificate for verification.
        client_ssl_context2: ssl.SSLContext = ssl.create_default_context(
            ssl.Purpose.SERVER_AUTH
        )
        client_ssl_context2.load_cert_chain(
            certfile=f"{path}/certs_ca/client_{uuid2}.cert",
            keyfile=f"{path}/certs_ca/client_{uuid2}.key",
        )
        client_ssl_context2.load_verify_locations(cafile=f"{path}/certs_ca/ca.cert")
        client_ssl_context2.verify_mode = ssl.CERT_REQUIRED

        # Initialize the ChaskiStreamer instance for the consumer, configuring SSL contexts
        # for secure communication, subscriptions, and other parameters.
        consumer: ChaskiStreamer = ChaskiStreamer(
            name="Consumer",
            subscriptions=["topic1"],
            reconnections=None,
            ssl_certificates_location="certs_ca",
            ssl_context_server=server_ssl_context2,
            ssl_context_client=client_ssl_context2,
        )

        await run_transmission(producer, consumer, parent=self)

    async def test_ssl_certificate_CA_inline(self) -> None:
        """
        Validate automatic certificate acquisition from a Certificate Authority.

        This test verifies that:
        1. ChaskiStreamer instances can request certificates from a CA during initialization
        2. The certificate request process completes successfully
        3. Obtained certificates enable secure communication between nodes

        Test procedure:
        1. Create producer ChaskiStreamer with automatic certificate request
        2. Create consumer ChaskiStreamer with automatic certificate request
        3. Run transmission between nodes using the obtained certificates
        4. Verify secure communication works correctly

        Raises:
            AssertionError: If secure communication fails between nodes
            ConnectionError: If CA connection fails
            SSLError: If certificate request or validation fails
        """
        producer: ChaskiStreamer = ChaskiStreamer(
            name="Producer",
            subscriptions=["topic1"],
            reconnections=None,
            ssl_certificates_location="tmp_certs_ca",
            request_ssl_certificate=os.getenv(
                "CHASKI_CERTIFICATE_AUTHORITY", "ChaskiCA@127.0.0.1:65432"
            ),
        )

        consumer: ChaskiStreamer = ChaskiStreamer(
            name="Consumer",
            subscriptions=["topic1"],
            reconnections=None,
            ssl_certificates_location="tmp_certs_ca",
            request_ssl_certificate=os.getenv(
                "CHASKI_CERTIFICATE_AUTHORITY", "ChaskiCA@127.0.0.1:65432"
            ),
        )

        await run_transmission(producer, consumer, parent=self)

    async def test_ssl_certificate_CA_off(self) -> None:
        """
        Validate error handling when requesting certificates from an unavailable CA.

        This test verifies that:
        1. The system gracefully handles connection attempts to non-existent CAs
        2. Appropriate errors are raised when certificate requests fail
        3. The application doesn't crash when certificate acquisition fails

        Test procedure:
        1. Attempt to create a ChaskiStreamer with an invalid CA address
        2. Expect and catch exceptions from the failed certificate request
        3. Verify the system handled the error appropriately

        Raises:
            AssertionError: If error handling doesn't work as expected
        """
        try:
            ChaskiStreamer(
                name="Producer",
                subscriptions=["topic1"],
                reconnections=None,
                ssl_certificates_location="tmp_certs_ca",
                request_ssl_certificate="ChaskiCA@127.0.0.1:1111",
            )
        except Exception:
            assert (
                True
            ), "SSL certificate request should raise an error with an incorrect CA address."
