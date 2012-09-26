import csv
import flask
from peewee import Model, CharField, DecimalField, SqliteDatabase
import flatkit.datatables


db = SqliteDatabase(None, autocommit=False)


class Record(Model):
    name = CharField()
    code = CharField()
    town = CharField()
    total = DecimalField()

    class Meta:
        database = db


class DatabasePlugin(object):

    def initialize(self, app):
        Record.Meta.database.init(app.config['DATABASE_PATH'])
        app.extensions['agripay_database'] = self


queries = flask.Blueprint('queries', __name__)


@queries.route('/')
def index():
    stats = {
        'sum(total)': Record.select('sum(total) as s').get().s,
    }
    return flask.render_template('table.html', stats=stats)


class RecordFilter(flatkit.datatables.FilterView):

    def query(self, options):
        select = Record.select()

        if options['limit']:
            select = select.limit(options['limit'])
        if options['offset']:
            select = select.offset(options['offset'])

        if options['count']:
            return select.count()

        else:
            return [{
                'name': r.name,
                'code': r.code,
                'town': r.town,
                'total': float(r.total),
            } for r in select]


queries.add_url_rule('/dt_query', view_func=RecordFilter.as_view('dt_query'))


CSV_CONFIG = {
    'apdrp.ro': {
        'csv_kwargs': {'delimiter': ';'},
    },
}


def register_commands(manager):

    @manager.command
    def create_all():
        Record.create_table(fail_silently=True)

    @manager.command
    def drop_all():
        Record.drop_table(fail_silently=True)

    @manager.command
    def load_csv(config_name, csv_path):
        config = CSV_CONFIG[config_name]

        with db.transaction():
            with open(csv_path, 'rb') as f:
                csv_kwargs = config.get('csv_kwargs', {})
                for csvrow in csv.DictReader(f, **csv_kwargs):
                    data = {
                        'name': csvrow['Denumire beneficiar'].decode('utf-8'),
                        'code': csvrow['Cod unic'],
                        'town': csvrow['Localitate'].decode('utf-8'),
                        'total': csvrow['Total plati'],
                    }
                    record = Record.create(**data)
            db.commit()


def initialize(app):
    app.register_blueprint(queries)
    DatabasePlugin().initialize(app)
