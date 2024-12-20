import os

env = {
    'STREAMER_ROOT': '127.0.0.1:65433',
    'CERTIFICATE_AUTHORITY': '127.0.0.1:65432',
    'REMOTE_PROXY': '127.0.0.1:65434',
    'CELERY_BACKEND': 'chaski://127.0.0.1:65433',
    'CELERY_BROKER': 'chaski://127.0.0.1:65433',
}

for key in env:
    os.environ[f'CHASKI_{key}'] = env[key]
