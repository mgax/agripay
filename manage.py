#!/usr/bin/env python

import flask
from flask.ext.script import Manager
import data


def create_app():
    app = flask.Flask(__name__, instance_relative_config=True)
    app.config.from_pyfile('settings.py', silent=True)
    data.initialize(app)
    return app


manager = Manager(create_app)

data.register_commands(manager)


if __name__ == '__main__':
    manager.run()
