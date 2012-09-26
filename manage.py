#!/usr/bin/env python

import flask
from flask.ext.script import Manager
import ingest


queries = flask.Blueprint('queries', __name__)

@queries.route('/')
def index():
    return "hello world!"


def create_app():
    app = flask.Flask(__name__, instance_relative_config=True)
    app.config.from_pyfile('settings.py', silent=True)
    app.register_blueprint(queries)
    ingest.DatabasePlugin().initialize(app)
    return app


manager = Manager(create_app)

ingest.register_commands(manager)


if __name__ == '__main__':
    manager.run()
