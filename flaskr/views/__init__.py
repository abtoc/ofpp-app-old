from flask import render_template, url_for
from datetime import date
from dateutil.relativedelta import relativedelta
from flaskr import app
from flaskr.models import Person, WorkLog

def _get_caption(person, yymmdd):
    worklog = WorkLog.get_date(person.id, yymmdd)
    yymm = yymmdd.strftime('%Y%m')
    dd = yymmdd.day
    if worklog is None:
        caption = 'ー'
        if person.staff:
            url = url_for('worklogs.create', id=person.id, yymm=yymm, dd=dd)
        else:
            url = url_for('performlogs.create', id=person.id, yymm=yymm, dd=dd)
    else:
        if person.staff:
            url = url_for('worklogs.edit', id=person.id, yymm=yymm, dd=dd)
        else:
            url = url_for('performlogs.edit', id=person.id, yymm=yymm, dd=dd)
        if worklog.absence:
            caption = '欠席'
        elif bool(worklog.work_in) or bool(worklog.work_out):
            caption = '{}-{}'.format(worklog.work_in, worklog.work_out)
        else:
            caption = 'ー'
    return caption, url

@app.route('/')
def index():
    today = date.today()
    yymm = today.strftime('%Y%m')
    yesterday1 = date.today() - relativedelta(days=1)
    yesterday2 = yesterday1 - relativedelta(days=1)
    prev = date.today() - relativedelta(months=1)
    items = []
    persons = Person.query.filter(Person.enabled==True).order_by(Person.staff.asc(), Person.name.asc()).all()
    for person in persons:
        item = {}
        item['id'] = person.id
        item['name'] = person.get_display()
        item['staff'] = person.staff
        item['yymm'] = yymm
        item['yymm_l'] = prev.strftime('%Y%m')
        item['dd'] = today.day
        item['caption'], item['url'] = _get_caption(person, today)
        item['caption1'], item['url1'] = _get_caption(person, yesterday1)
        item['caption2'], item['url2'] = _get_caption(person, yesterday2)
        items.append(item)
    return render_template('index.pug', items=items)

from flaskr.views import persons
app.register_blueprint(persons.bp)
from flaskr.views import performlogs
app.register_blueprint(performlogs.bp)
from flaskr.views import worklogs
app.register_blueprint(worklogs.bp)
from flaskr.views import timerules
app.register_blueprint(timerules.bp)
from flaskr.views import options
app.register_blueprint(options.bp)
from flaskr.views import users
app.register_blueprint(users.bp)
from flaskr.views import auth
app.register_blueprint(auth.bp)
from flaskr.views import staffs
app.register_blueprint(staffs.bp)
from flaskr.views import recipients
app.register_blueprint(recipients.bp)
from flaskr.views import absences
app.register_blueprint(absences.bp)
