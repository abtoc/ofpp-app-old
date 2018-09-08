from flask import Blueprint
from flask_login import login_required
from flask import render_template, redirect, flash, abort, url_for
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, EqualTo
from flaskr import db
from flaskr.models import User
from flaskr.utils.validators import Unique

bp = Blueprint('users', __name__, url_prefix="/users")

class UsersNewForm(FlaskForm):
    userid = StringField('ログインユーザID', validators=[
        DataRequired(message='必須入力です'),
        Unique(User, User.userid, message='同一ユーザIDが指定されいています')
    ])
    password = PasswordField('パスワード', validators=[
        DataRequired(message='必須入力です'),
        EqualTo('confirm', message='パスワードが一致しません')
    ])
    confirm = PasswordField('パスワード再入力')

class UsersPasswordForm(FlaskForm):
    password = PasswordField('パスワード', validators=[
        DataRequired(message='必須入力です'),
        EqualTo('confirm', message='パスワードが一致しません')
    ])
    confirm = PasswordField('パスワード再入力')

@bp.route('/')
@login_required
def index():
    users = User.query.all()
    return render_template('users/index.pug', users=users)

@bp.route('/create', methods=('GET','POST'))
@login_required
def create():
    form = UsersNewForm()
    if form.validate_on_submit():
        user = User()
        user.populate_form(form)
        user.set_password(form.password.data)
        db.session.add(user)
        try:
            db.session.commit()
            flash('ユーザを追加しました', 'success')
            return redirect(url_for('users.index'))
        except Exception as e:
            db.session.rollback()
            flash('ユーザ追加時にエラーが発生しました "{}"'.format(e), 'danger')
    return render_template('users/edit.pug', form=form)

@bp.route('/<id>/destroy', methods=('GET','POST'))
@login_required
def destroy(id):
    user = User.query.get(id)
    if user is None:
        abort(404)
    db.session.delete(user)
    try:
        db.session.commit()
        flash('ユーザを削除しました', 'success')
    except Exception as e:
        db.session.rollback()
        flash('ユーザ削除時にエラーが発生しました "{}"'.format(e), 'danger')
    return redirect(url_for('users.index'))