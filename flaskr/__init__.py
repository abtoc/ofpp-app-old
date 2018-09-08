from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_httpauth import HTTPBasicAuth
from werkzeug.contrib.cache import SimpleCache
from flaskr.workers import make_celery

app = Flask(__name__, instance_relative_config=True)
app.config.from_object('flaskr.config')
app.config.from_pyfile('config.py', silent=True)
app.jinja_env.add_extension('pypugjs.ext.jinja.PyPugJSExtension')

db = SQLAlchemy(app)

lm = LoginManager()
lm.init_app(app)
lm.login_view = 'auth.login'

auth = HTTPBasicAuth()

cache = SimpleCache()

celery = make_celery(app)
celery.conf.update(app.config)

import flaskr.models
import flaskr.views
import flaskr.api
import flaskr.reports
