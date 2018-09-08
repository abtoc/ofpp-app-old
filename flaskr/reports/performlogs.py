from flask import Blueprint, abort, make_response
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, portrait
from reportlab.lib.units import mm
from reportlab.platypus import Table
from io import BytesIO
from datetime import date
from flaskr import db
from flaskr.models import Person, PerformLog, Option
from flaskr.utils import weeka

bp = Blueprint('report_performlogs', __name__, url_prefix="/report/performlogs")

def make_head(id, yymm):
    person = Person.get(id)
    if person is None:
        return None
    yy = int(yymm[:4])
    gg = yy - 1988
    mm = int(yymm[4:])
    head = {}
    head['gm'] = '平成{}年{}月分'.format(gg,mm)
    head['name'] = person.name
    head['idm'] = person.idm
    head['number'] = person.recipient.number
    head['amount'] = person.recipient.amount
    head['usestart'] = ''
    head['usestart30d'] = ''
    usestart, usestart30d = person.recipient.get_usestart()
    if usestart is not None:
        yy1 = usestart.year
        mm1 = usestart.month
        yy2 = usestart30d.year
        mm2 = usestart30d.month
        if ((yy1 == yy) and (mm1 == mm)) or ((yy2 == yy) or (mm2 == mm)):
            head['usestart'] = usestart
            head['usestart30d'] = usestart30d
    return head

def make_items(id, yymm):
    yy = int(yymm[:4])
    mm = int(yymm[4:])
    foot = dict(
        count = 0,
        absence = 0,
        pickup = 0,
        visit = 0,
        meal = 0,
        medical = 0,
        experience = 0,
        outside = 0,
        usestart = 0
    )
    person = Person.get(id)
    performlogs = PerformLog.get_yymm(id, yymm)
    items = []
    for performlog in performlogs:
        item = dict(
            dd=performlog.dd,
            ww=weeka[date(yy,mm,performlog.dd).weekday()],
            stat='欠席' if performlog.absence_add else '',
            work_in = '',
            work_out = '',
            pickup_in = '',
            pickup_out = '',
            visit = '',
            meal = '',
            medical = '',
            experience = '',
            outside = '',
            remarks = ''
        )
        if (performlog.absence_add) and (bool(performlog.absencelog)) and (bool(performlog.absencelog.enabled)):
            foot['absence'] = foot['absence'] + 1
            item['stat'] = '欠席'
            item['remarks'] = performlog.remarks
            items.append(item)
            continue            
        if not performlog.enabled:
            continue
        foot['count'] += 1
        item['work_in'] = performlog.work_in if bool(performlog.work_in) else ''
        item['work_out'] = performlog.work_out if bool(performlog.work_out) else ''
        item['pickup_in'] = 1 if bool(performlog.pickup_in) else ''
        item['pickup_out'] = 1 if bool(performlog.pickup_out) else ''
        item['visit'] = performlog.visit
        item['meal'] = 1 if bool(performlog.meal) else ''
        item['medical'] = performlog.medical
        item['experience'] = performlog.experience
        item['outside'] = 1 if bool(performlog.outside) else ''
        foot['pickup'] += 1 if bool(performlog.pickup_in) else 0
        foot['pickup'] += 1 if bool(performlog.pickup_out) else 0
        foot['visit'] += 1 if bool(performlog.visit) else 0
        foot['meal'] += 1 if bool(performlog.meal) else 0
        foot['medical'] += 1 if bool(performlog.medical) else 0
        foot['experience'] += 1 if bool(performlog.experience) else 0
        foot['outside'] += 1 if bool(performlog.outside) else 0
        foot['usestart'] += 1 if person.recipient.is_usestart(date(yy,mm,performlog.dd)) else 0
        item['remarks'] = performlog.remarks
        items.append(item)
    return items, foot

