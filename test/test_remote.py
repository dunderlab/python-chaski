"""
===========================================================
TestRemote: Pytest Tests for `ChaskiRemote` Class Functionality
===========================================================

This module contains pytest tests for the `ChaskiRemote` class, which is part of the Chaski framework
for distributed systems.
"""

import os
import asyncio

import pytest
import numpy as np
import pytest_asyncio

from chaski.remote import ChaskiRemote


@pytest.mark.asyncio
class TestRemote:
    """
    A test class for testing the ChaskiRemote class functionality.

    This test class uses pytest.mark.asyncio to facilitate
    asynchronous tests. It covers different scenarios to ensure the
    ChaskiRemote class behaves as expected.
    """

    nodes = []

    @pytest_asyncio.fixture(autouse=True)
    async def cleanup(self):
        """Cleanup fixture to stop all nodes after each test"""
        yield
        for node in self.nodes:
            print(f"Closing node {node.port}")
            await node.stop()

    async def test_module_no_available_register(self):
        """
        Test absence of module registration.

        This test verifies that when a server is set up without any available
        modules, a client cannot access any unregistered module.

        Steps:
        1. Create a `ChaskiRemote` server with no available modules.
        2. Initialize the client and connect it to the server.
        3. Attempt to proxy the 'os' module on the client.
        4. Ensure that accessing attributes of the 'os' module raises an exception.

        Raises
        ------
        AssertionError
            If the client manages to access the module's attributes or
            if the connection steps fail.
        """
        server = ChaskiRemote(
            available=[],
            reconnections=None,
        )
        await asyncio.sleep(0.3)

        client = ChaskiRemote(
            reconnections=None,
        )
        await client.connect(server.address)
        await asyncio.sleep(0.3)

        os_remote = client.proxy("os")
        await asyncio.sleep(0.3)

        try:
            os_remote.name
            pytest.fail("bad, the module has access")
        except:
            assert True, "ok, the module has not access"

        await server.stop()
        await client.stop()

    async def test_module_register(self):
        """
        Test the registration and remote access of a specified module.

        This test method performs the following steps:
        1. Sets up a ChaskiRemote server with the 'os' module available for proxying.
        2. Connects a client to the server.
        3. Proxies the 'os' module on the client.
        4. Verifies that the 'os' module's 'listdir' method works correctly when called remotely.
        5. Confirms that the name attribute of the 'os' module matches between the client and server.

        Raises
        ------
        AssertionError
            If the proxied 'os' module's method call results do not match the expected values, or
            if any exceptions are encountered during the test steps.
        """
        server = ChaskiRemote(
            available=["os"],
            reconnections=None,
        )
        await asyncio.sleep(0.3)

        client = ChaskiRemote(
            reconnections=None,
        )
        await client.connect(server.address)
        await asyncio.sleep(0.3)

        os_remote = client.proxy("os")
        await asyncio.sleep(0.3)

        assert isinstance(os_remote.listdir("."), list)
        assert str(os_remote.name) == os.name

        await server.stop()
        await client.stop()

    async def test_secuential_calls(self):
        """
        Test multiple sequential calls to a remote module.

        This test verifies that multiple sequential calls to methods and
        attributes of a remote module work correctly and consistently.

        Steps:
        1. Create a server with the 'os' module available.
        2. Connect a client to the server.
        3. Make multiple sequential calls to the remote module.
        4. Verify each call returns the expected results.
        """
        server = ChaskiRemote(
            available=["os"],
            reconnections=None,
        )
        await asyncio.sleep(0.3)

        client = ChaskiRemote(
            reconnections=None,
        )
        await client.connect(server.address)
        await asyncio.sleep(0.3)

        os_remote = client.proxy("os")
        await asyncio.sleep(0.3)

        for _ in range(10):
            assert isinstance(os_remote.listdir("."), list)
            assert str(os_remote.name) == os.name
            assert os_remote.name._ == os.name

        await server.stop()
        await client.stop()

    async def test_numpy_calls(self):
        """
        Test remote access to numpy functionality.

        This test verifies that numpy functions, attributes and methods
        can be accessed and used correctly through the remote proxy.

        Steps:
        1. Create a server with the 'numpy' module available.
        2. Connect a client to the server.
        3. Proxy the numpy module and make various calls to its functions.
        4. Verify the return values match expectations.
        """
        server = ChaskiRemote(
            available=["numpy"],
            reconnections=None,
        )
        await asyncio.sleep(0.3)

        client = ChaskiRemote(
            reconnections=None,
        )
        await client.connect(server.address)
        await asyncio.sleep(0.3)

        np_remote = client.proxy("numpy")
        await asyncio.sleep(0.3)

        assert isinstance(np_remote.pi._, float)
        assert np_remote.random.normal(0, 1, size=(2, 2)).shape == (2, 2)
        assert np_remote.random.normal(0, 1, size=(4, 4)).shape == (4, 4)
        assert np.isclose(np_remote.pi._, 3.141592653589793)

        state = np_remote.random.get_state()
        seed = state[1][0]
        assert isinstance(seed, np.uint32)

        await server.stop()
        await client.stop()
