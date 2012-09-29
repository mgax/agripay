from StringIO import StringIO
import subprocess
import json
from functools import wraps
from fabric.api import *
from fabric.contrib.files import exists
from fabric.contrib.console import confirm
from path import path
import imp


def create_sarge_deployer(name, deployer_env):
    from blinker import Namespace
    from blinker.base import symbol

    deployer = imp.new_module('_sarge_deployer.{name}'.format(**locals()))
    deployer.env = deployer_env
    deployer.app_options = {}
    deployer.default_app = None
    deployer.signal_ns = Namespace()
    deployer.install = deployer.signal_ns.signal('install')
    deployer.has_started = deployer.signal_ns.signal('has_started')
    deployer.promote = deployer.signal_ns.signal('promote')
    deployer.will_stop = deployer.signal_ns.signal('will_stop')

    def _func(func):
        setattr(deployer, func.__name__, func)
        return func

    deployer._func = _func

    @deployer._func
    def _task(func):
        @deployer._func
        @task
        @wraps(func)
        def wrapper(*args, **kwargs):
            with settings(**deployer.env):
                return func(*args, **kwargs)

        return wrapper

    @deployer._func
    def quote_json(config):
        return "'" + json.dumps(config).replace("'", "\\u0027") + "'"

    @deployer._func
    def on(signal_name, app_name='ANY'):
        signal = deployer.signal_ns[signal_name]
        def decorator(func):
            def wrapper(*args, **kwargs):
                return func()
            signal.connect(wrapper, symbol(app_name), False)
            return func
        return decorator

    @deployer._func
    def add_application(app_name, **options):
        if deployer.default_app is None:
            deployer.default_app = app_name
        deployer.app_options[app_name] = options

    def _sarge_cmd(cmd):
        return "{sarge_home}/bin/sarge {cmd}".format(cmd=cmd, **env)

    def _sarge(cmd):
        return run(_sarge_cmd(cmd) + ' 2> /dev/null')

    def _new():
        instance_config = {
            'application_name': env['deployer_app_name'],
        }
        instance_config.update(env.get('sarge_instance_config', {}))
        out = _sarge("new " + deployer.quote_json(instance_config))
        sarge_instance = out.strip()
        return sarge_instance

    def _destroy_instance(sarge_instance):
        with settings(sarge_instance=sarge_instance):
            deployer.will_stop.send(symbol(env['deployer_app_name']))
            _sarge("destroy {sarge_instance}".format(**env))

    def _remove_instances(keep=None):
        for other_instance in _instances():
            if other_instance['id'] == keep:
                continue
            with settings(sarge_instance=other_instance['id']):
                app_name = other_instance['meta']['APPLICATION_NAME']
                deployer.will_stop.send(symbol(app_name))
                _destroy_instance(other_instance['id'])

    def _rolling_deploy():
        sarge_instance = _new()
        instance_dir = env['sarge_home'] / sarge_instance
        with settings(sarge_instance=sarge_instance,
                      instance_dir=instance_dir):
            deployer.install.send(symbol(env['deployer_app_name']))
            _sarge("start {sarge_instance}".format(**env))
            deployer.has_started.send(symbol(env['deployer_app_name']))
            if confirm("Deployed {sarge_instance} - make it live?"
                       .format(**locals())):
                deployer.promote.send(symbol(env['deployer_app_name']))
                _remove_instances(keep=env['sarge_instance'])
            else:
                if confirm("Destroy instance {sarge_instance}?".format(**env)):
                    deployer.will_stop.send(symbol(env['deployer_app_name']))
                    _destroy_instance(env['sarge_instance'])

    def _simple_deploy():
        _remove_instances()
        sarge_instance = _new()
        instance_dir = env['sarge_home'] / sarge_instance
        with settings(sarge_instance=sarge_instance,
                      instance_dir=instance_dir):
            deployer.install.send(symbol(env['deployer_app_name']))
            _sarge("start {sarge_instance}".format(**env))
            deployer.has_started.send(symbol(env['deployer_app_name']))
            deployer.promote.send(symbol(env['deployer_app_name']))

    def _instances():
        app_name = env['deployer_app_name']
        for instance in json.loads(_sarge('list'))['instances']:
            if instance['meta']['APPLICATION_NAME'] != app_name:
                continue
            yield instance

    @deployer._task
    def deploy(app_name=None):
        if app_name is None:
            print "Available applications: %r" % deployer.app_options.keys()
            return
        with settings(deployer_app_name=app_name):
            if deployer.app_options[app_name].get('rolling_update', False):
                _rolling_deploy()
            else:
                _simple_deploy()

    @deployer._task
    def shell(sarge_instance=None):
        if sarge_instance is None:
            sarge_instance = deployer.default_app
        open_shell("exec " + _sarge_cmd("run " + sarge_instance))

    @deployer._task
    def supervisorctl():
        open_shell("exec {sarge_home}/bin/supervisorctl".format(**env))

    return deployer


