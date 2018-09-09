from celery.schedules import crontab

SECRET_KEY = 'KnMzoQ7JA3WwtLQlFOKR68Km3WA3MzC8'
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ECHO = False
CELERY_ENABLE_UTC = False
CELERY_TIMEZONE = 'Asia/Tokyo'
CELERYBEAT_SCHEDULE={
    'destroy-performlogs': {
        'task': 'flaskr.workers.performlogs.destroy_performlogs',
        'schedule': crontab(hour=1, minute=0)
    },
    'destroy-worklogs': {
        'task': 'flaskr.workers.worklogs.destroy_worklogs',
        'schedule': crontab(hour=2, minute=0)
    }
}
