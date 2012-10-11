import os
from werkzeug.wsgi import DispatcherMiddleware
from paste.cgiapp import CGIApplication
from path import path
from webob.dec import wsgify


VIEWER_HOME = path(__file__).abspath().parent / 'maps'


def create_mapserver_app():
    mapserv_cgi = CGIApplication({}, os.environ.get('MAPSERV_BIN', 'mapserv'))

    @wsgify
    def mapserv_wrapper(request):
        request.GET['map'] = VIEWER_HOME / 'money.map'
        request.GET['SRS'] = 'EPSG:3857'
        return request.get_response(mapserv_cgi)

    return mapserv_wrapper


def initialize(app):
    app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
        '/mapserv': create_mapserver_app(),
    })
