from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from flaskr import app

pdfmetrics.registerFont(TTFont('Gothic','flaskr/fonts/fonts-japanese-gothic.ttf'))

from flaskr.reports import performlogs
app.register_blueprint(performlogs.bp)
from flaskr.reports import worklogs
app.register_blueprint(worklogs.bp)
