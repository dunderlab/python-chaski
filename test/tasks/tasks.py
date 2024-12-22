import sys
import os
from celery import Celery

sys.path.append('../../')
from chaski.utils import transport
from chaski.utils import backend

# Initialize the Celery application for task management
app = Celery(
    'test',
    broker=os.getenv("CHASKI_CELERY_BROKER", 'chaski://127.0.0.1:65433'),
    backend=os.getenv("CHASKI_CELERY_BACKEND", 'chaski://127.0.0.1:65433'),
)


# Define a task to add two numbers
@app.task
def add(x, y):
    return x + y
