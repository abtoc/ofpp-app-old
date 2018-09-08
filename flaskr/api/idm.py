from datetime import datetime
from flask import Blueprint
from flask import jsonify
from flaskr import db, cache, auth
from flaskr.models import Person, WorkLog
from flaskr.workers.worklogs import update_worklog_value
from flaskr.workers.performlogs import sync_performlog_from_worklog

bp = Blueprint('api_idm', __name__, url_prefix="/api/idm")

@bp.route('/<idm>',methods=['GET'])
@auth.login_required
def get(idm):
    person = Person.query.filter(Person.idm == idm).first()
    if person is None:
        return jsonify({"name": "該当者無し"}), 404
    result = dict(
        name=person.get_display()
    )
    cache.set('person.id', person.id, timeout=10*60)
    cache.set('person.idm', person.idm, timeout=10*60)
    return jsonify(result), 200

@bp.route('/<idm>',methods=['POST'])
@auth.login_required
def post(idm):
    person = Person.query.filter(Person.idm == idm).first()
    if person is None:
        return jsonify({"name": "該当者無し"}), 404
    cache.set('person.id', None)
    cache.set('person.idm', None)
    now = datetime.now()
    yymm = now.strftime('%Y%m')
    dd = now.day
    hhmm = now.strftime('%H:%M')
    worklog = WorkLog.get(person.id, yymm, dd)
    if worklog is None:
        worklog = WorkLog(person_id=person.id, yymm=yymm, dd=dd)
    worklog.absence = False
    if not bool(worklog.work_in):
        worklog.work_in = hhmm
    else:
        worklog.work_out = hhmm
        worklog.value = None
        worklog.break_t = None
        worklog.over_t = None
    db.session.add(worklog)
    try:
        db.session.commit()
        update_worklog_value.delay(person.id, yymm, dd)
        if not person.staff:
            sync_performlog_from_worklog.delay(person.id, yymm, dd)
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "{}".format(e)}), 500
    if bool(worklog.work_out):
        result = dict(
            work_in = worklog.work_in,
            work_out = worklog.work_out
        )
        return jsonify(result), 200
    result = dict(
        work_in = worklog.work_in,
        work_out = '--:--'
    )
    return jsonify(result), 201

@bp.route('/<idm>',methods=['DELETE'])
@auth.login_required
def delete(idm):
    cache.set('person.id', None)
    cache.set('person.idm', None)
    return jsonify({}), 200
