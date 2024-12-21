import sys
import os
from celery import Celery

sys.path.append('../../')
from chaski.utils import transport
from chaski.utils import backend


# Configuración de la aplicación Celery
app = Celery(
    'test',
    broker=os.getenv("CHASKI_CELERY_BROKER", 'chaski://127.0.0.1:65433'),
    backend=os.getenv("CHASKI_CELERY_BACKEND", 'chaski://127.0.0.1:65433'),
)


# Definición de una tarea simple
@app.task
def add(x, y):
    return x + y
