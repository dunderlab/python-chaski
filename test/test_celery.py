import sys
import unittest

sys.path.append('tasks')


########################################################################
class TestCelery(unittest.IsolatedAsyncioTestCase):
    """Prueba unitaria para Celery con worker."""

    # ----------------------------------------------------------------------
    async def test_task(self):
        """"""
        from tasks import add

        result = add.delay(5, 6)
        resultado = result.get(timeout=10)
        self.assertEqual(resultado, 11)
