from datetime import date
from dateutil.relativedelta import relativedelta
from flask import Blueprint, render_template, redirect, url_for, flash, abort
from flask_login import login_required
from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, DecimalField, ValidationError
from wtforms.validators import DataRequired, Regexp, Optional
from flaskr import app, db
from flaskr.models import Person, WorkLog
from flaskr.utils import weeka
from flaskr.workers.worklogs import update_worklog_value
from flaskr.workers.performlogs import sync_performlog_from_worklog

bp = Blueprint('worklogs', __name__, url_prefix='/worklogs')

class WorkLogForm(FlaskForm):
    value = DecimalField('勤務時間', validators=[Optional()])
    break_t = DecimalField('休憩時間', validators=[Optional()])
    over_t = DecimalField('残業時間', validators=[Optional()])
    late = BooleanField('遅刻')
    leave = BooleanField('早退')
    remarks = StringField('備考')

class WorkLogFormRemarks(FlaskForm):
    remarks = StringField('備考')

class WorkLogFormStaff(FlaskForm):
    work_in = StringField('開始時間', validators=[Optional(), Regexp(message='HH:MMで入力してください', regex='^[0-2][0-9]:[0-5][0-9]$')])
    work_out = StringField('終了時間', validators=[Optional(), Regexp(message='HH:MMで入力してください', regex='^[0-2][0-9]:[0-5][0-9]$')])
    value = DecimalField('勤務時間', validators=[Optional()])
    break_t = DecimalField('休憩時間', validators=[Optional()])
    over_t = DecimalField('残業時間', validators=[Optional()])
    absence = BooleanField('欠勤')
    late = BooleanField('遅刻')
    leave = BooleanField('早退')
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
        id=person.id,
        name=person.get_display(),
        staff=person.staff,
        yymm=yymm,
        ym='{}年{}月'.format(first.year, first.month),
        prev=prev.strftime('%Y%m'),
        next=last.strftime('%Y%m')
    )
    foot = dict(
        cnt=0,
        sum=0,
        avg=0,
        break_t=0,
        over_t=0,
        absence=0,
        late=0,
        leave=0
    )
    items=[]
    while first < last:
        item = dict(
            dd=first.day,
            week=weeka[first.weekday()],
            situation=None,
            work_in=None,
            work_out=None,
            value=None,
            break_t=None,
            over_t=None,
            remarks=None,
            absence=False,
            late=False,
            leave=False,
            edit=False
        )
        worklog = WorkLog.get_date(id, first)
        if worklog is not None:
            item['edit'] = True
            item['work_in']  = worklog.work_in
            item['work_out'] = worklog.work_out
            item['value'] = worklog.value
            item['break_t'] = worklog.break_t
            item['over_t'] = worklog.over_t
            item['absence'] = worklog.absence
            item['late'] = worklog.late
            item['leave'] = worklog.leave
            item['remarks'] = worklog.remarks
            foot['cnt'] += 1 if bool(worklog.value) else 0
            foot['sum'] += worklog.value if bool(worklog.value) else 0
            foot['break_t'] += worklog.break_t if bool(worklog.break_t) else 0
            foot['over_t'] += worklog.over_t if bool(worklog.over_t) else 0
            foot['absence'] += 1 if bool(worklog.absence) else 0
            foot['late'] += 1 if bool(worklog.late) else 0
            foot['leave'] += 1 if bool(worklog.leave) else 0
        items.append(item)
        first = first + relativedelta(days=1)
    return render_template('worklogs/index.pug', id=id, yymm=yymm, head=head, items=items, foot=foot)

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
        id=person.id,
        yymm=yymm,
        name=person.get_display(),
        yymmdd=yymmdd.strftime('%Y/%m/%d(%a)')
    )
    if not person.staff:
        flash('職員以外は勤怠登録はできません。実績登録で行ってください ', 'danger')
        return redirect(url_for('worklogs.index', id=id, yymm=yymm))
    form =  WorkLogFormStaff()
    if form.validate_on_submit():
        worklog = WorkLog(person_id=id, yymm=yymm, dd=dd)
        worklog.populate_form(form)
        try:
            db.session.add(worklog)
            try:
                db.session.commit()
                if (person.staff) and (worklog.value is None):
                    update_worklog_value.delay(id, yymm, dd)
                flash('勤怠の追加ができました','success')
                return redirect(url_for('worklogs.index', id=id, yymm=yymm))
            except Exception as e:
                db.session.rollback()
                flash('勤怠追加時にエラーが発生しました "{}"'.format(e), 'danger')
        except ValidationError as e:
            flash(e, 'danger')
    return render_template('worklogs/edit_staff.pug', id=id, yymm=yymm, form=form, item=item)

@bp.route('/<id>/<yymm>/<dd>/edit', methods=('GET', 'POST'))
@login_required
def edit(id, yymm, dd):
    if (not _check_yymmdd(yymm,dd=dd)):
        abort(400)
    person   = Person.get(id)
    if person is None:
        abort(404)
    yymmdd = date(int(yymm[:4]), int(yymm[4:]), int(dd))
    worklog = WorkLog.get(id, yymm, dd)
    item=dict(
        id=person.id,
        yymm=yymm,
        name=person.get_display(),
        yymmdd=yymmdd.strftime('%Y/%m/%d(%a)'),
        absence=worklog.absence,
        work_in=worklog.work_in if worklog.work_in is not None else '',
        work_out=worklog.work_out if worklog.work_out is not None else ''
    )
    if worklog is None:
        abort(404)
    if person.staff:
        form = WorkLogFormStaff(obj=worklog)
    else:
        if worklog.absence:
            form = WorkLogFormRemarks(obj=worklog)
        else:
            form = WorkLogForm(obj=worklog)
    if form.validate_on_submit():
        worklog.populate_form(form)
        try:
            db.session.add(worklog)
            try:
                db.session.commit()
                if (person.staff) and (worklog.value is None):
                    update_worklog_value.delay(id, yymm, dd)
                flash('勤怠の更新ができました','success')
                return redirect(url_for('worklogs.index', id=id, yymm=yymm))
            except Exception as e:
                db.session.rollback()
                flash('勤怠更新時にエラーが発生しました "{}"'.format(e), 'danger')
        except ValidationError as e:
            flash(e, 'danger')
    if person.staff:
        return render_template('worklogs/edit_staff.pug', id=id, yymm=yymm, form=form, item=item)
    return render_template('worklogs/edit.pug', id=id, yymm=yymm, form=form, item=item)

@bp.route('/<id>/<yymm>/<dd>/destroy')
@login_required
def destroy(id,yymm,dd):
    if (not _check_yymmdd(yymm,dd=dd)):
        abort(400)
    person   = Person.get(id)
    if person is None:
        abort(404)
    if not person.staff:
        flash('職員以外は勤怠削除はできません。実績削除で行ってください "{}"'.format(e), 'danger')
        return redirect(url_for('performlogs.index', id=id, yymm=yymm))
    worklog = WorkLog.get(id, yymm, dd)
    if worklog is None:
        abort(404)
    db.session.delete(worklog)
    try:
        db.session.commit()
        flash('勤怠の削除ができました', 'success')
    except Exception as e:
        db.session.rollback()
        flash('勤怠削除時にエラーが発生しました "{}"'.format(e), 'danger')
    return redirect(url_for('worklogs.index', id=id, yymm=yymm))

@bp.route('/<id>/<yymm>/update')
@login_required
def update(id,yymm):
    sync_performlog_from_worklog.delay(id, yymm)
    return redirect(url_for('worklogs.index', id=id, yymm=yymm))
