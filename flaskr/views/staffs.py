from flask import Blueprint, render_template, redirect, url_for, flash, abort
from flask_login import login_required
from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, DateField, HiddenField, SelectField, ValidationError
from wtforms.validators import DataRequired, Regexp, Optional
from sqlalchemy import func
from flaskr import app, db
from flaskr.models import Person, PerformLog, WorkLog, TimeRule
from flaskr.utils.validators import UniqueIDM

bp = Blueprint('staffs', __name__, url_prefix='/staffs')

class PersonForm(FlaskForm):
    id = HiddenField('id')
    name = StringField('名前', validators=[DataRequired(message='必須項目です')])
    display = StringField('表示名')
    idm = StringField('IDM', validators=[UniqueIDM(message='同一IDMが指定されています')])
    timerule_id = SelectField('タイムテーブル', render_kw={'class': 'form-control'})
    enabled = BooleanField('有効化', default='checked')
    def __init__(self, *args, **kwargs):
        super(PersonForm, self).__init__(*args, **kwargs)
        self.timerule_id.choices = [(tr.id, tr.caption) for tr in TimeRule.query.order_by(TimeRule.caption).all()]

@bp.route('/')
@login_required
def index():
    persons = Person.query.filter(Person.staff == True).order_by(Person.name.asc()).all()
    items = []
    for person in persons:
        timerule = TimeRule.get(person.timerule_id)
        item = dict(
            id=person.id,
            enabled=person.enabled,
            name=person.get_display(),
            idm=person.idm,
            timerule=timerule.caption if timerule is not None else '',
            create_at=person.create_at.strftime('%Y/%m/%d %H:%M') if person.create_at is not None else '',
            update_at=person.update_at.strftime('%Y/%m/%d %H:%M') if person.update_at is not None else ''
        )
        items.append(item)
    return render_template('staffs/index.pug', items=items)

@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    form = PersonForm()
    if form.validate_on_submit():
        person = Person()
        person.populate_form(form)
        person.id = None
        person.staff = True
        db.session.add(person)
        try:
            db.session.commit()
            flash('職員の追加ができました', 'success')
            return redirect(url_for('staffs.index'))
        except Exception as e:
            db.session.rollback()
            flash('職員追加時にエラーが発生しました "{}"'.format(e), 'danger')
    return render_template('staffs/edit.pug', form=form)

@bp.route('/<id>/edit', methods=('GET', 'POST'))
@login_required
def edit(id):
    person = Person.get(id)
    if person is None:
        abort(404)
    form = PersonForm(obj=person)
    if form.validate_on_submit():
        person.populate_form(form)
        db.session.add(person)
        try:
            db.session.commit()
            flash('職員の更新ができました', 'success')
            return redirect(url_for('staffs.index'))
        except Exception as e:
            db.session.rollback()
            flash('職員更新時にエラーが発生しました "{}"'.format(e), 'danger')
    return render_template('staffs/edit.pug', form=form)

@bp.route('/<id>/destroy', methods=('GET', 'POST'))
@login_required
def destroy(id):
    person = Person.get(id)
    if person is None:
        abort(404)
    q = db.session.query(
        func.count(WorkLog.yymm)
    ).filter(
        WorkLog.person_id==id
    ).group_by(
        WorkLog.person_id
    ).first()
    if q is not None:
        flash('勤怠データが存在しているため削除できません','danger')
        return redirect(url_for('staffs.index'))
    db.session.delete(person)
    try:
        db.session.commit()
        flash('職員の削除ができました', 'success')
    except Exception as e:
        db.session.rollback()
        flash('職員削除時にエラーが発生しました "{}"'.format(e), 'danger')
    return redirect(url_for('staffs.index'))
