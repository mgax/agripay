#!/usr/bin/env python

import flask
from flask.ext.script import Manager
import data
import viewer


DEFAULT_CONFIG = {
    'LIB_URL': 'http://grep.ro/quickpub/lib',
}


def create_app():
    app = flask.Flask(__name__, instance_relative_config=True)
    app.config.update(DEFAULT_CONFIG)
    app.config.from_pyfile('settings.py', silent=True)
    data.initialize(app)
    viewer.initialize(app)
    return app


manager = Manager(create_app)

data.register_commands(manager)


@manager.option('-s', '--socket')
def runfcgi(socket):
    from flup.server.fcgi import WSGIServer
    app = create_app()
    WSGIServer(app, debug=app.debug, bindAddress=socket, umask=0).run()


if __name__ == '__main__':
    from utils import set_up_logging
    set_up_logging()
    manager.run()

else:
    app = create_app()
