from werkzeug.wsgi import DispatcherMiddleware
from paste.cgiapp import CGIApplication
from path import path
from webob import Request


VIEWER_HOME = path(__file__).abspath().parent / 'maps'


def create_mapserver_app():
    cgi = CGIApplication({}, 'mapserv')

    def app(environ, start_response):
        request = Request(environ)
        request.GET['map'] = VIEWER_HOME / 'money.map'
        return cgi(environ, start_response)

    return app


def initialize(app):
    app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
        '/mapserv': create_mapserver_app(),
    })
