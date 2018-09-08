from celery import Celery

def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL']
    )
    class ContextTask(celery.Task):
        abstract = True
        def __call__(self, *args, **kwarg):
            with app.app_context():
                return self.run(*args, **kwarg)
    celery.Task = ContextTask
    return celery
