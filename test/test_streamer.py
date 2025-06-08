"""
==================================
ChaskiStreamer Testing Module
==================================

This module contains comprehensive test cases for the ChaskiStreamer class,
which implements communication and file transfer capabilities in the Chaski system.
The tests validate core functionalities such as:

- Basic message streaming between nodes
- File transfer capabilities with integrity verification
- Disabled file transfer behavior
- Chained streaming across multiple nodes
- Integration with root node for centralized communication

The test suite uses pytest-asyncio for asynchronous test execution and includes
fixtures for setup and teardown of streamer instances and root processes.
"""

import os
import sys
import time
import asyncio
import subprocess
from typing import List, Any

import pytest
import pytest_asyncio

from chaski.streamer import ChaskiStreamer
from chaski.utils.auto import run_transmission


@pytest.fixture(scope="class")
def setup_streamer_root(request: pytest.FixtureRequest) -> None:
    """
    Fixture to set up and manage a streamer root process for the test class.

    This fixture:
    1. Starts a subprocess running the streamer_root.py script
    2. Configures the environment to include the project path
    3. Ensures the process is properly terminated after tests complete
    4. Verifies the process starts correctly and doesn't crash

    Args:
        request: The pytest fixture request object to access the test class

    Raises:
        RuntimeError: If the streamer_root.py process crashes on startup
    """
    path = os.path.abspath(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    env = os.environ.copy()
    env["PYTHONPATH"] = ":".join(sys.path + [path])

    process = subprocess.Popen(
        [sys.executable, f"{path}/chaski/scripts/streamer_root.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    time.sleep(1)

    if process.poll() is not None:
        out, err = process.communicate()
        print(">>> CRASH DETECTED")
        print("STDOUT:\n", out)
        print("STDERR:\n", err)
        raise RuntimeError("streamer_root.py died unexpectedly")

    request.cls.streamer_process = process

    yield

    if process:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


@pytest.mark.asyncio
@pytest.mark.usefixtures("setup_streamer_root")
class TestStreamer:
    """
    Test suite for ChaskiStreamer functionality.

    This class contains test cases for validating the various features of
    the ChaskiStreamer class, including messaging, file transfers, and
    node chaining. It uses the setup_streamer_root fixture to ensure
    a root streamer process is available for tests that require it.
    """

    nodes: List[ChaskiStreamer] = []

    @pytest_asyncio.fixture(autouse=True)
    async def cleanup(self) -> None:
        """
        Fixture to clean up streamer nodes after each test.

        This fixture ensures all streamer nodes created during a test
        are properly stopped, preventing resource leaks between tests.
        """
        yield
        for node in self.nodes:
            await node.stop()

    async def test_stream(self) -> None:
        """
        Test basic streaming functionality between producer and consumer.

        This test:
        1. Creates producer and consumer streamers with matching subscriptions
        2. Runs a standard transmission between them using the run_transmission utility
        3. Verifies the communication works properly
        """
        producer = ChaskiStreamer(
            name="Producer",
            subscriptions=["topic1"],
            reconnections=None,
        )

        consumer = ChaskiStreamer(
            name="Consumer",
            subscriptions=["topic1"],
            reconnections=None,
        )

        await run_transmission(producer, consumer, parent=self)

    async def test_file_transfer(self) -> None:
        """
        Test file transfer capabilities between ChaskiStreamer instances.

        This test:
        1. Creates producer and consumer with file handling capabilities
        2. Transfers files of various sizes (1KB to 10MB)
        3. Verifies file integrity by checking size and hash
        4. Ensures files are properly received and saved

        The test uses a callback to validate each received file matches
        its expected size and hash.
        """

        def new_file_event(**kwargs: Any) -> None:
            """
            Callback to verify received file integrity.

            Args:
                **kwargs: Dictionary containing file metadata including:
                    - data: Custom data sent with the file
                    - size: File size in bytes
                    - filename: Name of the received file
                    - destination_folder: Folder where file was saved
                    - hash: Expected file hash

            Raises:
                AssertionError: If file size or hash doesn't match expectations
            """
            size = kwargs["data"]["size"]
            assert (
                size == kwargs["size"]
            ), f"File {kwargs['filename']} no match size of {kwargs['filename'][6:-5]}"

            hash = ChaskiStreamer.get_hash(
                os.path.join(
                    kwargs["destination_folder"],
                    kwargs["filename"],
                )
            )
            assert (
                hash == kwargs["hash"]
            ), "The hash of the received file does not match the expected hash."

        cwd = os.path.dirname(os.path.realpath(__file__))

        producer = ChaskiStreamer(
            name="Producer",
            subscriptions=["topicF"],
            reconnections=None,
            allow_incoming_files=True,
            file_handling_callback=new_file_event,
            destination_folder=os.path.join(cwd, "file_transfer", "output"),
        )

        consumer = ChaskiStreamer(
            name="Consumer",
            subscriptions=["topicF"],
            reconnections=None,
            allow_incoming_files=True,
            file_handling_callback=new_file_event,
            destination_folder=os.path.join(cwd, "file_transfer", "output"),
        )

        await asyncio.sleep(0.3)
        await producer.connect(consumer)
        await asyncio.sleep(0.3)

        for filename, size in [
            ("dummy_1KB.data", 1e3),
            ("dummy_10KB.data", 10e3),
            ("dummy_100KB.data", 100e3),
            ("dummy_1MB.data", 1e6),
            ("dummy_10MB.data", 10e6),
        ]:
            if os.path.exists(os.path.join(cwd, "file_transfer", "output", filename)):
                os.remove(os.path.join(cwd, "file_transfer", "output", filename))

            with open(
                os.path.join(cwd, "file_transfer", "input", filename), "rb"
            ) as file:
                await producer.push_file(
                    "topicF",
                    file,
                    data={"size": size},
                )

        await asyncio.sleep(1)
        await consumer.stop()
        await producer.stop()

    async def test_file_disable_transfer(self) -> None:
        """
        Test file transfer rejection when a node has file transfers disabled.

        This test:
        1. Creates a producer with file transfer enabled
        2. Creates a consumer with file transfer disabled
        3. Attempts to transfer a file between them
        4. Verifies the file is not received by the consumer

        The test confirms the security feature that prevents file transfers
        when a node has explicitly disabled this capability.
        """
        cwd = os.path.dirname(os.path.realpath(__file__))

        producer = ChaskiStreamer(
            name="Producer",
            subscriptions=["topicF"],
            reconnections=None,
            allow_incoming_files=True,
            destination_folder=os.path.join(cwd, "file_transfer", "output"),
        )

        consumer = ChaskiStreamer(
            name="Consumer",
            subscriptions=["topicF"],
            reconnections=None,
            allow_incoming_files=False,
            destination_folder=os.path.join(cwd, "file_transfer", "output"),
        )

        await asyncio.sleep(0.3)
        await producer.connect(consumer.address)
        await asyncio.sleep(0.3)

        filename = "dummy_1KB.data"
        output_path = os.path.join(cwd, "file_transfer", "output", filename)

        if os.path.exists(output_path):
            os.remove(output_path)

        with open(os.path.join(cwd, "file_transfer", "input", filename), "rb") as file:
            await producer.push_file("topicF", file)

        await asyncio.sleep(0.5)
        assert not os.path.exists(
            output_path
        ), "File transfer should fail as consumer has file transfer disabled"

        await asyncio.sleep(1)
        await consumer.stop()
        await producer.stop()

    async def test_stream_chain(self) -> None:
        """
        Test message propagation through a chain of connected streamers.

        This test:
        1. Creates a chain of 6 streamer instances
        2. Connects them sequentially (0->1->2->3->4->5)
        3. Sends messages from the first node
        4. Verifies messages propagate through the chain to the last node
        5. Tests bidirectional communication by triggering additional messages

        The test confirms messages flow correctly through a multi-node network
        and validates the streaming context manager pattern.
        """
        chains = [
            ChaskiStreamer(
                name=f"Producer{i}",
                subscriptions=["topic1"],
                reconnections=None,
            )
            for i in range(6)
        ]

        await asyncio.sleep(0.3)
        for i in range(5):
            await chains[i].connect(chains[i + 1].address)

        await asyncio.sleep(0.3)
        await chains[0].push("topic1", {"data": "test0"})

        count = 0
        async with chains[5] as message_queue:
            async for incoming_message in message_queue:
                assert incoming_message.data["data"] == f"test{count}"

                if count >= 5:
                    chains[5].terminate_stream()
                    break

                count += 1
                await chains[0].push("topic1", {"data": f"test{count}"})

        await asyncio.sleep(1)
        for chain in chains:
            await chain.stop()

    async def test_root_node(self) -> None:
        """
        Test integration with a root node for centralized communication.

        This test:
        1. Creates a root node and two regular streamers
        2. Connects the regular streamers to the root node
        3. Tests message propagation between streamers via the root
        4. Verifies the root can also publish messages to subscribed nodes

        The test confirms the root node properly routes messages to appropriate
        subscribers and that the system functions in a centralized topology.
        """
        chain0 = ChaskiStreamer(
            name="Producer 1",
            root=True,
            paired=True,
            reconnections=None,
        )

        chain1 = ChaskiStreamer(
            name="Producer 2",
            subscriptions=["topic1"],
            reconnections=None,
        )

        chain2 = ChaskiStreamer(
            name="Producer 3",
            subscriptions=["topic1"],
            reconnections=None,
        )

        await asyncio.sleep(0.3)
        await chain1.connect(chain0.address)
        await chain2.connect(chain0.address)

        await asyncio.sleep(0.3)
        await chain1.push("topic1", {"data": "test0"})

        count = 0
        async with chain2 as message_queue:
            async for incoming_message in message_queue:
                assert incoming_message.data["data"] == f"test{count}"

                if count >= 5:
                    chain2.terminate_stream()
                    break

                count += 1
                await chain0.push("topic1", {"data": f"test{count}"})

        await asyncio.sleep(1)
        await chain1.stop()
        await chain2.stop()
        await chain0.stop()
