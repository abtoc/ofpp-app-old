from wtforms.validators import Required, Regexp, ValidationError
from flaskr.models import Person

class RequiredNotIf(Required):
    def __init__(self, other_field_name, *args, **kwargs):
        self.other_field_name = other_field_name
        super(RequiredNotIf, self).__init__(*args, **kwargs)
    def __call__(self, form, field):
        other_field = form._fields.get(self.other_field_name)
        if other_field is None:
            raise Exception('no field named "%s" in form' % self.other_field_name)
        if not bool(other_field.data):
            super(RequiredNotIf, self).__call__(form, field)

class RegexpNotIf(Regexp):
    def __init__(self, other_field_name, *args, **kwargs):
        self.other_field_name = other_field_name
        super(RegexpNotIf, self).__init__(*args, **kwargs)
    def __call__(self, form, field):
        other_field = form._fields.get(self.other_field_name)
        if other_field is None:
            raise Exception('no field named "%s" in form' % self.other_field_name)
        if not bool(other_field.data):
            super(RegexpNotIf, self).__call__(form, field)

class Unique(object):
    def __init__(self, model, field, message='This element already exists.'):
        self.model   = model
        self.field   = field
        self.message = message
    def __call__(self, form, field):
        check = self.model.query.filter(self.field == field.data).first()
        if check:
            raise ValidationError(self.message)

class UniqueIDM(object):
    def __init__(self, message="同一IDMが指定されています"):
        self.message = message
    def __call__(self, form, field):
        if len(field.data) == 0:
            return
        id = form._fields.get('id')
        if id is None:
            raise Exception('no field named "id" in form')
        check = Person.query.filter(Person.idm == field.data, Person.id != id.data).first()
        if check:
            raise ValidationError(self.message)

