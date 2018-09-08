from flaskr import app, db, celery
from flaskr.models import Person, AbsenceLog

@celery.task
def update_absencelog_enabled(id, yymm):
    app.logger.info('Update AbsenceLogs enabled. id={} yymm={}'.format(id,yymm))
    person = Person.get(id)
    if person is None:
        return
    absencelogs = AbsenceLog.query.filter(AbsenceLog.person_id==id, AbsenceLog.yymm==yymm).order_by(AbsenceLog.dd).all()
    count = 0
    for absencelog in absencelogs:
        if bool(absencelog.deleted):
            absencelog.enabled = False
        else:
            count = count + 1
            if count <= 4:
                absencelog.enabled = True
            else:
                absencelog.enabled = False
        db.session.add(absencelog)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            app.logger.error(e)
