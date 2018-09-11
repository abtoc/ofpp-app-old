from flaskr import app, db, celery
from flaskr.models import Person, PerformLog, WorkLog, TimeRule
import json

@celery.task
def update_worklog_value(id, yymm, dd=None):
    app.logger.info('Update WorkLog value from Time-Table. id={} yymm={} dd={}'.format(id,yymm,dd))
    person = Person.get(id)
    if person is None:
        return        
    if person.timerule_id is None:
        return
    timerule=TimeRule.get(person.timerule_id)
    if timerule is None:
        return
    if dd is None:
        dds = range(1,32)
    else:
        dds = (dd,)
    for d in dds:
        worklog = WorkLog.get(id, yymm, d)
        if worklog is None:
            continue
        if worklog.value is not None:
            continue
        app.logger.info('Updating WorkLog value from Time-Table. id={} yymm={} dd={}'.format(id,yymm,d))
        if not bool(worklog.work_in):
            continue
        if not bool(worklog.work_out):
            continue
        rules=json.loads(timerule.rules)
        work_in = rules['core']['start']
        work_out = rules['core']['end']
        for i in rules['times']:
            if (i['in']) and (i['start'] <= worklog.work_in) and (worklog.work_in < i['end']):
                work_in = i['value']
                break
        for i in rules['times']:
            if (i['out']) and (i['start'] <= worklog.work_out) and (worklog.work_out < i['end']):
                work_out = i['value']
                break
        value = work_out - work_in
        break_t = 0.0
        if 'break' in rules:
            for i in rules['break']:
                if (work_in <= i['start']) and (work_out >= i['end']):
                    break_t = break_t + i['value']
        if value < 0:
            value = 0
        elif ('max' in rules) and (value > rules['max']):
            value = rules['max']
        worklog.value = value - break_t
        worklog.break_t = break_t
        worklog.over_t = worklog.value - rules['core']['value']
        if worklog.over_t < 0:
            worklog.over_t = 0
        worklog.late = work_in > rules['core']['start']
        worklog.leave = work_out < rules['core']['end']
        db.session.add(worklog)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        app.logger.error(e)

@celery.task
def destroy_worklogs():
    app.logger.info('Destroy WorkLogs.')
