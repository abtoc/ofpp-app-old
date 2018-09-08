from datetime import date
from dateutil.relativedelta import relativedelta
from flask import Blueprint, render_template, redirect, url_for, flash, abort
from flask_login import login_required
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField
from wtforms.validators import DataRequired
from flaskr import db
from flaskr.models import Person, AbsenceLog

bp = Blueprint('absences', __name__, url_prefix='/absences')

class AbsenceForm(FlaskForm):
    staff_id = SelectField('対応職員', render_kw={'class': 'form-control'})
    reason = StringField('欠席理由', validators=[DataRequired(message='必須項目です')])
    remarks = StringField('相談援助')
    def __init__(self, *args, **kwargs):
        super(AbsenceForm, self).__init__(*args, **kwargs)
        self.staff_id.choices = [(p.id, p.name) for p in Person.query.filter(Person.staff==True,Person.enabled==True).order_by(Person.name).all()]

@bp.route('/')
@bp.route('/<yymm>')
def index(yymm=None):
    if yymm is None:
        now = date.today()
        yymm = now.strftime('%Y%m')
    yy = int(yymm[:4])
    mm = int(yymm[4:])
    today = date(yy,mm, 1)
    prev = today - relativedelta(months=1)
    next = today + relativedelta(months=1)
    head = dict(
        ym='{}年{}月'.format(yy, mm),
        prev=prev.strftime('%Y%m'),
        next=next.strftime('%Y%m')
    )
    absencelogs = AbsenceLog.query.filter(AbsenceLog.yymm==yymm).order_by(AbsenceLog.yymm, AbsenceLog.dd, AbsenceLog.create_at).all()
    items = []
    for absencelog in absencelogs:
        person = Person.get(absencelog.person_id)
        staff = Person.get(absencelog.staff_id)
        item = dict(
            id=absencelog.person_id,
            dd= absencelog.dd,
            enabled = '○' if absencelog.enabled else '×',
            deleted = absencelog.deleted,
            name = person.get_display() if bool(person) else '',
            staff = staff.name if bool(staff) else '',
            reason = absencelog.reason if bool(absencelog.reason) else '',
            remarks = absencelog.remarks if bool(absencelog.remarks) else ''
        )
        items.append(item)
    return render_template('absences/index.pug', yymm=yymm, head=head, items=items)

@bp.route('/<id>/<yymm>/<dd>/edit', methods=('GET', 'POST'))
def edit(id,yymm,dd):
    absencelog = AbsenceLog.get(id, yymm, dd)
    if absencelog is None:
        abort(404)
    person = Person.get(id)
    if person is None:
        abort(404)
    form = AbsenceForm(obj=absencelog)
    if form.validate_on_submit():
        absencelog.populate_form(form)
        db.session.add(absencelog)
        try:
            db.session.commit()
            flash('欠席時対応加算記録を保存しました', 'success')
            return redirect(url_for('absences.index', yymm=yymm))
        except Exception as e:
            db.session.rollback()
            flash('欠席時対応加算記録更新時にエラーが発生しました "{}"'.format(e), 'danger')
    return render_template('absences/edit.pug', form=form, name=person.name)
