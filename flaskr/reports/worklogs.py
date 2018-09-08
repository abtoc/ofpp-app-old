from flask import Blueprint, abort, make_response
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, portrait
from reportlab.lib.units import mm
from reportlab.platypus import Table
from io import BytesIO
from datetime import date
from dateutil.relativedelta import relativedelta
from flaskr import db
from flaskr.models import Person, WorkLog, Option
from flaskr.utils import weeka

bp = Blueprint('report_worklogs', __name__, url_prefix="/report/worklogs")

def make_head(id, yymm):
    person = Person.get(id)
    if person is None:
        return None
    yy = int(yymm[:4])
    mm = int(yymm[4:])
    head = {}
    head['ym'] = '{}年{}月'.format(yy,mm)
    head['name'] = person.name
    return head

def make_items(id, yymm):
    yy = int(yymm[:4])
    mm = int(yymm[4:])
    foot = dict(
        count = 0,
        value = 0.0,
        break_t = 0.0,
        over_t = 0.0,
        absence = 0,
        late = 0,
        leave = 0
    )
    first = date(yy,mm,1)
    items = []
    for dd in range(1, 32):
        if mm != first.month:
            items.append(None)
            continue
        first = first + relativedelta(days=1)
        item = dict(
            dd = dd,
            ww = weeka[date(yy,mm,dd).weekday()],
            work_in = '',
            work_out = '',
            break_t = '',
            value = '',
            over_t = '',
            absence = '',
            leave = '',
            late = '',
            remarks = ''
        )
        worklog = WorkLog.get(id, yymm, dd)
        if worklog is None:
            items.append(item)
            continue
        item['work_in'] = worklog.work_in if bool(worklog.work_in) else ''
        item['work_out'] = worklog.work_out if bool(worklog.work_out) else ''
        if worklog.break_t is not None:
            item['break_t'] = worklog.break_t
            foot['break_t'] +=  worklog.break_t
        if worklog.value is not None:
            item['value'] = worklog.value
            foot['value'] += worklog.value
            foot['count'] += 1
        if worklog.over_t is not None:
            item['over_t'] = worklog.over_t
            foot['over_t'] += worklog.over_t
        item['absence'] = '○' if bool(worklog.absence) else ''
        foot['absence'] = foot['absence'] + (1 if bool(worklog.absence) else 0) 
        item['leave'] = '○' if bool(worklog.leave) else ''
        foot['leave'] = foot['leave'] + (1 if bool(worklog.leave) else 0)
        item['late'] = '○' if bool(worklog.late) else ''
        foot['late'] = foot['late'] + (1 if bool(worklog.late) else 0)
        item['remarks'] = worklog.remarks if bool(worklog.remarks) else ''
        items.append(item)
    return items, foot

def make_pdf(head, items, foot):
    output = BytesIO()
    psize = portrait(A4)
    xmargin = 15.0*mm
    p = canvas.Canvas(output, pagesize=psize, bottomup=True)
    # Title
    name = Option.get('office_name',  '')
    colw = (45.5*mm, 20.5*mm, 24.5*mm, 22.5*mm, 30.5*mm, 27.5*mm)
    data = [[head['ym'],'出勤簿','氏名:',head['name'],'所属：',name]]
    table = Table(data, colWidths=colw, rowHeights=8.0*mm)
    table.setStyle([
        ('FONT',   ( 0, 0), ( 1,-1), 'Gothic', 16),
        ('FONT',   ( 2, 0), (-1,-1), 'Gothic', 12),
        ('ALIGN',  ( 0, 0), (-1,-1), 'CENTER'),
        ('ALIGN',  ( 2, 0), ( 2,-1), 'RIGHT'),
        ('ALIGN',  ( 3, 0), ( 3,-1), 'LEFT'),
        ('ALIGN',  ( 4, 0), ( 4,-1), 'RIGHT'),
        ('ALIGN',  ( 5, 0), ( 5,-1), 'LEFT'),
    ])
    table.wrapOn(p, xmargin, 272.0*mm)
    table.drawOn(p, xmargin, 272.0*mm)
    # Detail
    colw = (10.0*mm, 10.0*mm, 16.5*mm, 16.5*mm, 16.5*mm, 20.5*mm, 16.5*mm, 10.5*mm, 10.5*mm, 10.5*mm, 47.0*mm)
    data =[
        ['日','曜日','始業','終業','休憩','時間','残業', '欠勤', '遅刻', '早退', '備考']
    ]
    for item in items:
        row = []
        if item  is not None:
            row.append(item['dd'])
            row.append(item['ww'])
            row.append(item['work_in'])
            row.append(item['work_out'])
            row.append(item['break_t'])
            row.append(item['value'])
            row.append(item['over_t'])
            row.append(item['absence'])
            row.append(item['late'])
            row.append(item['leave'])
            row.append(item['remarks'])
        data.append(row)
    table = Table(data, colWidths=colw, rowHeights=8.0*mm)
    table.setStyle([
        ('FONT',   ( 0, 0), (-1,-1), 'Gothic', 12),
        ('GRID',   ( 0, 0), (-1,-1), 0.5, colors.black),
        ('BOX',    ( 0, 0), (-1,-1), 1.8, colors.black),
        ('VALIGN', ( 0, 0), (-1,-1), 'MIDDLE'),
        ('ALIGN',  ( 0, 0), (-1,-1), 'CENTER'),
        ('ALIGN',  (10, 1), (10,-1), 'LEFT')
    ])
    table.wrapOn(p, xmargin, 16.0*mm)
    table.drawOn(p, xmargin, 16.0*mm)
    # Foot
    colw = (20.0*mm, 33.0*mm, 16.5*mm, 20.5*mm, 16.5*mm, 10.5*mm, 10.5*mm, 10.5*mm, 47.0*mm)
    data =[
        [
            '合計',
            '{}日'.format(foot['count']),
            foot['break_t'],
            foot['value'],
            foot['over_t'], 
            foot['absence'], 
            foot['late'], 
            foot['leave'],
            ''
        ]
    ]
    table = Table(data, colWidths=colw, rowHeights=8.0*mm)
    table.setStyle([
        ('FONT',   ( 0, 0), (-1,-1), 'Gothic', 12),
        ('GRID',   ( 0, 0), (-1,-1), 0.5, colors.black),
        ('BOX',    ( 0, 0), (-1,-1), 1.8, colors.black),
        ('VALIGN', ( 0, 0), (-1,-1), 'MIDDLE'),
        ('ALIGN',  ( 0, 0), (-1,-1), 'CENTER'),
    ])
    table.wrapOn(p, xmargin, 7.0*mm)
    table.drawOn(p, xmargin, 7.0*mm)
    # Print
    p.showPage()
    p.save()
    result = output.getvalue()
    output.close()
    return result


@bp.route('/<id>/<yymm>')
def report(id, yymm):
    head = make_head(id, yymm)
    if head == None:
        abort(404)
    items, foot = make_items(id, yymm)
    if items == None:
        abort(404)
    response = make_response(make_pdf(head, items, foot))
    response.mimetype = 'application/pdf'
    return response

