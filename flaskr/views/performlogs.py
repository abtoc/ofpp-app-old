from datetime import date
from dateutil.relativedelta import relativedelta
from flask import Blueprint, render_template, redirect, url_for, flash, abort
from flask_login import login_required
from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, IntegerField, ValidationError
from wtforms.validators import DataRequired, Regexp, Optional
from flaskr import app, db, cache
from flaskr.models import Person, PerformLog, AbsenceLog
from flaskr.utils import weeka
from flaskr.workers.worklogs import sync_worklog_from_performlog
from flaskr.workers.performlogs import update_performlogs_enabled
from flaskr.workers.absences import update_absencelog_enabled

bp = Blueprint('performlogs', __name__, url_prefix='/performlogs')

class PerformLogsFormIDM(FlaskForm):
    absence = BooleanField('欠席')
    absence_add = BooleanField('欠席加算')
    work_in = StringField('開始時間', validators=[Optional(), Regexp(message='HH:MMで入力してください', regex='^[0-2][0-9]:[0-5][0-9]$')])
    work_out = StringField('終了時間', validators=[Optional(), Regexp(message='HH:MMで入力してください', regex='^[0-2][0-9]:[0-5][0-9]$')])
    pickup_in = BooleanField('送迎加算（往路）', validators=[Optional()])
    pickup_out = BooleanField('送迎加算（復路）', validators=[Optional()])
    meal = BooleanField('食事提供加算', validators=[Optional()])
    outside = BooleanField('施設外支援', validators=[Optional()])
    visit = IntegerField('訪問支援特別加算（時間数）', validators=[Optional()])
    medical = IntegerField('医療連携体制加算', validators=[Optional()])
    experience = IntegerField('体験利用支援加算（初日ー５日目は１、６日目ー１５日目は2）', validators=[Optional()])
    remarks = StringField('備考')

class PerformLogsForm(FlaskForm):
    absence = BooleanField('欠席')
    absence_add = BooleanField('欠席加算')
    pickup_in = BooleanField('送迎加算（往路）', validators=[Optional()])
    pickup_out = BooleanField('送迎加算（復路）', validators=[Optional()])
    meal = BooleanField('食事提供加算', validators=[Optional()])
    outside = BooleanField('施設外支援', validators=[Optional()])
    visit = IntegerField('訪問支援特別加算（時間数）', validators=[Optional()])
    medical = IntegerField('医療連携体制加算', validators=[Optional()])
    experience = IntegerField('体験利用支援加算（初日ー５日目は１、６日目ー１５日目は2）', validators=[Optional()])
    remarks = StringField('備考')

def _check_yymmdd(yymm, dd=1):
    if len(yymm) != 6:
        return False
    try:
        yy = int(yymm[:4])
        mm = int(yymm[4:])
        dd = int(dd)
        date(yy,mm,dd)
        return True
    except ValueError:
        return False

@bp.route('/<id>')
@bp.route('/<id>/<yymm>')
def index(id, yymm=None):
    if (yymm is not None) and (not _check_yymmdd(yymm)):
        abort(400)
    person = Person.get(id)
    if person is None:
        abort(404)
    if yymm is None:
        now = date.today()
        yymm = now.strftime('%Y%m')
    else:
        now = date(int(yymm[:4]), int(yymm[4:]), 1)
    first = date(now.year, now.month, 1)
    last = first + relativedelta(months=1)
    prev = first - relativedelta(months=1)
    head = dict(
        name=person.get_display(),
        ym='{}年{}月'.format(first.year, first.month),
        prev=prev.strftime('%Y%m'),
        next=last.strftime('%Y%m')
    )
    foot = dict(
        count=0,
        pickup=0,
        visit=0,
        meal=0,
        medical=0,
        experience=0,
        outside=0
    )
    items = []
    while first < last:
        item = dict(
            dd=first.day,
            week=weeka[first.weekday()],
            edit=False,
            create=True,
            delete=False,
            enabled=None,
            absence=False,
            absence_add=False,
            work_in=None,
            work_out=None,
            pickup_in=None,
            pickup_out=None,
            visit=None,
            meal=None,
            medical=None,
            experience=None,
            outside=None,
            remarks=None
        )
        performlog = PerformLog.get_date(id, first)
        if performlog is None:
            item['create'] = True
        else:
            if person.is_idm():
                item['edit'] = True
                item['delete'] = True
            else:
                if (not bool(performlog.work_in)) or (not bool(performlog.work_out)):
                    item['edit'] = True
                    item['delete'] = True
                else:
                    item['edit'] = True
            item['enabled'] = performlog.enabled
            item['absence'] = performlog.absence
            item['absence_add'] = performlog.absence_add
            item['work_in'] = performlog.work_in
            item['work_out'] = performlog.work_out
            item['pickup_in'] = '○' if performlog.pickup_in else ''
            item['pickup_out'] = '○' if performlog.pickup_out else ''
            item['visit'] = performlog.visit
            item['meal'] = '○' if performlog.meal else ''
            item['medical'] = performlog.medical
            item['experience'] = performlog.experience
            item['outside'] = '○' if performlog.outside else ''
            item['remarks'] = performlog.remarks
            if (bool(item['enabled'])) and (not bool(item['absence'])):
                foot['count'] += 1 if bool(item['work_in']) else 0
                foot['pickup'] += 1 if bool(item['pickup_in']) else 0
                foot['pickup'] += 1 if bool(item['pickup_out']) else 0
                foot['visit'] += 1 if bool(item['visit'])  else 0
                foot['meal'] += 1 if bool(item['meal']) else 0
                foot['medical'] += 1 if bool(item['medical']) else 0
                foot['experience'] += 1 if bool(item['experience']) else 0
                foot['outside'] += 1 if bool(item['outside']) else 0
        items.append(item)
        first = first + relativedelta(days=1)
    return render_template('performlogs/index.pug', id=id, yymm=yymm, head=head, items=items, foot=foot)

