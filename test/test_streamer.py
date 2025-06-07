import subprocess
import pytest
import pytest_asyncio
import asyncio
import time
import os
import sys
from chaski.streamer import ChaskiStreamer
from chaski.utils.auto import run_transmission


@pytest.fixture(scope="class")
def setup_streamer_root(request):
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

    nodes = []

    @pytest_asyncio.fixture(autouse=True)
    async def cleanup(self):
        yield
        for node in self.nodes:
            await node.stop()

    async def test_stream(self):
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

    async def test_file_transfer(self):
        def new_file_event(**kwargs):
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
            # ("dummy_100MB.data", 100e6),
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

    async def test_file_disable_transfer(self):
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

    async def test_stream_chain(self):
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

    async def test_root_node(self):
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
