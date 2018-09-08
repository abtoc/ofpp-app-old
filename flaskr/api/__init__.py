from flaskr import app, auth
from flaskr.models import User

@auth.verify_password
def verify_pw(username,password):
    user, checked = User.auth(username,password)
    return checked

from flaskr.api import idm
app.register_blueprint(idm.bp)