env['use_ssh_config'] = True

SARGE_HOME = path('/var/local/agripay')


agripay = create_sarge_deployer('agripay', {
        'host_string': 'gerty',
        'agripay_python_bin': '/usr/local/Python-2.7.3/bin/python',
        'sarge_instance_config': {'prerun': 'sarge_rc.sh'},
        'sarge_home': SARGE_HOME,
        'agripay_venv': SARGE_HOME / 'var' / 'agripay-venv',
        'agripay_bin': SARGE_HOME / 'var' / 'agripay-bin',
        'agripay_node_modules': SARGE_HOME / 'var' / 'agripay-node',
        'agripay_nginx_instance': "agripay-{sarge_instance}.gerty.grep.ro",
        'agripay_nginx_live': "agripay.gerty.grep.ro",
    })

agripay.add_application('web', rolling_update=True)

_agripay_env = agripay.env

_quote_json = agripay.quote_json


@task
def configure():
    with settings(**_agripay_env):
        etc_app = env['sarge_home'] / 'etc' / 'app'
        run('mkdir -p {etc_app}'.format(**locals()))
        put(StringIO(json.dumps(agripay_CONFIG, indent=2)),
            str(etc_app / 'config.json'))


@task
def virtualenv():
    with settings(**_agripay_env):
        if not exists(env['agripay_venv']):
            run("virtualenv '{agripay_venv}' "
                "--distribute --no-site-packages "
                "-p '{agripay_python_bin}'"
                .format(**env))

        put("requirements.txt", str(env['agripay_venv']))
        run("{agripay_venv}/bin/pip install "
            "-r {agripay_venv}/requirements.txt"
            .format(**env))


@agripay.on('install', 'web')
def install_flask_app():
    src = subprocess.check_output(['git', 'archive', 'HEAD'])
    put(StringIO(src), str(env['instance_dir'] / '_src.tar'))
    with cd(env['instance_dir']):
        try:
            run("tar xvf _src.tar")
        finally:
            run("rm _src.tar")

    run("mkdir {instance_dir}/instance".format(**env))

    sarge_rc = (
        "source {agripay_venv}/bin/activate\n"
    ).format(**env)
    put(StringIO(sarge_rc), str(env['instance_dir'] / 'sarge_rc.sh'))

    app_name = env['deployer_app_name']

    put(StringIO("#!/bin/bash\n"
                 "export DATABASE_PATH=/var/local/agripay/var/db.sqlite\n"
                 "exec python manage.py runfcgi -s fcgi.sock\n"
                 .format(**env)),
        str(env['instance_dir'] / 'server'),
        mode=0755)


@agripay.on('has_started', 'web')
def link_nginx(server_name=None):
    if server_name is None:
        server_name = env['agripay_nginx_instance'].format(**env)

    instance_dir = env['sarge_home'] / env['sarge_instance']

    nginx_config = {
        'options': {
            'send_timeout': '2m',
            'client_max_body_size': '20m',
            'proxy_buffers': '8 16k',
            'proxy_buffer_size': '32k',
        },
        'urlmap': [
            {'type': 'fcgi', 'url': '/',
             'socket': 'unix:' + instance_dir / 'fcgi.sock'},
            {'type': 'static', 'url': '/static',
             'path': instance_dir / 'static'},
        ],
    }

    quoted_config = _quote_json(nginx_config)
    run('sudo tek-nginx configure {server_name}:80 {quoted_config}'
        .format(**locals()))

    print "nginx: {server_name}".format(**locals())


@agripay.on('promote', 'web')
def link_nginx_live():
    link_nginx(server_name=env['agripay_nginx_live'])


@agripay.on('will_stop', 'web')
def unlink_nginx():
    server_name = env['agripay_nginx_instance'].format(**env)
    run('sudo tek-nginx delete -f {server_name}:80'.format(**locals()))


# remap tasks to top-level namespace
deploy = agripay.deploy
supervisorctl = agripay.supervisorctl
shell = agripay.shell
del agripay
