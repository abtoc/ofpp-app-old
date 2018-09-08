#!/usr/bin/env python
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from flaskr import app,db
from commands.init import InitCommand

migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)
manager.add_command('init', InitCommand)

if __name__ == '__main__':
    manager.run()
