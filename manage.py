#!/usr/bin/env python

import flask
from flask.ext.script import Manager
import data


queries = flask.Blueprint('queries', __name__)

@queries.route('/')
def index():
    record_list = data.Record.select().limit(40)
    return flask.render_template('table.html', record_list=record_list)


def create_app():
    app = flask.Flask(__name__, instance_relative_config=True)
    app.config.from_pyfile('settings.py', silent=True)
    app.register_blueprint(queries)
    data.DatabasePlugin().initialize(app)
    return app


manager = Manager(create_app)

data.register_commands(manager)


if __name__ == '__main__':
    manager.run()
