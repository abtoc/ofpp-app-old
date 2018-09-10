from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
from flaskr import app

pdfmetrics.registerFont(TTFont('Gothic','flaskr/fonts/fonts-japanese-gothic.ttf'))

class Report:
    def __init__(self):
        pass
    def __call__(self, output, psize):
        p = canvas.Canvas(output, pagesize=psize, bottomup=True)
        self.make_report(p)
        p.save()
    def make_report(self, p):
        pass

from flaskr.reports import performlogs
app.register_blueprint(performlogs.bp)
from flaskr.reports import worklogs
app.register_blueprint(worklogs.bp)
from flaskr.reports import absencelogs
app.register_blueprint(absencelogs.bp)
