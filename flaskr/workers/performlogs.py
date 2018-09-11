from datetime import date
from dateutil.relativedelta import relativedelta
from flaskr import app, db, celery
from flaskr.models import Person, PerformLog, WorkLog

def _is_persent(performlog):
    if bool(performlog.work_in) or bool(performlog.work_out):
        return True
    worklog = WorkLog.get(performlog.person_id, performlog.yymm, performlog.dd)
    if (worklog is None) or (worklog.value is None):
        return False
    return True

def _is_enabled(performlog):
    if bool(performlog.absence_add):
        return True
    if bool(performlog.pickup_in) or bool(performlog.pickup_out):
        return True
    if bool(performlog.visit):
        return True
    if bool(performlog.meal):
        return True
    if bool(performlog.medical):
        return True
    if bool(performlog.experience):
        return True
    if bool(performlog.outside):
        return True
    if bool(performlog.remarks):
        return True
    return False

@celery.task
def update_performlogs_enabled(id, yymm):
    app.logger.info('Update PerformLogs enabled. id={} yymm={}'.format(id,yymm))
    person = Person.get(id)
    if person is None:
        return
    yy = yymm[:4]
    mm = yymm[4:]
    first = date(int(yy), int(mm), 1)
    last = first + relativedelta(months=1) - relativedelta(days=1)
    last = last.day - 8
    performlogs = PerformLog.get_yymm(id, yymm)
    count = 0
    absence = 0
    visit = 0
    for performlog in performlogs:
        if _is_persent(performlog):
            count = count + 1
            if count <= last:
                performlog.presented = True
                performlog.enabled = True
            else:
                performlog.presented = False
                performlog.enabled = False
        else:
            performlog.enabled = _is_enabled(performlog)
            performlog.presented = False
        db.session.add(performlog)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            app.logger.error(e)

@celery.task
def destroy_performlogs():
    app.logger.info('Destroy PerformLogs.')