@bp.route('/<id>/<yymm>/<dd>/create', methods=('GET', 'POST'))
@login_required
def create(id, yymm, dd):
    if (not _check_yymmdd(yymm,dd=dd)):
        abort(400)
    person   = Person.get(id)
    if person is None:
        abort(404)
    yymmdd = date(int(yymm[:4]), int(yymm[4:]), int(dd))
    item=dict(
        name=person.get_display(),
        yymmdd=yymmdd.strftime('%Y/%m/%d(%a)')
    )
    if person.is_idm():
        form =  PerformLogsFormIDM()
    else:
        form =  PerformLogsForm()
    if form.validate_on_submit():
        performlog = PerformLog(person_id=id, yymm=yymm, dd=dd)
        performlog.populate_form(form)
        try:
            performlog.validate()
            if performlog.absence_add:
                absencelog = AbsenceLog()
                absencelog.deleted = False
                performlog.absencelog = absencelog
            db.session.add(performlog)
            try:
                db.session.commit()
                sync_worklog_from_performlog.delay(id, yymm, dd)
                update_performlogs_enabled.delay(id, yymm)
                update_absencelog_enabled.delay(id, yymm)
                flash('実績の追加ができました','success')
                return redirect(url_for('performlogs.index', id=id, yymm=yymm))
            except Exception as e:
                db.session.rollback()
                flash('実績追加時にエラーが発生しました "{}"'.format(e), 'danger')
        except ValidationError as e:
            flash(e, 'danger')
    return render_template('performlogs/edit.pug', id=id, yymm=yymm, item=item, form=form)

@bp.route('/<id>/<yymm>/<dd>/edit', methods=('GET', 'POST'))
@login_required
def edit(id, yymm, dd):
    if (not _check_yymmdd(yymm,dd=dd)):
        abort(400)
    person   = Person.get(id)
    if person is None:
        abort(404)
    yymmdd = date(int(yymm[:4]), int(yymm[4:]), int(dd))
    item=dict(
        name=person.get_display(),
        yymmdd=yymmdd.strftime('%Y/%m/%d(%a)')
    )
    performlog = PerformLog.get(id, yymm, dd)
    if performlog is None:
        abort(404)
    if person.is_idm():
        form =  PerformLogsFormIDM(obj=performlog)
    else:
        form =  PerformLogsForm(obj=performlog)
    if form.validate_on_submit():
        performlog.populate_form(form)
        try:
            performlog.validate()
            if performlog.absence_add:
                if bool(performlog.absencelog):
                    performlog.absencelog.deleted = False
                else:
                    absencelog = AbsenceLog()
                    performlog.absencelog = absencelog
            else:
                if bool(performlog.absencelog):
                    performlog.absencelog.deleted = True
            db.session.add(performlog)
            try:
                db.session.commit()
                sync_worklog_from_performlog.delay(id, yymm, dd)
                update_performlogs_enabled.delay(id, yymm)
                update_absencelog_enabled.delay(id, yymm)
                flash('実績の更新ができました','success')
                return redirect(url_for('performlogs.index', id=id, yymm=yymm))
            except Exception as e:
                db.session.rollback()
                flash('実績更新時にエラーが発生しました "{}"'.format(e), 'danger')
        except ValidationError as e:
            flash(e, 'danger')
    return render_template('performlogs/edit.pug', id=id, yymm=yymm, item=item, form=form)

@bp.route('/<id>/<yymm>/<dd>/destroy')
@login_required
def destroy(id,yymm,dd):
    if (not _check_yymmdd(yymm,dd=dd)):
        abort(400)
    person   = Person.get(id)
    if person is None:
        abort(404)
    if not person.is_idm():
        flash('利用者のICカードをセットしてください', 'danger')
        return redirect(url_for('performlogs.index', id=id, yymm=yymm))
    performlog = PerformLog.get(id, yymm, dd)
    if performlog is None:
        abort(404)
    if bool(performlog.absencelog):
        db.session.delete(performlog.absencelog)
    db.session.delete(performlog)
    try:
        db.session.commit()
        sync_worklog_from_performlog.delay(id, yymm, dd)
        update_performlogs_enabled.delay(id, yymm)
        flash('実績の削除ができました', 'success')
    except Exception as e:
        db.session.rollback()
        flash('実績削除時にエラーが発生しました "{}"'.format(e), 'danger')
    return redirect(url_for('performlogs.index', id=id, yymm=yymm))

@bp.route('/<id>/<yymm>/update')
@login_required
def update(id,yymm):
    sync_worklog_from_performlog.delay(id, yymm)
    update_performlogs_enabled.delay(id, yymm)
    update_absencelog_enabled.delay(id, yymm)
    return redirect(url_for('performlogs.index', id=id, yymm=yymm))
