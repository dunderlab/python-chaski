"""
===============================
Test Celery Task Functionality
===============================

This module contains pytest tests for Celery tasks integration.
It verifies that basic Celery task execution works correctly.
"""

import os
import subprocess
import time
import sys
import asyncio
import pytest
import pytest_asyncio

# Ensure the tasks directory is in the Python path


@pytest.fixture(scope="class")
def setup_celery(request):
    path = os.path.abspath(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    env = os.environ.copy()
    env["PYTHONPATH"] = ":".join(sys.path + [path])

    # Asegurarse que la carpeta test está en el path para que Celery pueda encontrar el módulo tasks
    if path not in sys.path:
        sys.path.append(path)

    process = subprocess.Popen(
        ["celery", "-A", "tasks", "worker", "--loglevel=info"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        cwd=os.path.join(path, "test", "tasks"),  # Ejecutar desde el directorio tasks
    )
    time.sleep(5)

    if process.poll() is not None:
        out, err = process.communicate()
        print(">>> CELERY WORKER CRASH DETECTED")
        print("STDOUT:\n", out)
        print("STDERR:\n", err)
        raise RuntimeError("Celery worker died unexpectedly")

    request.cls.celery_process = process

    yield

    if process:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


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
@pytest.mark.usefixtures("setup_celery")
@pytest.mark.usefixtures("setup_streamer_root")
class TestCelery:
    """
    Test class for verifying Celery task functionality.

    This test class uses pytest.mark.asyncio to facilitate
    asynchronous tests for Celery tasks.
    """

    async def test_task(self):
        """
        Test basic Celery task execution.

        This test verifies that a simple addition task can be executed
        through Celery and returns the expected result.

        Steps:
        1. Import the 'add' task from the tasks module
        2. Call the task asynchronously using delay()
        3. Wait for the result with a timeout
        4. Verify the result matches the expected sum

        Raises
        ------
        AssertionError
            If the task result doesn't match the expected value
        """

        # Asegurarse que la carpeta de tasks está en el path
        path = os.path.abspath(
            os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        )
        tasks_path = os.path.join(path, "test", "tasks")
        if tasks_path not in sys.path:
            sys.path.append(tasks_path)

        # Importar la aplicación Celery y la tarea
        from tasks.tasks import app, add

        # Esperar un momento para asegurar que el worker esté listo
        await asyncio.sleep(2)

        # Ejecutar la tarea
        result = add.delay(5, 6)
        resultado = result.get(timeout=10)
        assert resultado == 11, "The add task should return the sum of its arguments"
