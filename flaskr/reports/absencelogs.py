from datetime import date
from flask import Blueprint, abort, make_response
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.platypus import Table
from io import BytesIO
from flaskr.reports import Report
from flaskr.models import Person, AbsenceLog

bp = Blueprint('report_absencelogs', __name__, url_prefix="/report/absencelogs")

class AbsenceLogsReport(Report):
    MAX_ROW_COUNT=14
    def __init__(self, yymm):
        super(AbsenceLogsReport, self).__init__()
        self.yymm = yymm
        self.yy = int(yymm[:4])
        self.mm = int(yymm[4:])
    def __call__(self, output):
        psize = landscape(A4)
        super(AbsenceLogsReport, self).__call__(output, psize)
    def make_report_page(self, p, items):
        p.setFont('Gothic', 16)
        p.drawString(110.0*mm, 180.0*mm, '欠席時対応加算記録')
        p.setFont('Gothic', 9)
        p.drawString(105.0*mm, 174.0*mm, '※利用を中止した日の前々日、前日または当日に連絡があった場合に利用者の状況を確認し、その内容を記録する。')
        colw = (18.0*mm, 18.0*mm, 23.5*mm, 23.5*mm, 35.0*mm, 148*mm)
        data = [['利用予定日','連絡日','連絡者','対応職員','欠席理由','相談援助']]
        count = 0
        while count < len(items):
            person = Person.get(items[count].person_id)
            staff = Person.get(items[count].staff_id)
            item = [
                date(self.yy, self.mm, items[count].dd),
                items[count].contact,
                person.name if person is not None else '',
                staff.name if staff is not None else '',
                items[count].reason,
                items[count].remarks
            ]
            data.append(item)
            count = count + 1
        while self.MAX_ROW_COUNT > count:
            data.append([])
            count = count + 1
        table = Table(data, colWidths=colw, rowHeights=10.0*mm)
        table.setStyle([
            ('FONT',   ( 0, 0), (-1,-1), 'Gothic', 9),
            ('GRID',   ( 0, 0), (-1,-1), 0.5, colors.black),
            ('BOX',    ( 0, 0), (-1,-1), 1.8, colors.black),
            ('VALIGN', ( 0, 0), (-1,-1), 'MIDDLE'),
            ('ALIGN',  ( 0, 0), (-1,-1), 'CENTER'),
            ('ALIGN',  ( 5, 1), ( 5,-1), 'LEFT'),
        ])
        table.wrapOn(p, 18.0*mm, 20.0*mm)
        table.drawOn(p, 18.0*mm, 20.0*mm)
        p.showPage()
    def make_report(self, p):
        logs = AbsenceLog.query.filter(AbsenceLog.yymm == self.yymm, AbsenceLog.enabled == True).order_by(AbsenceLog.yymm, AbsenceLog.dd).all()
        count = len(logs)
        pos = 0
        while count > pos:
            items = logs[pos:pos+self.MAX_ROW_COUNT]
            self.make_report_page(p, items)
            pos += self.MAX_ROW_COUNT

@bp.route('/<yymm>')
def report(yymm):
    with BytesIO() as output:
        report = AbsenceLogsReport(yymm)
        report(output)
        response = make_response(output.getvalue())
        response.mimetype = 'application/pdf'
    return response
