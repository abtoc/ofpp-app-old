from flask import Blueprint, render_template, redirect, url_for, flash, abort
from flask_login import login_required
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField
from wtforms.validators import DataRequired, ValidationError
from sqlalchemy import func
from flaskr import app, db
from flaskr.models import Person, TimeRule
import json
from json.decoder import JSONDecodeError
import jsonschema

bp = Blueprint('timerules', __name__, url_prefix='/timerules')

schema = {
  "type": "object",
  "title": "Root",
  "required": [ "times", "core" ],
  "properties": {
    "max": { "type": "number", "title":  "最大勤務時間" },
    "times": {
      "type": "array",
      "title": "The Times Schema",
      "items": {
        "type": "object",
        "title": "タイムテーブル",
        "required": [ "caption", "start", "end", "in", "out", "value" ],
        "properties": {
          "caption": { "type": "string", "title": "Caption", "pattern": "^(.*)$"  },
          "start": { "type": "string", "title": "開始時刻", "pattern": "^(.*)$" },
          "end": { "type": "string", "title": "終了時刻", "pattern": "^(.*)$"  },
          "in": { "type": "boolean", "title": "開始時有効" },
          "out": { "type": "boolean", "title": "終了時有効" },
          "value": { "type": "number", "title": "時刻値" }
        }
      }
    },
    "core": {
      "type": "object",
      "title": "コアタイム",
      "required": [ "start", "end", "value" ],
      "properties": {
        "start": { "type": "number", "title": "開始時刻値" },
        "end": { "type": "number", "title": "終了時刻値" },
        "value": { "type": "number", "title": "勤務時間" }
      }
    },
    "break": {
      "type": "array",
      "title": "The 休憩時刻 Schema",
      "items": {
        "type": "object",
        "title": "休憩時刻",
        "required": [ "start", "end", "value" ],
        "properties": {
          "start": { "type": "number", "title": "開始時刻値" },
          "end": { "type": "number", "title": "終了時刻値"  },
          "value": { "type": "number", "title": "休憩時間"  }
        }
      }
    }
  }
}

class TimeRuleForm(FlaskForm):
    caption = StringField('題名', validators=[DataRequired(message='必須入力です')])
    rules = TextAreaField('タイムテーブル', render_kw={'rows': 16})
    def validate_rules(form, field):
        if len(field.data) == 0:
            raise ValidationError('入力必須です')
        try:
            data=json.loads(field.data)
            jsonschema.validate(data, schema)
        except Exception as e:
            raise ValidationError(e)
        
@bp.route('/')
@login_required
def index():
    timerules = TimeRule.query.order_by(TimeRule.caption.asc()).all()
    return render_template('timerules/index.pug', timerules=timerules)

@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    form = TimeRuleForm()
    if form.validate_on_submit():
        timerule = TimeRule()
        timerule.populate_form(form)
        db.session.add(timerule)
        try:
            db.session.commit()
            flash('タイムテーブルの追加ができました', 'success')
            return redirect(url_for('timerules.index'))
        except Exception as e:
            db.session.rollback()
            flash('タイムテーブル追加時にエラーが発生しました"{}"'.format(e),'danger')
    return render_template('timerules/edit.pug', form=form)

@bp.route('/<id>/edit', methods=('GET', 'POST'))
@login_required
def edit(id):
    timerule = TimeRule.get(id)
    if timerule is None:
        abort(404)
    form = TimeRuleForm(obj=timerule)
    if form.validate_on_submit():
        timerule.populate_form(form)
        db.session.add(timerule)
        try:
            db.session.commit()
            flash('タイムテーブルの更新ができました', 'success')
            return redirect(url_for('timerules.index'))
        except Exception as e:
            db.session.rollback()
            flash('タイムテーブル更新時にエラーが発生しました"{}"'.format(e),'danger')
    return render_template('timerules/edit.pug', form=form)

@bp.route('/<id>/destroy', methods=('GET', 'POST'))
@login_required
def destroy(id):
    timerule = TimeRule.get(id)
    if timerule is None:
        abort(404)
    q = db.session.query(
        func.count(Person.id)
    ).filter(
        Person.timerule_id == id
    ).group_by(
        Person.timerule_id
    ).first()
    if q is not None:
        flash('タイムテーブルを使用しているメンバーが存在しているため、削除できません','danger')
        return redirect(url_for('timerules.index'))
    db.session.delete(timerule)
    try:
        db.session.commit()
        flash('タイムテーブルの削除ができました', 'success')
    except Exception as e:
        db.session.rollback()
        flash('タイムテーブル削除時にエラーが発生しました "{}"'.format(e), 'danger')
    return redirect(url_for('timerules.index'))

