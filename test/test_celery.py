import os
import subprocess
import time
import sys
import pytest
from chaski.scripts import terminate_connections
import signal

import psutil
import os


@pytest.fixture(scope="class")
def setup_celery(request):
    path = os.path.abspath(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    env = os.environ.copy()
    env["PYTHONPATH"] = ":".join(sys.path + [path])

    process_celery = subprocess.Popen(
        ["celery", "-A", "test.celery_tasks.tasks", "worker"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        cwd=path,
    )
    time.sleep(5)

    if process_celery.poll() is not None:
        out, err = process_celery.communicate()
        print(">>> CELERY WORKER CRASH DETECTED")
        print("STDOUT:\n", out)
        print("STDERR:\n", err)
        raise RuntimeError("Celery worker died unexpectedly")

    request.cls.celery_process = process_celery

    # yield

    # if process_celery:
    #     process_celery.terminate()
    #     try:
    #         process_celery.wait(timeout=5)
    #     except subprocess.TimeoutExpired:
    #         process_celery.kill()


@pytest.fixture(scope="class")
def setup_streamer_root(request):
    path = os.path.abspath(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    env = os.environ.copy()
    env["PYTHONPATH"] = ":".join(sys.path + [path])

    process_streamer = subprocess.Popen(
        [sys.executable, f"{path}/chaski/scripts/streamer_root.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    time.sleep(1)

    if process_streamer.poll() is not None:
        out, err = process_streamer.communicate()
        print(">>> CRASH DETECTED")
        print("STDOUT:\n", out)
        print("STDERR:\n", err)
        raise RuntimeError("streamer_root.py died unexpectedly")

    request.cls.streamer_process = process_streamer

    # yield

    # if process_streamer:
    #     process_streamer.terminate()
    #     try:
    #         process_streamer.wait(timeout=5)
    #     except subprocess.TimeoutExpired:
    #         process_streamer.kill()


#
# @pytest.fixture(scope="session", autouse=True)
# def cleanup_processes(request):
#     """
#     Fixture global para limpiar y terminar todos los procesos al finalizar las pruebas.
#     """
#     # yield
#
#     print("\n>>> Iniciando limpieza final de procesos")
#
#     def cleanup_instance(instance):
#
#         # 2. Luego terminamos el proceso del streamer
#         if hasattr(instance, "streamer_process"):
#             # cleanup_celery_process_and_children(instance.streamer_process)
#             terminate_connections.close_connections(
#                 instance.streamer_process.pid, signal=signal.SIGKILL
#             )
#             try:
#                 instance.streamer_process.terminate()
#                 instance.streamer_process.wait(timeout=5)
#             except Exception as e:
#                 print(f"Error al terminar proceso streamer: {e}")
#                 try:
#                     instance.streamer_process.kill()
#                 except:
#                     pass
#
#         # 3. Finalmente cerramos Celery
#         if hasattr(instance, "celery_process"):
#             # hard_cleanup_celery(instance.celery_process)
#             terminate_connections.close_connections(
#                 instance.celery_process.pid, signal=signal.SIGKILL
#             )
#
#             try:
#                 instance.celery_process.terminate()
#                 instance.celery_process.wait(timeout=5)
#             except Exception as e:
#                 print(f"Error al cerrar Celery: {e}")
#                 try:
#                     instance.celery_process.kill()
#                 except:
#                     pass
#
#     # Limpiar todas las instancias
#     for item in request.node.items:
#         if hasattr(item, "instance"):
#             cleanup_instance(item.instance)
#
#     print(">>> Limpieza final completada")
#     # print_celery_processes()
#     # cleanup_all_celery_procs()


@pytest.mark.usefixtures("setup_celery")
@pytest.mark.usefixtures("setup_streamer_root")
class TestCelery:

    def setup_method(self):
        """Setup method that runs before each test method"""
        path = os.path.abspath(
            os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        )
        self.tasks_path = os.path.join(path, "test")
        if self.tasks_path not in sys.path:
            sys.path.append(self.tasks_path)

        # Importamos las dependencias una vez
        from celery_tasks.tasks import app, add

        self.app = app
        self.add = add

    def test_task(self):
        result = self.add.delay(5, 6)
        result_value = result.get(timeout=10)
        assert result_value == 11, "The add task should return the sum of its arguments"

    # def test_task_app(self):
    #     result = self.app.send_task("sub", args=[7, 3])
    #     result_value = result.get(timeout=10)
    #     assert result_value == 4, "The add task should return the sum of its arguments"
