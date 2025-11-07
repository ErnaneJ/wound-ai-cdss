from celery import Celery
import os

celery_app = Celery(
    'worker',
    broker='redis://redis:6379/0',  # URL direta
    backend='redis://redis:6379/0',  # URL direta
    include=['app.tasks']
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='America/Sao_Paulo',
    enable_utc=True,
    task_routes={
        'app.tasks.*': {'queue': 'celery'}
    }
)