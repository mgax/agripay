from StringIO import StringIO
import tempfile
import json
from fabric.api import *
from fabric.contrib.files import exists
from path import path


env['use_ssh_config'] = True

SARGE_HOME = path('/var/local/agripay')
ES_KIT = ('https://github.com/downloads/elasticsearch/'
          'elasticsearch/elasticsearch-0.19.9.tar.gz')
ES_ATTACH_SPEC = 'elasticsearch/elasticsearch-mapper-attachments/1.6.0'
AGRIPAY_VENV = SARGE_HOME / 'var' / 'agripay-venv'

AGRIPAY_CONFIG = {
    'SENTRY_DSN': ('http://326f1cd02a1b474a9b973f5e2c74d76c'
                         ':cc011e2b752945b6895938893a8fa14a'
                         '@sentry.gerty.grep.ro/3'),
    'ES_HEAP_SIZE': '256m',
    'AGRIPAY_VENV': AGRIPAY_VENV,
    'PYTHONPATH': '.',
    'DATABASE_PATH': SARGE_HOME / 'var' / 'db.sqlite',
    'MAPSERV_BIN': '/usr/local/mapserver-6.0.3/mapserv',
}


env.update({
    'host_string': 'gerty',
    'agripay_python_bin': '/usr/local/Python-2.7.3/bin/python',
    'sarge_home': SARGE_HOME,
    'agripay_venv': AGRIPAY_VENV,
})


@task
def configure():
    etc_app = env['sarge_home'] / 'etc' / 'app'
    run('mkdir -p {etc_app}'.format(**locals()))
    put(StringIO(json.dumps(AGRIPAY_CONFIG, indent=2)),
        str(etc_app / 'config.json'))


@task
def virtualenv():
    if not exists(env['agripay_venv']):
        run("virtualenv '{agripay_venv}' "
            "--distribute --no-site-packages "
            "-p '{agripay_python_bin}'"
            .format(**env))

    put("requirements.txt", str(env['agripay_venv']))
    run("{agripay_venv}/bin/pip install "
        "-r {agripay_venv}/requirements.txt"
        .format(**env))


@task
def deploy(app_name):
    with cd(env['sarge_home']):
        with tempfile.NamedTemporaryFile() as tmp_file:
            local('git archive HEAD | gzip > {tmp}'
                  .format(tmp=tmp_file.name))
            put(tmp_file.name, '_deploy.tgz'.format(**env))
        run("{sarge_home}/bin/sarge deploy <(zcat _deploy.tgz) {app_name}"
            .format(app_name=app_name, **env))
        run('rm _deploy.tgz')
