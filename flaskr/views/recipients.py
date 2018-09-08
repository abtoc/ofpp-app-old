from flask import Blueprint, render_template, redirect, url_for, flash, abort
from flask_login import login_required
from flask_wtf import FlaskForm
from wtforms import StringField, DateField
from wtforms.validators import DataRequired, Regexp, Optional
from flaskr import db
from flaskr.models import Recipient

bp = Blueprint('recipients', __name__, url_prefix='/recipients')

class RecipientForm(FlaskForm):
    number = StringField('受給者番号', validators=[Regexp(message='数字10桁で入力してください', regex='^[0-9]{10}$')])
    amount = StringField('契約支給量', validators=[DataRequired(message='入力必須です')])
    usestart = DateField('利用開始日', validators=[Optional()])
    supply_in = DateField('支給決定開始日', validators=[Optional()])
    supply_out = DateField('支給決定終了日', validators=[Optional()])
    apply_in = DateField('適用決定開始日', validators=[Optional()])
    apply_out = DateField('適用決定終了日', validators=[Optional()])

@bp.route('/')
@login_required
def index():
    recipients = Recipient.query.all()
    items = []
    for recipient in recipients:
        if not recipient.person.enabled:
            continue
        item = dict(
            id=recipient.person_id,
            enabled=recipient.person.enabled,
            name=recipient.person.get_display(),
            number=recipient.number if bool(recipient.number) else '',
            usestart=recipient.usestart if bool(recipient.usestart) else '',
            supply_in=recipient.supply_in if bool(recipient.supply_in) else '',
            supply_out=recipient.supply_out if bool(recipient.supply_out) else '',
            supply_over=recipient.is_supply_over(),
            apply_in=recipient.apply_in if bool(recipient.apply_in) else '',
            apply_out=recipient.apply_out if bool(recipient.apply_out) else '',
            apply_over=recipient.is_apply_over(),
            create_at=recipient.create_at.strftime('%Y/%m/%d %H:%M') if bool(recipient.create_at) else '',
            update_at=recipient.update_at.strftime('%Y/%m/%d %H:%M') if bool(recipient.update_at) else ''
        )
        items.append(item)
    return render_template('recipients/index.pug', items=items)

@bp.route('/<id>/edit', methods=('GET', 'POST'))
@login_required
def edit(id):
    recipient = Recipient.get(id)
    if recipient is None:
        abort(404)
    form = RecipientForm(obj=recipient)
    if form.validate_on_submit():
        recipient.populate_form(form)
        db.session.add(recipient)
        try:
            db.session.commit()
            flash('受給者証の更新ができました', 'success')
            return redirect(url_for('recipients.index'))
        except Exception as e:
            db.session.rollback()
            flash('受給者証更新時にエラーが発生しました "{}"'.format(e), 'danger')
    return render_template('recipients/edit.pug', id=id, name=recipient.person.get_display(), form=form)