def make_pdf(head, items, foot):
    output = BytesIO()
    psize = portrait(A4)
    xmargin = 15.0*mm
    p = canvas.Canvas(output, pagesize=psize, bottomup=True)
    # Title
    p.setFont('Gothic', 16)
    p.drawString(75*mm, 275*mm, '就労継続支援提供実績記録票')
    p.setFont('Gothic', 11)
    p.drawString(17*mm, 275*mm, head['gm'])
    # Header
    colw = (25.0*mm, 29.5*mm, 32.0*mm, 32.0*mm, 22.0*mm, 43.5*mm)
    idm = head['idm']
    number = Option.get('office_number','')
    name = Option.get('office_name',  '')
    data =[
        ['受給者証番号',head['number'],'支給決定障害者氏名',head['name'],'事業所番号',number],
        ['契約支給量',head['amount'],'','','事業者及び\nその事業所',name]
    ]
    table = Table(data, colWidths=colw, rowHeights=10.0*mm)
    table.setStyle([
        ('FONT',   ( 0, 0), (-1,-1), 'Gothic', 8),
        ('GRID',   ( 0, 0), (-1,-1), 0.5, colors.black),
        ('BOX',    ( 0, 0), (-1,-1), 1.8, colors.black),
        ('VALIGN', ( 0, 0), (-1,-1), 'MIDDLE'),
        ('ALIGN',  ( 0, 0), (-1,-1), 'CENTER'),
        ('ALIGN',  ( 1, 1), ( 1, 1), 'LEFT'),
        ('SPAN',   ( 1, 1), ( 3, 1))
    ])
    table.wrapOn(p, xmargin, 252.0*mm)
    table.drawOn(p, xmargin, 252.0*mm)
    # Detail
    colw = (8.6*mm,11.0*mm, 17.2*mm, 17.2*mm,  17.2*mm, 6.0*mm, 6.0*mm, 9.6*mm, 8.6*mm, 8.6*mm, 8.6*mm, 8.6*mm, 14.6*mm, 42.2*mm)
    data = [
        ['日\n付', '曜\n日','サービス提供実績',    '', '' , '',  '',  '', '', '', '', '', '利用者\n確認印', '備考'],
        ['',       '',      'サービス提供\nの状況','開始時間', '終了時間', '送迎加算', '',   '訪問支援\n特別加算', '食事\n提供\n加算', '医療\n連携\n体制\n加算', '体験\n利用\n支援\n加算', '施設外\n支援'], 
        ['',       '',      '',                    '',         '',         '往', '復', '時間数'           ]       
    ]
    count = 0
    for item in items:
        row = []
        row.append(item['dd'])
        row.append(item['ww'])
        row.append(item['stat'])
        row.append(item['work_in'])
        row.append(item['work_out'])
        row.append(item['pickup_in'])
        row.append(item['pickup_out'])
        row.append(item['visit'])
        row.append(item['meal'])
        row.append(item['medical'])
        row.append(item['experience'])
        row.append(item['outside'])
        row.append('')
        row.append(item['remarks'])
        data.append(row)
        count = count + 1
    while count < 28:
        data.append([])
        count = count + 1
    table = Table(data, colWidths=colw, rowHeights=7.0*mm)
    table.setStyle([
        ('FONT',   ( 0, 0), (-1,-1), 'Gothic', 9),
        ('FONT',   ( 2, 1), ( 2, 1), 'Gothic', 7), # サービス提供の状況
        ('FONT',   ( 5, 1), ( 6, 1), 'Gothic', 7), # 送迎加算
        ('FONT',   ( 7, 1), ( 7, 1), 'Gothic', 5), # 訪問支援特別加算
        ('FONT',   ( 7, 2), ( 7, 2), 'Gothic', 7), # 訪問支援特別加算
        ('FONT',   ( 8, 1), ( 8, 1), 'Gothic', 7), # 食事提供加算
        ('FONT',   ( 9, 1), ( 9, 1), 'Gothic', 6), # 医療連携体制加算
        ('FONT',   (10, 1), (10, 1), 'Gothic', 6), # 体験利用加算
        ('FONT',   (11, 1), (11, 1), 'Gothic', 7), # 施設外支援
        ('GRID',   ( 0, 0), (-1,-1), 0.5, colors.black),
        ('BOX',    ( 0, 0), (-1,-1), 1.8, colors.black),
        ('VALIGN', ( 0, 0), (-1,-1), 'MIDDLE'),
        ('ALIGN',  ( 0, 0), (-1,-1), 'CENTER'),
        ('SPAN',   ( 0, 0), ( 0, 2)), # 日付
        ('SPAN',   ( 1, 0), ( 1, 2)), # 曜日
        ('SPAN',   ( 2, 0), (11, 0)), # サービス提供実績
        ('SPAN',   (12, 0), (12, 2)), # 利用者確認印
        ('SPAN',   (13, 0), (13, 2)), # 備考
        ('SPAN',   ( 2, 1), ( 2, 2)), # サービス提供の状況
        ('SPAN',   ( 3, 1), ( 3, 2)), # 開始時間
        ('SPAN',   ( 4, 1), ( 4, 2)), # 終了時間
        ('SPAN',   ( 5, 1), ( 6, 1)), # 送迎加算
        ('SPAN',   ( 8, 1), ( 8, 2)), # 食事提供加算
        ('SPAN',   ( 9, 1), ( 9, 2)), # 医療連携体制加算
        ('SPAN',   (10, 1), (10, 2)), # 体験利用支援加算
        ('SPAN',   (11, 1), (11, 2)), # 施設外支援
        ('ALIGN',  (13, 3), (13,-1), 'LEFT'),
    ])
    table.wrapOn(p, xmargin, 32.0*mm)
    table.drawOn(p, xmargin, 32.0*mm)
    # Footer
    colw = (36.8*mm, 34.2*mm, 12.0*mm, 9.6*mm, 8.6*mm, 8.6*mm, 8.6*mm, 13.6*mm, 9.0*mm, 26.2*mm, 16.7*mm)
    data = [
        [
            '合計', 
            '{}回'.format(foot['count']),
            '{}回'.format(foot['pickup']),
            '{}回'.format(foot['visit']),
            '{}回'.format(foot['meal']),
            '{}回'.format(foot['medical']),
            '{}回'.format(foot['experience']),
            '施設外\n支援',
            '当月',
            '{}日      '.format(foot['outside']),
            ''
        ],
        ['', '', '', '', '', '', '', '', '累計','日/180日']
    ]
    table = Table(data, colWidths=colw, rowHeights=4.0*mm)
    table.setStyle([
        ('FONT',   ( 0, 0), (-1,-1), 'Gothic', 8),
        ('FONT',   ( 0, 0), ( 0, 0), 'Gothic', 9),
        ('GRID',   ( 0, 0), (-1,-1), 0.5, colors.black),
        ('BOX',    ( 0, 0), (-1,-1), 1.8, colors.black),
        ('VALIGN', ( 0, 0), (-1,-1), 'MIDDLE'),
        ('ALIGN',  ( 0, 0), (-1,-1), 'CENTER'),
        ('ALIGN',  ( 9, 0), ( 9,-1), 'RIGHT'),
        ('SPAN',   ( 0, 0), ( 0, 1)), # 合計
        ('SPAN',   ( 1, 0), ( 1, 1)), # 利用回数
        ('SPAN',   ( 2, 0), ( 2, 1)), # 送迎加算
        ('SPAN',   ( 3, 0), ( 3, 1)), # 訪問支援特別加算
        ('SPAN',   ( 4, 0), ( 4, 1)), # 食事提供加算
        ('SPAN',   ( 5, 0), ( 5, 1)), # 医療連携体制加算
        ('SPAN',   ( 6, 0), ( 6, 1)), # 体験利用支援加算
        ('SPAN',   ( 7, 0), ( 7, 1)), # 施設外支援
        ('SPAN',   (10, 0), (10, 1)), 
    ])
    table.wrapOn(p, xmargin, 23.2*mm)
    table.drawOn(p, xmargin, 23.2*mm)
    # UseStart
    colw=(28.0*mm,21.5*mm,30.5*mm,21.5*mm,30.5*mm,21.5*mm,30.5*mm)
    data=[
        ['初期加算','利用開始日',head['usestart'],'30日目',head['usestart30d'],'当月算定日数','{}日'.format(foot['usestart'])]
    ]
    table = Table(data, colWidths=colw, rowHeights=6.5*mm)
    table.setStyle([
        ('FONT',   ( 0, 0), (-1,-1), 'Gothic', 9),
        ('GRID',   ( 0, 0), (-1,-1), 0.5, colors.black),
        ('BOX',    ( 0, 0), (-1,-1), 1.8, colors.black),
        ('VALIGN', ( 0, 0), (-1,-1), 'MIDDLE'),
        ('ALIGN',  ( 0, 0), (-1,-1), 'CENTER')
    ])
    table.wrapOn(p, xmargin, 15.0*mm)
    table.drawOn(p, xmargin, 15.0*mm)
    # IDm
    p.setFont('Gothic', 11)
    p.drawString(17*mm, 10*mm, '記録ICカード：{idm}'.format(idm=idm))
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

    
