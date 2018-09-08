from flask import Blueprint, render_template, redirect, request, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, EqualTo
from flaskr import db, lm, cache
from flaskr.models import User

bp = Blueprint('auth', __name__, url_prefix="/auth")

@lm.user_loader
def load_user(id):
    return User.query.get(id)

class LoginForm(FlaskForm):
    userid = StringField('ユーザID')
    password = PasswordField('パスワード')

class PasswordChangeForm(FlaskForm):
    password = PasswordField('パスワード', validators=[
            DataRequired(message='必須入力です'),
            EqualTo('confirm', message='パスワードが一致しません')
        ])
    confirm = PasswordField('パスワード再入力')

@bp.route('/login',methods=['GET','POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user, checked = User.auth(form.userid.data, form.password.data)
        if checked:
            login_user(user)
            return redirect(request.args.get("next") or url_for("index"))
        flash('ユーザIDまたはパスワードが違います', 'danger')
        return render_template('auth/login.pug', form=form), 401
    return render_template('auth/login.pug', form=form)

@bp.route('/logout')
def logout():
    cache.set('person.id', None)
    cache.set('person.idm', None)
    logout_user()
    return redirect(url_for('index'))


@bp.route('/passwd',methods=['GET','POST'])
@login_required
def passwd():
    form = PasswordChangeForm()
    if form.validate_on_submit():
        user = current_user
        user.set_password(form.password.data)
        db.session.add(user)
        try:
            db.session.commit()
            flash('パスワードの変更が完了しました', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash('パスワードの変更が失敗しました "{}"'.format(e), 'danger')
    return render_template('auth/edit.pug', form=form)
